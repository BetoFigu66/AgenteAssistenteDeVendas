"""
Modelos SQLAlchemy para o Assistente de Vendas.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Date, Enum, Index, Boolean, Numeric, ForeignKey, Integer, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Classe base para todos os modelos."""
    pass


class OrigemMensagem(str, enum.Enum):
    """Enum para origem da mensagem."""
    USER = "user"
    SYSTEM = "system"


class StatusNegociacao(str, enum.Enum):
    """Status da negociação."""
    NOVO = "novo"
    EM_CONTATO = "em_contato"
    AGUARDANDO_ORCAMENTO = "aguardando_orcamento"
    ORCAMENTO_ENVIADO = "orcamento_enviado"
    EM_NEGOCIACAO = "em_negociacao"
    FECHADO_VENDA = "fechado_venda"
    FECHADO_PERDA = "fechado_perda"
    ARQUIVADO = "arquivado"


class StatusOrcamento(str, enum.Enum):
    """Status do orçamento."""
    EM_ELABORACAO = "em_elaboracao"
    PENDENTE_APROVACAO = "pendente_aprovacao"
    ENVIADO_CLIENTE = "enviado_cliente"
    APROVADO = "aprovado"
    REPROVADO = "reprovado"
    EXPIRADO = "expirado"


class Mensagem(Base):
    """Modelo para armazenar mensagens do chat."""
    
    __tablename__ = "mensagens"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    origem: Mapped[OrigemMensagem] = mapped_column(
        Enum(OrigemMensagem, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    message_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    
    # Novos campos - relacionamentos
    contato_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contatos.id"), nullable=True, index=True)
    negociacao_id: Mapped[Optional[int]] = mapped_column(ForeignKey("negociacoes.id"), nullable=True, index=True)
    processamento_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("processamentos_mensagem.id"), nullable=True, index=True
    )
    
    # Relacionamentos
    contato: Mapped[Optional["Contato"]] = relationship(back_populates="mensagens")
    negociacao: Mapped[Optional["Negociacao"]] = relationship(back_populates="mensagens")
    processamento: Mapped[Optional["ProcessamentoMensagem"]] = relationship(
        back_populates="mensagem", foreign_keys=[processamento_id]
    )
    
    __table_args__ = (
        Index('idx_mensagens_telefone_timestamp', 'telefone', 'timestamp'),
        Index('idx_mensagens_contato', 'contato_id'),
        Index('idx_mensagens_negociacao', 'negociacao_id'),
    )
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "telefone": self.telefone,
            "conteudo": self.conteudo,
            "origem": self.origem.value if isinstance(self.origem, OrigemMensagem) else self.origem,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "contato_id": self.contato_id,
            "negociacao_id": self.negociacao_id,
            "processamento_id": self.processamento_id,
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
        Enum(TipoEmpresa, values_callable=lambda x: [e.value for e in x]),
        nullable=True
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
    ultima_atualizacao_api: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relacionamentos
    atividades: Mapped[List["AtividadeEmpresa"]] = relationship(
        back_populates="empresa", 
        cascade="all, delete-orphan"
    )
    socios: Mapped[List["SocioEmpresa"]] = relationship(
        back_populates="empresa", 
        cascade="all, delete-orphan"
    )
    contatos: Mapped[List["Contato"]] = relationship(
        back_populates="empresa", 
        cascade="all, delete-orphan"
    )
    negociacoes: Mapped[List["Negociacao"]] = relationship(
        back_populates="empresa"
    )
    
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
    
    __table_args__ = (
        Index('idx_atividades_codigo', 'codigo'),
    )
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "codigo": self.codigo,
            "descricao": self.descricao,
            "is_principal": self.is_principal
        }


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
    
    __table_args__ = (
        Index('idx_socios_nome', 'nome'),
    )
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "nome": self.nome,
            "qualificacao": self.qualificacao
        }


class Contato(Base):
    """
    Contato de uma empresa.
    Vincula telefone a empresa para identificar quem está conversando.
    """
    
    __tablename__ = "contatos"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    nome: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    empresa: Mapped["Empresa"] = relationship(back_populates="contatos")
    mensagens: Mapped[List["Mensagem"]] = relationship(back_populates="contato")
    negociacoes: Mapped[List["Negociacao"]] = relationship(back_populates="contato")
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "nome": self.nome,
            "telefone": self.telefone,
            "email": self.email,
            "cargo": self.cargo
        }


