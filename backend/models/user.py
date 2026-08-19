"""Usuários do sistema (aprovadores/atendentes do painel)."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .mensagem import Mensagem
    from .pessoa import Pessoa


class User(Base):
    """Usuário do sistema.

    Usado para registrar quem aprovou mensagens geradas pelo agente antes
    do envio ao cliente, e (REQ-010, Fase 4) para autenticação mínima do
    painel — `login`/`senha_hash` são nullable porque usuários criados antes
    dessa fase não têm senha até alguém definir uma via
    `PATCH /api/users/{id}/senha`.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    login: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    senha_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    # Relacionamentos
    mensagens_aprovadas: Mapped[List["Mensagem"]] = relationship(
        back_populates="aprovador", foreign_keys="Mensagem.aprovador_id"
    )
    pessoas_verificadas: Mapped[List["Pessoa"]] = relationship(
        back_populates="verificador", foreign_keys="Pessoa.user_id_verificador"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "login": self.login,
            "tem_senha": self.senha_hash is not None,
            "created_at": serialize_utc_datetime(self.created_at),
        }
