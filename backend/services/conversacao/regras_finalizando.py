"""
Regras da fase Finalizando do motor de roteamento (`services/conversacao/motor.py`).

O pipeline F1-F4 (loop de coleta ativa: captura solta, resolução de modelo, dúvida com
retomada, resumo) continua vivendo em `ProcessadorMensagem._processar_finalizando()` quase
verbatim — vira a "ação padrão" (wildcard) desta Fase. Só o desfecho G1-G3 (confirmação do
resumo → handoff pra humano) é extraído como Regra própria, exclusiva: é um `if` isolado e
de baixo risco, ao contrário de decompor F3 (dúvida) de verdade, que exigiria estado
mutável adicional pra reproduzir o texto composto sem ganho de produto imediato.
"""

from __future__ import annotations

from models import FaseAtendimento

from services.classificador import Intencao
from services.conversacao.campos_pendentes import campos_pendentes

from .acoes import Acao, ContextoAcao, GrupoAcoes
from .motor import RegraIntencao

_CHAVE_RESUMO_APRESENTADO = "resumo_finalizando_apresentado"


async def _executar_acao_padrao_finalizando(ctx: ContextoAcao):
    return await ctx.processador._processar_finalizando(
        ctx.db, ctx.atendimento, ctx.conteudo, ctx.resultado_class, dlog=ctx.dlog
    )


def _builder_acao_padrao_finalizando(ctx: ContextoAcao) -> GrupoAcoes:
    return GrupoAcoes(pos=[Acao("acao_padrao_finalizando", _executar_acao_padrao_finalizando)])


async def _executar_confirmar_conclusao(ctx: ContextoAcao):
    return await ctx.processador._concluir_finalizando(ctx.db, ctx.atendimento, dlog=ctx.dlog)


def _builder_confirmar(ctx: ContextoAcao) -> GrupoAcoes:
    """G1-G3: CONFIRMAR só conclui o handoff se o resumo (F4) já foi apresentado e não há
    mais nada pendente — senão devolve grupo vazio e a "ação padrão" trata normalmente
    (ex.: CONFIRMAR pode também ser uma resposta solta a algum campo ainda pendente)."""
    p = ctx.processador
    atendimento = ctx.atendimento
    if not atendimento:
        return GrupoAcoes()
    if campos_pendentes(atendimento):
        return GrupoAcoes()
    if not p._info_atendimento(ctx.db, atendimento.id, "tipos_produto"):
        return GrupoAcoes()
    if not p._info_atendimento(ctx.db, atendimento.id, _CHAVE_RESUMO_APRESENTADO):
        return GrupoAcoes()
    return GrupoAcoes(exclusivo=[Acao("confirmar_conclusao_finalizando", _executar_confirmar_conclusao)])


REGISTRO_FINALIZANDO: list[RegraIntencao] = [
    RegraIntencao(
        intencao=Intencao.CONFIRMAR,
        fase=FaseAtendimento.FINALIZANDO,
        builder=_builder_confirmar,
        nome="confirmar_conclusao_finalizando",
    ),
    RegraIntencao(
        intencao=None,
        fase=FaseAtendimento.FINALIZANDO,
        builder=_builder_acao_padrao_finalizando,
        nome="acao_padrao_finalizando",
    ),
]