class Negociacao(Base):
    """
    Negociação com um contato.
    Representa o ciclo de vendas desde o primeiro contato até fechamento.
    """
    
    __tablename__ = "negociacoes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contato_id: Mapped[int] = mapped_column(ForeignKey("contatos.id"), nullable=False, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    titulo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[StatusNegociacao] = mapped_column(
        Enum(StatusNegociacao, values_callable=lambda x: [e.value for e in x]),
        default=StatusNegociacao.NOVO,
        nullable=False
    )
    valor_estimado: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relacionamentos
    contato: Mapped["Contato"] = relationship(back_populates="negociacoes")
    empresa: Mapped["Empresa"] = relationship(back_populates="negociacoes")
    mensagens: Mapped[List["Mensagem"]] = relationship(back_populates="negociacao")
    orcamentos: Mapped[List["Orcamento"]] = relationship(back_populates="negociacao", cascade="all, delete-orphan")
    itens: Mapped[List["ItemNegociacao"]] = relationship(back_populates="negociacao", cascade="all, delete-orphan")
    informacoes: Mapped[List["NegociacaoInfo"]] = relationship(back_populates="negociacao", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "contato_id": self.contato_id,
            "empresa_id": self.empresa_id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "status": self.status.value if self.status else None,
            "valor_estimado": str(self.valor_estimado) if self.valor_estimado else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Orcamento(Base):
    """
    Orçamento enviado em uma negociação.
    """
    
    __tablename__ = "orcamentos"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    negociacao_id: Mapped[int] = mapped_column(ForeignKey("negociacoes.id"), nullable=False, index=True)
    numero: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    status: Mapped[StatusOrcamento] = mapped_column(
        Enum(StatusOrcamento, values_callable=lambda x: [e.value for e in x]),
        default=StatusOrcamento.EM_ELABORACAO,
        nullable=False
    )
    valor_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    validade: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relacionamentos
    negociacao: Mapped["Negociacao"] = relationship(back_populates="orcamentos")
    itens: Mapped[List["ItemOrcamento"]] = relationship(back_populates="orcamento", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "negociacao_id": self.negociacao_id,
            "numero": self.numero,
            "status": self.status.value if self.status else None,
            "valor_total": str(self.valor_total) if self.valor_total else None,
            "validade": self.validade.isoformat() if self.validade else None,
            "observacoes": self.observacoes
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    produtos: Mapped[List["Produto"]] = relationship(back_populates="tipo_produto")
    itens_negociacao: Mapped[List["ItemNegociacao"]] = relationship(back_populates="tipo_produto")
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "descricao": self.descricao,
            "ativo": self.ativo
        }


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relacionamentos
    tipo_produto: Mapped["TipoProduto"] = relationship(back_populates="produtos")
    itens_orcamento: Mapped[List["ItemOrcamento"]] = relationship(back_populates="produto")
    itens_negociacao: Mapped[List["ItemNegociacao"]] = relationship(back_populates="produto")
    
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
            "ativo": self.ativo
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
            "desconto_percentual": str(self.desconto_percentual) if self.desconto_percentual else None
        }


class ItemNegociacao(Base):
    """
    Item de uma negociação (pré-orçamento).
    Começa apenas com tipo_produto e quantidade.
    O produto específico é definido quando o modelo for escolhido.
    """
    
    __tablename__ = "itens_negociacao"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    negociacao_id: Mapped[int] = mapped_column(ForeignKey("negociacoes.id"), nullable=False, index=True)
    tipo_produto_id: Mapped[int] = mapped_column(ForeignKey("tipos_produto.id"), nullable=False, index=True)
    produto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("produtos.id"), nullable=True, index=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relacionamentos
    negociacao: Mapped["Negociacao"] = relationship(back_populates="itens")
    tipo_produto: Mapped["TipoProduto"] = relationship(back_populates="itens_negociacao")
    produto: Mapped[Optional["Produto"]] = relationship(back_populates="itens_negociacao")
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "negociacao_id": self.negociacao_id,
            "tipo_produto_id": self.tipo_produto_id,
            "produto_id": self.produto_id,
            "quantidade": str(self.quantidade),
            "observacoes": self.observacoes
        }


