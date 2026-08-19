"""Reports de problema de um processamento e seu histórico de triagem."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime

if TYPE_CHECKING:
    from .processamento import ProcessamentoMensagem


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


class HistoricoStatusReport(Base):
    """Log de transições de status de um `ReportProblema` (REQ-012, Fase 8).

    Tabela dedicada e simplificada — mesmo padrão de `HistoricoModoExecucao`/
    `HistoricoConfiguracao`, não a `EventoAtendimento` da Fase 6 (que exige
    `atendimento_id` not-null; um report nem sempre resolve a um atendimento,
    ex. reports manuais sem mensagem vinculada).
    """

    __tablename__ = "historico_status_report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports_problema.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status_anterior: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    status_novo: Mapped[str] = mapped_column(String(30), nullable=False)
    ator: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "status_anterior": self.status_anterior,
            "status_novo": self.status_novo,
            "ator": self.ator,
            "timestamp": serialize_utc_datetime(self.timestamp),
        }
