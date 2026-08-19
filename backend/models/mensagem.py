"""Mensagens do chat (WhatsApp/web) e sua origem."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .atendimento import Atendimento
    from .contato import Contato
    from .processamento import ProcessamentoMensagem
    from .user import User


class OrigemMensagem(str, enum.Enum):
    """Enum para origem da mensagem."""

    USER = "user"
    SYSTEM = "system"


class Mensagem(Base):
    """Modelo para armazenar mensagens do chat."""

    __tablename__ = "mensagens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    origem: Mapped[OrigemMensagem] = mapped_column(
        Enum(OrigemMensagem, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    message_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    # Novos campos - relacionamentos
    contato_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contatos.id"), nullable=True, index=True)
    atendimento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("atendimentos.id"), nullable=True, index=True)
    processamento_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("processamentos_mensagem.id"), nullable=True, index=True
    )

    # Aprovação de mensagens geradas pelo agente (REQ-011)
    aprovador_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    timestamp_aprovacao: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    # REQ-011.6: feedback textual opcional ao aprovar (mensagem correta, mas com nota).
    # Reprovação já tem seu próprio texto livre em `ReportProblema.descricao` — aqui é
    # só o caso positivo, que não gera report.
    feedback_aprovacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos
    contato: Mapped[Optional["Contato"]] = relationship(back_populates="mensagens")
    atendimento: Mapped[Optional["Atendimento"]] = relationship(back_populates="mensagens")
    processamento: Mapped[Optional["ProcessamentoMensagem"]] = relationship(
        back_populates="mensagem", foreign_keys=[processamento_id]
    )
    aprovador: Mapped[Optional["User"]] = relationship(
        back_populates="mensagens_aprovadas", foreign_keys=[aprovador_id]
    )

    __table_args__ = (
        Index("idx_mensagens_telefone_timestamp", "telefone", "timestamp"),
        Index("idx_mensagens_contato", "contato_id"),
        Index("idx_mensagens_atendimento", "atendimento_id"),
    )

    @property
    def pendente_aprovacao(self) -> bool:
        """True quando a mensagem foi gerada pelo agente e ainda não foi aprovada.

        Mensagens do cliente (origem=USER) nunca são consideradas pendentes.
        """
        origem_val = self.origem.value if isinstance(self.origem, OrigemMensagem) else self.origem
        return origem_val == OrigemMensagem.SYSTEM.value and self.aprovador_id is None

    @property
    def segundos_pendente(self) -> Optional[int]:
        """REQ-011.13: há quanto tempo esta mensagem está pendente (SLA visual). `None`
        quando não está pendente."""
        if not self.pendente_aprovacao:
            return None
        return int((utc_now() - self.timestamp).total_seconds())

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "telefone": self.telefone,
            "conteudo": self.conteudo,
            "origem": self.origem.value if isinstance(self.origem, OrigemMensagem) else self.origem,
            "timestamp": serialize_utc_datetime(self.timestamp),
            "contato_id": self.contato_id,
            "atendimento_id": self.atendimento_id,
            "processamento_id": self.processamento_id,
            "aprovador_id": self.aprovador_id,
            "timestamp_aprovacao": serialize_utc_datetime(self.timestamp_aprovacao),
            "pendente_aprovacao": self.pendente_aprovacao,
            "feedback_aprovacao": self.feedback_aprovacao,
            "segundos_pendente": self.segundos_pendente,
        }