class OrigemInfo(str, enum.Enum):
    """Origem da informação coletada."""
    USER = "user"           # Fornecido pelo cliente
    INFERIDO = "inferido"   # Extraído pela LLM
    SISTEMA = "sistema"     # Preenchido pelo sistema (ex: consulta CNPJ)
    ATENDENTE = "atendente" # Preenchido manualmente por atendente humano


class NegociacaoInfo(Base):
    """
    Informações coletadas/pendentes durante uma negociação.
    Modelo chave-valor auditável para rastrear dados da negociação.
    
    Exemplos de chaves: cnpj, nome_contato, localizacao_instalacao,
                       sistema_cliente, prazo_desejado, etc.
    """
    
    __tablename__ = "negociacao_infos"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    negociacao_id: Mapped[int] = mapped_column(ForeignKey("negociacoes.id"), nullable=False, index=True)
    chave: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pendente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    origem: Mapped[Optional[OrigemInfo]] = mapped_column(
        Enum(OrigemInfo, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relacionamentos
    negociacao: Mapped["Negociacao"] = relationship(back_populates="informacoes")
    
    __table_args__ = (
        Index('idx_negociacao_info_chave', 'negociacao_id', 'chave', unique=True),
    )
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "negociacao_id": self.negociacao_id,
            "chave": self.chave,
            "valor": self.valor,
            "pendente": self.pendente,
            "origem": self.origem.value if self.origem else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
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
    origem_classificacao: Mapped[Optional[OrigemClassificacao]] = mapped_column(
        Enum(OrigemClassificacao, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    entidades: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # --- Identificação do remetente no momento do processamento ---
    status_identificacao: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    contato_id_identificado: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contatos.id"), nullable=True
    )
    empresa_id_identificada: Mapped[Optional[int]] = mapped_column(
        ForeignKey("empresas.id"), nullable=True
    )
    negociacao_id_ativa: Mapped[Optional[int]] = mapped_column(
        ForeignKey("negociacoes.id"), nullable=True
    )
    
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
    
    # --- Controle ---
    duracao_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    erro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
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
            "origem_classificacao": (
                self.origem_classificacao.value if self.origem_classificacao else None
            ),
            "entidades": self.entidades,
            "status_identificacao": self.status_identificacao,
            "contato_id_identificado": self.contato_id_identificado,
            "empresa_id_identificada": self.empresa_id_identificada,
            "negociacao_id_ativa": self.negociacao_id_ativa,
            "template_usado": self.template_usado,
            "personalizado_via_llm": self.personalizado_via_llm,
            "llm_provider": self.llm_provider,
            "llm_modelo": self.llm_modelo,
            "llm_tokens_input": self.llm_tokens_input,
            "llm_tokens_output": self.llm_tokens_output,
            "llm_latencia_ms": self.llm_latencia_ms,
            "llm_raw_resposta": self.llm_raw_resposta,
            "duracao_ms": self.duracao_ms,
            "erro": self.erro,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CategoriaReport(str, enum.Enum):
    """Categoria do problema reportado — indica a camada afetada."""
    CLASSIFICACAO = "classificacao"  # intenção/entidades erradas
    FLUXO = "fluxo"                  # orquestração/roteamento errado
    TEMPLATE = "template"            # texto/tom da resposta
    DADOS = "dados"                  # dados incorretos (CNPJ, contato, etc.)
    LLM = "llm"                      # problema com a LLM (timeout, erro, etc.)
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
    processamento_id: Mapped[int] = mapped_column(
        ForeignKey("processamentos_mensagem.id", ondelete="CASCADE"),
        nullable=False,
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
    resolvido_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
            "descricao": self.descricao,
            "autor": self.autor,
            "categoria": self.categoria.value if self.categoria else None,
            "severidade": self.severidade.value if self.severidade else None,
            "status": self.status.value if self.status else None,
            "resolvido": self.resolvido,
            "resolucao": self.resolucao,
            "resolvido_por": self.resolvido_por,
            "resolvido_em": self.resolvido_em.isoformat() if self.resolvido_em else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
