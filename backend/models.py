"""
Modelos SQLAlchemy para o Assistente de Vendas via WhatsApp com IA.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType
from utils.datetime_utils import serialize_utc_datetime, utc_now

UTCDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    """Classe base para todos os modelos."""

    pass


class Vector(UserDefinedType):
    """Tipo pgvector para embeddings.

    Serializa list[float] no formato textual aceito pelo pgvector ("[v1,v2,...]")
    e converte a leitura de volta para list[float]. Permite usar o atributo
    `embedding` como uma lista Python em codigo cliente.
    """

    cache_ok = True

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def get_col_spec(self, **kw) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return "[" + ",".join(repr(float(x)) for x in value) + "]"

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return list(value)
            texto = value.strip()
            if texto.startswith("[") and texto.endswith("]"):
                texto = texto[1:-1]
            if not texto:
                return []
            return [float(x) for x in texto.split(",")]

        return process


class OrigemMensagem(str, enum.Enum):
    """Enum para origem da mensagem."""

    USER = "user"
    SYSTEM = "system"


class StatusAtendimento(str, enum.Enum):
    """Status do atendimento (REQ-016.4)."""

    ATIVO = "ativo"
    ENCERRADO = "encerrado"


class StatusOrcamento(str, enum.Enum):
    """Status do orçamento."""

    EM_ELABORACAO = "em_elaboracao"
    PENDENTE_APROVACAO = "pendente_aprovacao"
    ENVIADO_CLIENTE = "enviado_cliente"
    APROVADO = "aprovado"
    REPROVADO = "reprovado"
    EXPIRADO = "expirado"


class ModoOperacao(str, enum.Enum):
    """Modo de operação do atendimento.

    - AGENTE: sistema gera respostas automáticas (padrão).
    - HUMANO: sistema apenas recebe e registra mensagens; respostas são
      enviadas manualmente pelo operador via interface web.
    """

    AGENTE = "agente"
    HUMANO = "humano"


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

    # Aprovação de mensagens geradas pelo agente (REQ-aprovação)
    aprovador_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    timestamp_aprovacao: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

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
        }


class User(Base):
    """Usuário do sistema (sem autenticação por enquanto).

    Usado para registrar quem aprovou mensagens geradas pelo agente antes
    do envio ao cliente.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
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
            "created_at": serialize_utc_datetime(self.created_at),
        }


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


class TipoDocumento(str, enum.Enum):
    """Tipo de documento fiscal associado ao atendimento."""

    CPF = "cpf"
    CNPJ = "cnpj"
    INDEFINIDO = "indefinido"


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


class Atendimento(Base):
    """
    Atendimento com um contato (REQ-016).
    Agrupa conversas e orçamentos de uma mesma demanda do cliente.
    """

    __tablename__ = "atendimentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contato_id: Mapped[int] = mapped_column(ForeignKey("contatos.id"), nullable=False, index=True)
    empresa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("empresas.id"), nullable=True, index=True)
    pessoa_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pessoas.id"), nullable=True, index=True)
    tipo_documento: Mapped[TipoDocumento] = mapped_column(
        Enum(TipoDocumento, values_callable=lambda x: [e.value for e in x], name="tipodocumento"),
        default=TipoDocumento.INDEFINIDO,
        nullable=False,
        index=True,
    )
    titulo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[StatusAtendimento] = mapped_column(
        Enum(
            StatusAtendimento,
            values_callable=lambda x: [e.value for e in x],
            name="statusatendimento",
        ),
        default=StatusAtendimento.ATIVO,
        nullable=False,
    )
    motivo_encerramento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    modo_operacao: Mapped[ModoOperacao] = mapped_column(
        Enum(ModoOperacao, values_callable=lambda x: [e.value for e in x], name="modooperacao"),
        default=ModoOperacao.AGENTE,
        nullable=False,
        index=True,
    )
    valor_estimado: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
    ultima_mensagem_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    numero_atendimento_cliente: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "contato_id",
            "numero_atendimento_cliente",
            name="uq_atendimentos_contato_numero",
        ),
    )

    # Relacionamentos
    contato: Mapped["Contato"] = relationship(back_populates="atendimentos")
    empresa: Mapped[Optional["Empresa"]] = relationship(back_populates="atendimentos")
    pessoa: Mapped[Optional["Pessoa"]] = relationship(back_populates="atendimentos")
    mensagens: Mapped[List["Mensagem"]] = relationship(back_populates="atendimento")
    orcamentos: Mapped[List["Orcamento"]] = relationship(back_populates="atendimento", cascade="all, delete-orphan")
    itens: Mapped[List["ItemAtendimento"]] = relationship(back_populates="atendimento", cascade="all, delete-orphan")
    informacoes: Mapped[List["AtendimentoInfo"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "contato_id": self.contato_id,
            "empresa_id": self.empresa_id,
            "pessoa_id": self.pessoa_id,
            "tipo_documento": self.tipo_documento.value if self.tipo_documento else None,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "status": self.status.value if self.status else None,
            "motivo_encerramento": self.motivo_encerramento,
            "modo_operacao": self.modo_operacao.value if self.modo_operacao else None,
            "valor_estimado": str(self.valor_estimado) if self.valor_estimado else None,
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
            "ultima_mensagem_at": serialize_utc_datetime(self.ultima_mensagem_at),
            "numero_atendimento_cliente": self.numero_atendimento_cliente,
        }


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


class TipoProduto(Base):
    """
    Tipo/categoria de produto (ex: Catraca, Relógio de Ponto).
    Usado para classificar produtos e itens de negociação antes da escolha do modelo.
    """

    __tablename__ = "tipos_produto"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    descricao: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    # Relacionamentos
    produtos: Mapped[List["Produto"]] = relationship(back_populates="tipo_produto")
    itens_atendimento: Mapped[List["ItemAtendimento"]] = relationship(back_populates="tipo_produto")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {"id": self.id, "descricao": self.descricao, "ativo": self.ativo}


class Produto(Base):
    """
    Catálogo de produtos para orçamentos.
    """

    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_produto_id: Mapped[int] = mapped_column(ForeignKey("tipos_produto.id"), nullable=False, index=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    preco_tabela: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    unidade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="UN")
    categoria: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    tipo_produto: Mapped["TipoProduto"] = relationship(back_populates="produtos")
    itens_orcamento: Mapped[List["ItemOrcamento"]] = relationship(back_populates="produto")
    itens_atendimento: Mapped[List["ItemAtendimento"]] = relationship(back_populates="produto")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "tipo_produto_id": self.tipo_produto_id,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "preco_tabela": str(self.preco_tabela),
            "unidade": self.unidade,
            "categoria": self.categoria,
            "ativo": self.ativo,
        }


