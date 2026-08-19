"""Atendimento (caso/negociação) e as entidades que só existem em função dele."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from models_comportamento import ComportamentoAtendimento
from sqlalchemy import Boolean, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .catalogo import Modelo, Produto
    from .contato import Contato
    from .empresa import Empresa
    from .mensagem import Mensagem
    from .orcamento import Orcamento
    from .pessoa import Pessoa


class StatusAtendimento(str, enum.Enum):
    """Status do atendimento (REQ-016.4)."""

    ATIVO = "ativo"
    ENCERRADO = "encerrado"


class MotivoEncerramento(str, enum.Enum):
    """Motivo de encerramento de um atendimento (REQ-016.4).

    Valores legados de dados anteriores à formalização deste enum
    (`inatividade`, `ganha_legado`, `perdida_legado` — ver migração
    `2026061502_estados_atendimento_ativo_encerrado.py`) continuam aceitos pelo check
    constraint do banco para não quebrar histórico, mas não fazem mais parte do
    vocabulário ativo do código — não gerar novos registros com esses valores.
    """

    CONCLUIDO_PELO_CLIENTE = "concluido_pelo_cliente"
    CONCLUIDO_CONVERSAO = "concluido_conversao"
    ABANDONO = "abandono"
    DESISTENCIA = "desistencia"
    MANUAL_VENDEDOR = "manual_vendedor"


class TipoEventoAtendimento(str, enum.Enum):
    """Tipo de evento auditável de um Atendimento (`EventoAtendimento`, REQ-005 Fase 6).

    String livre (sem CHECK constraint) para admitir novos tipos futuros — ex.:
    `orcamento_criado`/`orcamento_convertido`/`orcamento_perdido` na Fase 14 — sem
    exigir migração de schema, só um novo valor.
    """

    CRIADO = "criado"
    ENCERRADO = "encerrado"
    REABERTO = "reaberto"
    ESCALADO = "escalado"
    MODO_OPERACAO_ALTERADO = "modo_operacao_alterado"
    FASE_ALTERADA = "fase_alterada"


class MotivoEscalonamento(str, enum.Enum):
    """Motivo de escalonamento para modo humano (REQ-004, Fase 5).

    Armazenado como string livre em `Atendimento.motivo_escalonamento` — sem CHECK
    constraint (diferente de `MotivoEncerramento`), "solução simples" até a tabela de
    eventos genérica da Fase 6/REQ-005 existir.
    """

    SOLICITADO_CLIENTE = "solicitado_cliente"
    RECLAMACAO = "reclamacao"
    PROJETO_COMPLEXO = "projeto_complexo"
    BAIXA_CONFIANCA = "baixa_confianca"
    BASE_INSUFICIENTE = "base_insuficiente"
    MANUAL_VENDEDOR = "manual_vendedor"
    MODELO_NAO_RECONHECIDO = "modelo_nao_reconhecido"


class ModoOperacao(str, enum.Enum):
    """Modo de operação do atendimento.

    - AGENTE: sistema gera respostas automáticas (padrão).
    - HUMANO: sistema apenas recebe e registra mensagens; respostas são
      enviadas manualmente pelo operador via interface web.
    """

    AGENTE = "agente"
    HUMANO = "humano"


class FaseAtendimento(str, enum.Enum):
    """Estágio da jornada conversacional guiada (MVP Continuidade, jul/2026).

    Eixo ortogonal a `StatusAtendimento` — complementa REQ-016, não substitui:
    `status` indica se o atendimento está aberto para interação (ativo/encerrado);
    `fase` indica em que ponto do fluxo guiado ele está enquanto ativo. Ver
    `artefatos/analista_de_requisitos/catalogo_conversacao/README.md` e
    `docs/dicionario_termos.md` (entrada "Fase (do atendimento)").

    Fases fora do MVP (`encerrado_por_inatividade`, `encerrado`) ainda não têm
    valor aqui — permanecem só no catálogo até serem implementadas.
    """

    ESCLARECENDO = "esclarecendo"
    FINALIZANDO = "finalizando"
    EM_ORCAMENTACAO = "em_orcamentacao"


class TipoDocumento(str, enum.Enum):
    """Tipo de documento fiscal associado ao atendimento."""

    CPF = "cpf"
    CNPJ = "cnpj"
    INDEFINIDO = "indefinido"


class Atendimento(Base, ComportamentoAtendimento):
    """
    Atendimento com um contato (REQ-016).
    Agrupa conversas e orçamentos de uma mesma demanda do cliente.

    Comportamento derivado do próprio estado (sem I/O, sem colaboradores
    externos) mora em `ComportamentoAtendimento` (models_comportamento.py) —
    separado deste arquivo para que um diff aqui continue significando "mudou
    estrutura de tabela".
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
    # Auditoria mínima das transições (REQ-016.5) — simplificada até a tabela de eventos
    # da Fase 5 (REQ-005) existir; ver docs/plano_implementacao_requisitos_formais_2026-07.md.
    encerrado_em: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    encerrado_por: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reaberto_em: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    reaberto_por: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reabertura_justificativa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Auditoria mínima de escalonamento (REQ-004, Fase 5) — mesmo padrão simplificado
    # dos campos de encerramento acima, sem CHECK constraint (ver MotivoEscalonamento).
    escalado_em: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    escalado_por: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    motivo_escalonamento: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    resumo_escalonamento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modo_operacao: Mapped[ModoOperacao] = mapped_column(
        Enum(ModoOperacao, values_callable=lambda x: [e.value for e in x], name="modooperacao"),
        default=ModoOperacao.AGENTE,
        nullable=False,
        index=True,
    )
    fase: Mapped[FaseAtendimento] = mapped_column(
        Enum(FaseAtendimento, values_callable=lambda x: [e.value for e in x], name="faseatendimento"),
        default=FaseAtendimento.ESCLARECENDO,
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
    eventos: Mapped[List["EventoAtendimento"]] = relationship(
        back_populates="atendimento",
        cascade="all, delete-orphan",
        order_by="EventoAtendimento.timestamp.desc()",
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
            "encerrado_em": serialize_utc_datetime(self.encerrado_em),
            "encerrado_por": self.encerrado_por,
            "reaberto_em": serialize_utc_datetime(self.reaberto_em),
            "reaberto_por": self.reaberto_por,
            "reabertura_justificativa": self.reabertura_justificativa,
            "escalado_em": serialize_utc_datetime(self.escalado_em),
            "escalado_por": self.escalado_por,
            "motivo_escalonamento": self.motivo_escalonamento,
            "resumo_escalonamento": self.resumo_escalonamento,
            "modo_operacao": self.modo_operacao.value if self.modo_operacao else None,
            "fase": self.fase.value if self.fase else None,
            "valor_estimado": str(self.valor_estimado) if self.valor_estimado else None,
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
            "ultima_mensagem_at": serialize_utc_datetime(self.ultima_mensagem_at),
            "numero_atendimento_cliente": self.numero_atendimento_cliente,
        }


class EventoAtendimento(Base):
    """Log auditável e genérico de mudanças de estado de um Atendimento (REQ-005, Fase 6).

    Generaliza os padrões simplificados de auditoria criados nas Fases 1
    (`encerrar_atendimento`/`reabrir_atendimento`) e 5 (`_escalar_atendimento`): cada
    transição continua também atualizando as colunas de "estado atual" no próprio
    `Atendimento` (`encerrado_em`, `motivo_escalonamento` etc.) como snapshot rápido de
    consulta direta, e passa a gravar aqui o histórico completo (múltiplas ocorrências),
    igual ao par Parâmetro (estado atual) + `HistoricoModoExecucao` (log) já usado para o
    modo de execução (REQ-011).
    """

    __tablename__ = "eventos_atendimento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    atendimento_id: Mapped[int] = mapped_column(ForeignKey("atendimentos.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estado_novo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ator: Mapped[str] = mapped_column(String(50), nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mensagem_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mensagens.id"), nullable=True)
    processamento_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("processamentos_mensagem.id"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False, index=True)

    atendimento: Mapped["Atendimento"] = relationship(back_populates="eventos")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "atendimento_id": self.atendimento_id,
            "tipo": self.tipo,
            "estado_anterior": self.estado_anterior,
            "estado_novo": self.estado_novo,
            "ator": self.ator,
            "motivo": self.motivo,
            "mensagem_id": self.mensagem_id,
            "processamento_id": self.processamento_id,
            "timestamp": serialize_utc_datetime(self.timestamp),
        }


class ItemAtendimento(Base):
    """
    Item de um atendimento (pré-orçamento).
    Começa apenas com produto (categoria) e quantidade.
    O modelo específico é definido quando o modelo for escolhido.
    """

    __tablename__ = "itens_atendimento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    atendimento_id: Mapped[int] = mapped_column(ForeignKey("atendimentos.id"), nullable=False, index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False, index=True)
    modelo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("modelos.id"), nullable=True, index=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relacionamentos
    atendimento: Mapped["Atendimento"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship(back_populates="itens_atendimento")
    modelo: Mapped[Optional["Modelo"]] = relationship(back_populates="itens_atendimento")

    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "atendimento_id": self.atendimento_id,
            "produto_id": self.produto_id,
            "modelo_id": self.modelo_id,
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
