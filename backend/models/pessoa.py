"""Pessoa Física (PF) identificada por CPF."""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .atendimento import Atendimento
    from .user import User


class Pessoa(Base):
    """
    Pessoa Física (PF) identificada por CPF.

    Dados coletados na conversa (CPF, nome, data de nascimento). A validação
    cadastral é manual: `user_id_verificador` e `timestamp_verificacao` registram
    quem confirmou os dados e quando (sem API externa por enquanto).
    """

    __tablename__ = "pessoas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cpf: Mapped[str] = mapped_column(String(14), unique=True, nullable=False, index=True)
    nome: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    situacao: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    ultima_atualizacao_api: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    user_id_verificador: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    timestamp_verificacao: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    atendimentos: Mapped[List["Atendimento"]] = relationship(back_populates="pessoa")
    verificador: Mapped[Optional["User"]] = relationship(
        back_populates="pessoas_verificadas", foreign_keys=[user_id_verificador]
    )

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "cpf": self.cpf,
            "nome": self.nome,
            "data_nascimento": self.data_nascimento.isoformat() if self.data_nascimento else None,
            "situacao": self.situacao,
            "user_id_verificador": self.user_id_verificador,
            "timestamp_verificacao": serialize_utc_datetime(self.timestamp_verificacao),
            "verificado": self.user_id_verificador is not None and self.timestamp_verificacao is not None,
        }