class DocumentoConhecimento(Base):
    """
    Chunk/documento de conhecimento usado pela RAG.

    A coluna no banco chama-se `metadata`, mas no modelo usamos `metadados`
    porque `metadata` e reservado pelo SQLAlchemy Declarative.
    """

    __tablename__ = "documentos_conhecimento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_externo: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    id_documento_origem: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    id_fonte: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    metadados: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    conteudo_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_documentos_conhecimento_tipo_ativo", "tipo", "ativo"),
        Index("idx_documentos_conhecimento_titulo", "titulo"),
        Index("idx_documentos_conhecimento_hash", "conteudo_hash"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "id_externo": self.id_externo,
            "id_documento_origem": self.id_documento_origem,
            "id_fonte": self.id_fonte,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "conteudo": self.conteudo,
            "metadata": self.metadados,
            "conteudo_hash": self.conteudo_hash,
            "ativo": self.ativo,
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
        }


class ParQA(Base):
    """
    Par Pergunta+Resposta curado para busca semântica.

    O embedding é gerado a partir do campo `pergunta` (não da resposta),
    maximizando a similaridade cosseno com queries dos usuários.
    """

    __tablename__ = "pares_qa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_externo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    pergunta: Mapped[str] = mapped_column(Text, nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    contexto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    pergunta_tsv: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aprovado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criado_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_pares_qa_contexto_ativo", "contexto", "ativo"),
        Index("idx_pares_qa_aprovado_ativo", "aprovado", "ativo"),
        Index("idx_pares_qa_pergunta_tsv", "pergunta_tsv", postgresql_using="gin"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "id_externo": self.id_externo,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "contexto": self.contexto,
            "tags": self.tags or [],
            "ativo": self.ativo,
            "aprovado": self.aprovado,
            "criado_por": self.criado_por,
            "criado_em": serialize_utc_datetime(self.criado_em),
            "atualizado_em": serialize_utc_datetime(self.atualizado_em),
        }


class ItemOrcamento(Base):
    """
    Item de um orçamento.
    """

    __tablename__ = "itens_orcamento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orcamento_id: Mapped[int] = mapped_column(ForeignKey("orcamentos.id"), nullable=False, index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False, index=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    desconto_percentual: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True, default=0)

    # Relacionamentos
    orcamento: Mapped["Orcamento"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship(back_populates="itens_orcamento")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "orcamento_id": self.orcamento_id,
            "produto_id": self.produto_id,
            "quantidade": str(self.quantidade),
            "preco_unitario": str(self.preco_unitario),
            "desconto_percentual": str(self.desconto_percentual) if self.desconto_percentual else None,
        }


