"""Empresas (PJ, consulta CNPJ) e seus dados derivados (atividades, sócios)."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .atendimento import Atendimento
    from .contato import Contato


class TipoEmpresa(str, enum.Enum):
    """Tipo da empresa (matriz ou filial)."""

    MATRIZ = "MATRIZ"
    FILIAL = "FILIAL"


class Empresa(Base):
    """
    Modelo para armazenar dados de empresas (consulta CNPJ).
    Dados obtidos via API ReceitaWS ou similar.
    """

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cnpj: Mapped[str] = mapped_column(String(18), unique=True, nullable=False, index=True)

    # Dados básicos
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    fantasia: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tipo: Mapped[Optional[TipoEmpresa]] = mapped_column(
        Enum(TipoEmpresa, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    porte: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    natureza_juridica: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    capital_social: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    abertura: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Situação cadastral
    situacao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    data_situacao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    motivo_situacao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    situacao_especial: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    data_situacao_especial: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Endereço
    logradouro: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    numero: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    complemento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bairro: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    municipio: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uf: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    cep: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Contato
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Simples Nacional
    simples_optante: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    simples_data_opcao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    simples_data_exclusao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # MEI
    simei_optante: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Controle
    ultima_atualizacao_api: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    atividades: Mapped[List["AtividadeEmpresa"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    socios: Mapped[List["SocioEmpresa"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    contatos: Mapped[List["Contato"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    atendimentos: Mapped[List["Atendimento"]] = relationship(back_populates="empresa")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "cnpj": self.cnpj,
            "nome": self.nome,
            "fantasia": self.fantasia,
            "tipo": self.tipo.value if self.tipo else None,
            "porte": self.porte,
            "natureza_juridica": self.natureza_juridica,
            "capital_social": str(self.capital_social) if self.capital_social else None,
            "abertura": self.abertura.isoformat() if self.abertura else None,
            "situacao": self.situacao,
            "data_situacao": self.data_situacao.isoformat() if self.data_situacao else None,
            "logradouro": self.logradouro,
            "numero": self.numero,
            "complemento": self.complemento,
            "bairro": self.bairro,
            "municipio": self.municipio,
            "uf": self.uf,
            "cep": self.cep,
            "email": self.email,
            "telefone": self.telefone,
            "simples_optante": self.simples_optante,
            "simei_optante": self.simei_optante,
            "atividades": [a.to_dict() for a in self.atividades],
            "socios": [s.to_dict() for s in self.socios],
        }


class AtividadeEmpresa(Base):
    """
    Atividades econômicas da empresa (CNAE).
    Inclui atividade principal e secundárias.
    """

    __tablename__ = "atividades_empresa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    is_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relacionamento
    empresa: Mapped["Empresa"] = relationship(back_populates="atividades")

    __table_args__ = (Index("idx_atividades_codigo", "codigo"),)

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {"codigo": self.codigo, "descricao": self.descricao, "is_principal": self.is_principal}


class SocioEmpresa(Base):
    """
    Quadro societário da empresa (QSA).
    """

    __tablename__ = "socios_empresa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    qualificacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relacionamento
    empresa: Mapped["Empresa"] = relationship(back_populates="socios")

    __table_args__ = (Index("idx_socios_nome", "nome"),)

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {"nome": self.nome, "qualificacao": self.qualificacao}
