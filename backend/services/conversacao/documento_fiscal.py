"""
Pedido de CNPJ/CPF ao longo do atendimento (decisão do Beto, 05/10/2026).

O documento é pedido **no início do atendimento, junto com o nome**. Se o cliente não o
der, fica pendente e é pedido **uma vez mais, só no Finalizando** (antes do resumo, ou
antes de transferir um projeto complexo). Em Esclarecendo ele não é repetido: a resposta
sem documento marca `recusado` (`estados/esclarecendo.py`).

Estado em `AtendimentoInfo[documento_fiscal_pendente]`: `solicitado` (pedido no início),
`recusado` (a mensagem seguinte não trouxe documento) e `pedido_finalizando` (a segunda e
última vez). O documento não entra na pilha de perguntas pendentes: CNPJ e CPF se
identificam sozinhos e as Regras globais `FORNECER_CNPJ`/`FORNECER_CPF` os capturam a
qualquer momento, então a pilha não acrescentaria nada; e a retomada após dúvida (D1) o
repetiria em Esclarecendo, contra a regra acima.
"""

from __future__ import annotations

from typing import Optional

from services.respostas import MensagemId

from .acoes import ContextoAcao

CHAVE_DOC_PENDENTE = "documento_fiscal_pendente"
SOLICITADO = "solicitado"
RECUSADO = "recusado"
PEDIDO_FINALIZANDO = "pedido_finalizando"


def _tem_documento(ctx: ContextoAcao) -> bool:
    atendimento = ctx.atendimento
    if ctx.empresa or ctx.pessoa or (atendimento and (atendimento.empresa_id or atendimento.pessoa_id)):
        return True
    entidades = ctx.resultado_class.entidades
    return bool(entidades.cnpjs or entidades.cpfs)


def _estado(ctx: ContextoAcao) -> Optional[str]:
    return ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_DOC_PENDENTE)


def _marcar(ctx: ContextoAcao, estado: str) -> None:
    ctx.processador._salvar_info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_DOC_PENDENTE, estado)


def pedido_inicial(ctx: ContextoAcao) -> Optional[tuple[MensagemId, None]]:
    """A parte que pede o documento no início do atendimento, ou None se ele já foi
    dado ou já foi pedido. Exige `ctx.atendimento`."""
    if _tem_documento(ctx) or _estado(ctx):
        return None
    _marcar(ctx, SOLICITADO)
    if ctx.dlog:
        ctx.dlog.log("documento", "pedido no início do atendimento")
    return (MensagemId.PEDIR_DOCUMENTO, None)


def repedido_devido(ctx: ContextoAcao) -> bool:
    """No Finalizando: o documento ainda falta e a última tentativa não foi feita."""
    return not _tem_documento(ctx) and _estado(ctx) != PEDIDO_FINALIZANDO


def repedir(ctx: ContextoAcao) -> tuple[MensagemId, None]:
    """A segunda e última vez que o documento é pedido."""
    _marcar(ctx, PEDIDO_FINALIZANDO)
    if ctx.dlog:
        ctx.dlog.log("documento", "pedido de novo no Finalizando (última vez)")
    return (MensagemId.PEDIR_DOCUMENTO, None)
