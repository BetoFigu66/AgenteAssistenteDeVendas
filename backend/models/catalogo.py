"""Catálogo comercial: produtos (categorias), modelos (SKUs) e seus atributos."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .atendimento import ItemAtendimento
    from .orcamento import ItemOrcamento

modelos_categorias = Table(
    "modelos_categorias",
    Base.metadata,
    Column("modelo_id", ForeignKey("modelos.id", ondelete="CASCADE"), primary_key=True),
    Column("categoria_id", ForeignKey("categorias.id", ondelete="CASCADE"), primary_key=True),
)


class Categoria(Base):
    """Agrupador comercial associado a um ou mais modelos."""

    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    descricao: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    modelos: Mapped[List["Modelo"]] = relationship(
        secondary=modelos_categorias,
        back_populates="categorias",
    )

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {"id": self.id, "descricao": self.descricao, "ativo": self.ativo}


class Produto(Base):
    """
    Categoria genérica de produto (ex: Catraca, Relógio de Ponto).
    Usado para classificar modelos e itens de atendimento antes da escolha do modelo
    específico. (Renomeado de `TipoProduto` — decisão 2026-07-09, ver docs/dicionario_termos.md.)
    """

    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    descricao: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    # Relacionamentos
    modelos: Mapped[List["Modelo"]] = relationship(back_populates="produto")
    itens_atendimento: Mapped[List["ItemAtendimento"]] = relationship(back_populates="produto")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {"id": self.id, "descricao": self.descricao, "ativo": self.ativo}


class AtributoAdicionalModelo(Base):
    """Atributos genéricos adicionais de um modelo de produto (ex.: tecnologia de leitura).

    Permite estender o catálogo sem alterar a tabela `modelos` para cada novo
    tipo de atributo. A chave deve coincidir com a chave usada em
    `AtendimentoInfo` para que a resolução de modelo possa filtrar modelos pelos
    sinais extraídos da conversa.
    """

    __tablename__ = "atributos_adicionais_modelo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    modelo_id: Mapped[int] = mapped_column(ForeignKey("modelos.id", ondelete="CASCADE"), nullable=False, index=True)
    chave: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[str] = mapped_column(String(300), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    modelo: Mapped["Modelo"] = relationship(back_populates="atributos")

    def to_dict(self) -> dict:
        """Converte o atributo para dicionário."""
        return {
            "id": self.id,
            "modelo_id": self.modelo_id,
            "chave": self.chave,
            "valor": self.valor,
            "ativo": self.ativo,
        }


class Modelo(Base):
    """
    Catálogo de modelos específicos e precificáveis para orçamentos (SKU), FK obrigatória
    para a categoria (`Produto`). (Renomeado de `Produto` — decisão 2026-07-09, ver
    docs/dicionario_termos.md.)
    """

    __tablename__ = "modelos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False, index=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    preco_tabela: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    unidade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="UN")
    marca: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    aplicacao: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    produto: Mapped["Produto"] = relationship(back_populates="modelos")
    categorias: Mapped[List["Categoria"]] = relationship(
        secondary=modelos_categorias,
        back_populates="modelos",
    )
    atributos: Mapped[List["AtributoAdicionalModelo"]] = relationship(
        back_populates="modelo",
        cascade="all, delete-orphan",
    )
    itens_orcamento: Mapped[List["ItemOrcamento"]] = relationship(back_populates="modelo")
    itens_atendimento: Mapped[List["ItemAtendimento"]] = relationship(back_populates="modelo")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "preco_tabela": str(self.preco_tabela) if self.preco_tabela is not None else None,
            "unidade": self.unidade,
            "categorias": [categoria.to_dict() for categoria in self.categorias],
            "atributos": [atributo.to_dict() for atributo in self.atributos],
            "marca": self.marca,
            "aplicacao": self.aplicacao,
            "ativo": self.ativo,
        }