class ItemAtendimento(Base):
    """
    Item de um atendimento (pré-orçamento).
    Começa apenas com tipo_produto e quantidade.
    O produto específico é definido quando o modelo for escolhido.
    """

    __tablename__ = "itens_negociacao"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    atendimento_id: Mapped[int] = mapped_column(ForeignKey("atendimentos.id"), nullable=False, index=True)
    tipo_produto_id: Mapped[int] = mapped_column(ForeignKey("tipos_produto.id"), nullable=False, index=True)
    produto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("produtos.id"), nullable=True, index=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    atendimento: Mapped["Atendimento"] = relationship(back_populates="itens")
    tipo_produto: Mapped["TipoProduto"] = relationship(back_populates="itens_atendimento")
    produto: Mapped[Optional["Produto"]] = relationship(back_populates="itens_atendimento")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "atendimento_id": self.atendimento_id,
            "tipo_produto_id": self.tipo_produto_id,
            "produto_id": self.produto_id,
            "quantidade": str(self.quantidade),
            "observacoes": self.observacoes,
        }


class OrigemInfo(str, enum.Enum):
    """Origem da informação coletada."""

    USER = "user"  # Fornecido pelo cliente
    INFERIDO = "inferido"  # Extraído pela LLM
    SISTEMA = "sistema"  # Preenchido pelo sistema (ex: consulta CNPJ)
    ATENDENTE = "atendente"  # Preenchido manualmente por atendente humano


