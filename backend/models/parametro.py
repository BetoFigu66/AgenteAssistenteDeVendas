"""Configuração dinâmica do sistema (parâmetros e modo de execução) e seus históricos."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime


class ModoExecucao(str, enum.Enum):
    """Modo de execução vigente do sistema (REQ-011).

    Eixo ortogonal a `ModoOperacao` (agente/humano é POR ATENDIMENTO): este é uma
    configuração GLOBAL do sistema, lida/persistida via `Parametro`/`ParametroService`
    (`services/parametro_service.py::ParametroService.modo_execucao`), não uma coluna de
    tabela — REQ-011.1 pede persistência sem exigir schema novo.

    - SIMULACAO: sem integração com WhatsApp; toda mensagem gerada pela IA fica
      pendente de aprovação no painel.
    - CONVERSA_CONTROLADA: mensagens do cliente chegam pelo WhatsApp normalmente, mas
      respostas da IA ficam pendentes até aprovação humana antes do envio efetivo.
    - EXECUCAO_NORMAL: operação plena — respostas da IA são enviadas automaticamente,
      sem aprovação manual (REQ-004.10/REQ-011.14 — modo `HUMANO` por atendimento
      continua suprimindo geração automática independente deste modo).
    """

    SIMULACAO = "simulacao"
    CONVERSA_CONTROLADA = "conversa_controlada"
    EXECUCAO_NORMAL = "execucao_normal"


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


class HistoricoModoExecucao(Base):
    """Log de mudanças do modo de execução vigente (REQ-011.3/REQ-011.19).

    Tabela dedicada e simplificada — mesmo padrão de `HistoricoConfiguracao` (REQ-014,
    Fase 7), não a `EventoAtendimento` da Fase 6 (que exige `atendimento_id`, não
    aplicável a configuração global).
    """

    __tablename__ = "historico_modo_execucao"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    modo_anterior: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    modo_novo: Mapped[str] = mapped_column(String(30), nullable=False)
    ator: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "modo_anterior": self.modo_anterior,
            "modo_novo": self.modo_novo,
            "ator": self.ator,
            "timestamp": serialize_utc_datetime(self.timestamp),
        }


class HistoricoConfiguracao(Base):
    """Log de alterações de parâmetros de configuração via API (REQ-014, Fase 7).

    Tabela dedicada e simplificada — mesmo padrão de `HistoricoModoExecucao` (REQ-011),
    não a `EventoAtendimento` da Fase 6 (que exige `atendimento_id`, não aplicável a
    configuração global). Alimentada por `ParametroService.set()`/`set_int()` quando
    chamados com `ator` (endpoints que não passam `ator` não geram registro — hoje é o
    caso só de `PATCH /api/config/execucao`, que já tem sua própria auditoria dedicada
    em `HistoricoModoExecucao`).
    """

    __tablename__ = "historico_configuracao"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    valor_anterior: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_novo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ator: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "valor_anterior": self.valor_anterior,
            "valor_novo": self.valor_novo,
            "ator": self.ator,
            "timestamp": serialize_utc_datetime(self.timestamp),
        }
