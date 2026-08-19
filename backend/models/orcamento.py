"""Orçamento de um atendimento e seus itens."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .atendimento import Atendimento
    from .catalogo import Modelo


class StatusOrcamento(str, enum.Enum):
    """Status do orçamento."""

    EM_ELABORACAO = "em_elaboracao"
    PENDENTE_APROVACAO = "pendente_aprovacao"
    ENVIADO_CLIENTE = "enviado_cliente"
    APROVADO = "aprovado"
    REPROVADO = "reprovado"
    EXPIRADO = "expirado"


class Orcamento(Base):
    """
    Orçamento enviado em um atendimento.
    """

    __tablename__ = "orcamentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    atendimento_id: Mapped[int] = mapped_column(ForeignKey("atendimentos.id"), nullable=False, index=True)
    numero: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    status: Mapped[StatusOrcamento] = mapped_column(
        Enum(StatusOrcamento, values_callable=lambda x: [e.value for e in x]),
        default=StatusOrcamento.EM_ELABORACAO, nullable=False
    )
    valor_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    validade: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    atendimento: Mapped["Atendimento"] = relationship(back_populates="orcamentos")
    itens: Mapped[List["ItemOrcamento"]] = relationship(back_populates="orcamento", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "atendimento_id": self.atendimento_id,
            "numero": self.numero,
            "status": self.status.value if self.status else None,
            "valor_total": str(self.valor_total) if self.valor_total else None,
            "validade": self.validade.isoformat() if self.validade else None,
            "observacoes": self.observacoes,
        }


class ItemOrcamento(Base):
    """
    Item de um orçamento.
    """

    __tablename__ = "itens_orcamento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orcamento_id: Mapped[int] = mapped_column(ForeignKey("orcamentos.id"), nullable=False, index=True)
    modelo_id: Mapped[int] = mapped_column(ForeignKey("modelos.id"), nullable=False, index=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    desconto_percentual: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True, default=0)

    # Relacionamentos
    orcamento: Mapped["Orcamento"] = relationship(back_populates="itens")
    modelo: Mapped["Modelo"] = relationship(back_populates="itens_orcamento")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "orcamento_id": self.orcamento_id,
            "modelo_id": self.modelo_id,
            "quantidade": str(self.quantidade),
            "preco_unitario": str(self.preco_unitario),
            "desconto_percentual": str(self.desconto_percentual) if self.desconto_percentual else None,
        }