class AtendimentoInfo(Base):
    """
    Informações coletadas/pendentes durante um atendimento.
    Modelo chave-valor auditável para rastrear dados do atendimento.

    Exemplos de chaves: cnpj, nome_contato, localizacao_instalacao,
                       sistema_cliente, prazo_desejado, etc.
    """

    __tablename__ = "atendimento_infos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    atendimento_id: Mapped[int] = mapped_column(ForeignKey("atendimentos.id"), nullable=False, index=True)
    chave: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pendente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    origem: Mapped[Optional[OrigemInfo]] = mapped_column(
        Enum(OrigemInfo, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    atendimento: Mapped["Atendimento"] = relationship(back_populates="informacoes")

    __table_args__ = (Index("idx_atendimento_info_chave", "atendimento_id", "chave", unique=True),)

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "atendimento_id": self.atendimento_id,
            "chave": self.chave,
            "valor": self.valor,
            "pendente": self.pendente,
            "origem": self.origem.value if self.origem else None,
            "updated_at": serialize_utc_datetime(self.updated_at),
        }


class OrigemClassificacao(str, enum.Enum):
    """Origem da classificação da mensagem."""

    REGRA = "regra"
    LLM = "llm"
    HIBRIDO = "hibrido"


class ProcessamentoMensagem(Base):
    """
    Registro auditável do processamento de uma mensagem pelo cérebro.

    Armazena todas as decisões tomadas (classificação, identificação, geração de resposta),
    permitindo debug de conversas, medição de qualidade e evolução do cérebro.

    Uma mensagem (Mensagem) aponta para um ProcessamentoMensagem opcionalmente.
    Geralmente apenas mensagens de origem USER têm processamento associado.
    """

    __tablename__ = "processamentos_mensagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Classificação ---
    intencao: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    confianca: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    confianca_nivel: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    origem_classificacao: Mapped[Optional[OrigemClassificacao]] = mapped_column(
        Enum(OrigemClassificacao, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    entidades: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- Identificação do remetente no momento do processamento ---
    status_identificacao: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    contato_id_identificado: Mapped[Optional[int]] = mapped_column(ForeignKey("contatos.id"), nullable=True)
    empresa_id_identificada: Mapped[Optional[int]] = mapped_column(ForeignKey("empresas.id"), nullable=True)
    atendimento_id_ativa: Mapped[Optional[int]] = mapped_column(ForeignKey("atendimentos.id"), nullable=True)

    # --- Decisão de resposta ---
    template_usado: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    personalizado_via_llm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Metadados da LLM (se usada) ---
    llm_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    llm_modelo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    llm_tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_latencia_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_raw_resposta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- RAG (retrieval-augmented generation) ---
    rag_utilizada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rag_trechos: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    rag_score_maximo: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)

    # --- Controle ---
    duracao_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    erro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    # Relacionamento inverso (mensagem aponta para cá via FK)
    mensagem: Mapped[Optional["Mensagem"]] = relationship(
        back_populates="processamento",
        foreign_keys="Mensagem.processamento_id",
        uselist=False,
    )
    reports: Mapped[List["ReportProblema"]] = relationship(
        back_populates="processamento",
        cascade="all, delete-orphan",
        order_by="ReportProblema.created_at.desc()",
    )

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "intencao": self.intencao,
            "confianca": float(self.confianca) if self.confianca is not None else None,
            "origem_classificacao": (self.origem_classificacao.value if self.origem_classificacao else None),
            "entidades": self.entidades,
            "status_identificacao": self.status_identificacao,
            "contato_id_identificado": self.contato_id_identificado,
            "empresa_id_identificada": self.empresa_id_identificada,
            "atendimento_id_ativa": self.atendimento_id_ativa,
            "template_usado": self.template_usado,
            "personalizado_via_llm": self.personalizado_via_llm,
            "llm_provider": self.llm_provider,
            "llm_modelo": self.llm_modelo,
            "llm_tokens_input": self.llm_tokens_input,
            "llm_tokens_output": self.llm_tokens_output,
            "llm_latencia_ms": self.llm_latencia_ms,
            "llm_raw_resposta": self.llm_raw_resposta,
            "rag_utilizada": self.rag_utilizada,
            "rag_trechos": self.rag_trechos,
            "rag_score_maximo": (float(self.rag_score_maximo) if self.rag_score_maximo is not None else None),
            "duracao_ms": self.duracao_ms,
            "erro": self.erro,
            "created_at": serialize_utc_datetime(self.created_at),
        }


class CategoriaReport(str, enum.Enum):
    """Categoria do problema reportado — indica a camada afetada."""

    CLASSIFICACAO = "classificacao"  # intenção/entidades erradas
    FLUXO = "fluxo"  # orquestração/roteamento errado
    TEMPLATE = "template"  # texto/tom da resposta
    RESPOSTA_INADEQUADA = "resposta_inadequada"  # resposta do agente inadequada (reprovação)
    DADOS = "dados"  # dados incorretos (CNPJ, contato, etc.)
    LLM = "llm"  # problema com a LLM (timeout, erro, etc.)
    OUTRO = "outro"


class SeveridadeReport(str, enum.Enum):
    """Severidade do impacto do problema."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class StatusReport(str, enum.Enum):
    """Estágio do report no workflow de correção."""

    ABERTO = "aberto"
    EM_ANALISE = "em_analise"
    AGUARDANDO_FIX = "aguardando_fix"
    RESOLVIDO = "resolvido"
    DESCARTADO = "descartado"


class ReportProblema(Base):
    """
    Report de problema em um processamento de mensagem.

    Permite que o usuário (desenvolvedor, atendente) marque um processamento
    como problemático, descrevendo em texto livre o que não funcionou.
    Usado para evoluir o cérebro do assistente.
    """

    __tablename__ = "reports_problema"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    processamento_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("processamentos_mensagem.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    mensagem_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("mensagens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    autor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Triagem
    categoria: Mapped[CategoriaReport] = mapped_column(
        Enum(CategoriaReport, values_callable=lambda x: [e.value for e in x]),
        default=CategoriaReport.OUTRO,
        nullable=False,
    )
    severidade: Mapped[SeveridadeReport] = mapped_column(
        Enum(SeveridadeReport, values_callable=lambda x: [e.value for e in x]),
        default=SeveridadeReport.MEDIA,
        nullable=False,
    )
    status: Mapped[StatusReport] = mapped_column(
        Enum(StatusReport, values_callable=lambda x: [e.value for e in x]),
        default=StatusReport.ABERTO,
        nullable=False,
        index=True,
    )

    # Resolução
    resolucao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolvido_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolvido_em: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relacionamentos
    processamento: Mapped["ProcessamentoMensagem"] = relationship(back_populates="reports")

    @property
    def resolvido(self) -> bool:
        """Compatibilidade retroativa: resolvido = status terminal."""
        return self.status in (StatusReport.RESOLVIDO, StatusReport.DESCARTADO)

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "processamento_id": self.processamento_id,
            "mensagem_id": self.mensagem_id,
            "descricao": self.descricao,
            "autor": self.autor,
            "categoria": self.categoria.value if self.categoria else None,
            "severidade": self.severidade.value if self.severidade else None,
            "status": self.status.value if self.status else None,
            "resolvido": self.resolvido,
            "resolucao": self.resolucao,
            "resolvido_por": self.resolvido_por,
            "resolvido_em": serialize_utc_datetime(self.resolvido_em),
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
        }


class Parametro(Base):
    """
    Parâmetro de configuração dinâmica, calibrável sem deploy.

    Usado para limiares de fallback, scores de RAG, e outras
    constantes que evoluem com a operação. O valor é sempre string
    no banco; o leitor faz cast para int/float/bool conforme necessário.
    """

    __tablename__ = "parametros"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "valor": self.valor,
            "descricao": self.descricao,
            "updated_at": serialize_utc_datetime(self.updated_at),
        }
