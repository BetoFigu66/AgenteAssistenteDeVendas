"""Contato de WhatsApp, vinculado (ou não) a uma empresa."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .atendimento import Atendimento
    from .empresa import Empresa
    from .mensagem import Mensagem


class Contato(Base):
    """
    Contato de uma empresa.
    Vincula telefone a empresa para identificar quem está conversando.
    """

    __tablename__ = "contatos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empresas.id"), nullable=True, index=True)
    nome: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    # Relacionamentos
    empresa: Mapped[Optional["Empresa"]] = relationship(back_populates="contatos")
    mensagens: Mapped[List["Mensagem"]] = relationship(back_populates="contato")
    atendimentos: Mapped[List["Atendimento"]] = relationship(back_populates="contato")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id, "empresa_id": self.empresa_id, "nome": self.nome,
            "telefone": self.telefone, "email": self.email, "cargo": self.cargo
        }
