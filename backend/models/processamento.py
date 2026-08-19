"""Registro auditável do processamento de cada mensagem pelo cérebro."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .mensagem import Mensagem
    from .report import ReportProblema


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
    """Intenção principal (maior prioridade) — só para auditoria/exibição simples. O
    roteamento de verdade usa `intencoes` (motor Intenção×Fase→Ações)."""
    intencoes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    """Lista completa e ordenada de todas as intenções que bateram nesta mensagem."""
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
    fase_atendimento: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """Fase do atendimento (esclarecendo/finalizando/em_orcamentacao) no momento em que esta
    mensagem foi processada — não confundir com a fase *atual* do atendimento (que pode já
    ter mudado desde então). Usado para debug ("Raciocínio do cérebro" no painel)."""

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

    # --- Fallback REQ-003.7/REQ-004.9 (Fase 6, REQ-005) ---
    fallback_req003: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """True quando nenhuma Ação do motor (Intenção×Fase→Ações) produziu resposta e o
    cérebro caiu no último recurso (`_fallback_qa_ou_nao_entendi`): QA, escalonamento
    por baixa confiança repetida, ou NAO_ENTENDI genérico."""
    resultado_fallback: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    """Qual desfecho o fallback teve: `qa_encontrado` / `escalado_baixa_confianca` /
    `nao_entendi_aguardando_confirmacao` / `nao_entendi`. `None` quando `fallback_req003`
    é `False`."""
    justificativa_curta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Explicação de uma linha do porquê desse desfecho — alimenta a janela "Raciocínio
    do Cérebro" no painel."""

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
            "intencoes": self.intencoes,
            "confianca": float(self.confianca) if self.confianca is not None else None,
            "confianca_nivel": self.confianca_nivel,
            "origem_classificacao": (self.origem_classificacao.value if self.origem_classificacao else None),
            "entidades": self.entidades,
            "status_identificacao": self.status_identificacao,
            "contato_id_identificado": self.contato_id_identificado,
            "empresa_id_identificada": self.empresa_id_identificada,
            "atendimento_id_ativa": self.atendimento_id_ativa,
            "fase_atendimento": self.fase_atendimento,
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
            "fallback_req003": self.fallback_req003,
            "resultado_fallback": self.resultado_fallback,
            "justificativa_curta": self.justificativa_curta,
            "duracao_ms": self.duracao_ms,
            "erro": self.erro,
            "created_at": serialize_utc_datetime(self.created_at),
        }
