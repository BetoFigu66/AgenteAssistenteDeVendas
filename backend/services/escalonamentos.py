"""
Registro do gatilho/evidências de cada escalonamento e avaliação humana (REQ-004.5B/5C).

Quem decide escalar continua sendo `ProcessadorMensagem._escalar_atendimento`; este módulo
só grava o `Escalonamento` ligado ao evento e trata a avaliação feita no painel.

Regra das evidências: valores extraídos, limiares vigentes, intenção/confiança e origem da
classificação. Nunca o texto da mensagem (ele já está em `mensagens`, e o vínculo basta).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Sequence

from models import (
    GATILHO_UNICO_POR_MOTIVO,
    Atendimento,
    AvaliacaoEscalonamento,
    Escalonamento,
    EventoAtendimento,
    GatilhoEscalonamento,
    MotivoEscalonamento,
)
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from services.classificador import ResultadoClassificacao


def evidencias_da_classificacao(resultado_class: Optional["ResultadoClassificacao"]) -> dict[str, Any]:
    """Intenções, confiança e origem (regra/llm) da classificação da mensagem que
    provocou o escalonamento. Vazio quando não há classificação (takeover manual)."""
    if resultado_class is None:
        return {}
    return {
        "intencoes": [i.value for i in resultado_class.intencoes],
        "confianca": round(float(resultado_class.confianca), 4),
        "confianca_nivel": resultado_class.confianca_nivel.value,
        "origem_classificacao": resultado_class.origem,
    }


def registrar_escalonamento(
    db: Session,
    atendimento: Atendimento,
    *,
    motivo: MotivoEscalonamento,
    ator: str,
    evento: Optional[EventoAtendimento] = None,
    gatilhos: Optional[Sequence[GatilhoEscalonamento]] = None,
    evidencias: Optional[dict[str, Any]] = None,
    mensagem_id: Optional[int] = None,
    processamento_id: Optional[int] = None,
) -> Escalonamento:
    """Grava o `Escalonamento` na mesma transação do evento `escalado` (só `flush`, como
    `registrar_evento_atendimento`).

    Sem `gatilhos`, usa o gatilho único do motivo (`GATILHO_UNICO_POR_MOTIVO`); projeto
    complexo não tem gatilho único e fica com lista vazia se o chamador não disser quais
    condições dispararam. `mensagem_id`/`processamento_id` ausentes aqui são preenchidos
    pelo back-fill do fim de `ProcessadorMensagem.processar()`, junto com os do evento.
    """
    if gatilhos is None:
        unico = GATILHO_UNICO_POR_MOTIVO.get(motivo)
        gatilhos = [unico] if unico else []
    escalonamento = Escalonamento(
        atendimento_id=atendimento.id,
        evento_id=evento.id if evento is not None else None,
        mensagem_id=mensagem_id,
        processamento_id=processamento_id,
        motivo=motivo.value,
        gatilhos=[g.value for g in gatilhos],
        evidencias=dict(evidencias or {}),
        ator=ator,
    )
    db.add(escalonamento)
    db.flush()
    return escalonamento


def avaliar_escalonamento(
    escalonamento: Escalonamento,
    *,
    avaliacao: Optional[AvaliacaoEscalonamento],
    comentario: Optional[str],
    avaliado_por: str,
) -> Escalonamento:
    """REQ-004.5C: grava a avaliação (vale a última). `avaliacao=None` desfaz, voltando
    a "não avaliado" (limpa também comentário, autor e data)."""
    if avaliacao is None:
        escalonamento.avaliacao = None
        escalonamento.avaliacao_comentario = None
        escalonamento.avaliado_por = None
        escalonamento.avaliado_em = None
        return escalonamento
    escalonamento.avaliacao = avaliacao.value
    escalonamento.avaliacao_comentario = (comentario or "").strip() or None
    escalonamento.avaliado_por = avaliado_por
    escalonamento.avaliado_em = utc_now()
    # PENDENTE (decisão do Beto): um escalonamento "indevido" deve abrir ReportProblema
    # automaticamente? Por ora só registra a avaliação.
    return escalonamento
