"""
Regras da fase Finalizando do motor de roteamento (`services/conversacao/motor.py`).

O pipeline F1-F4 (loop de coleta ativa: captura solta, resolução de modelo, dúvida com
retomada, resumo) vive em `estados/finalizando.py::FinalizandoState.tratamento_principal` —
vira a "ação padrão" (wildcard) desta Fase. Só o desfecho G1-G3 (confirmação do resumo →
handoff pra humano) é extraído como Regra própria, exclusiva: é um `if` isolado e de baixo
risco, ao contrário de decompor F3 (dúvida) de verdade, que exigiria estado mutável
adicional pra reproduzir o texto composto sem ganho de produto imediato.

Este módulo é a camada de ROTEAMENTO (decide SE a Ação dispara para este par
Intenção×Fase) — o COMPORTAMENTO (o que a Ação faz) mora em `estados/finalizando.py`
(GRASP Information Expert: `FinalizandoState` é quem "sabe" processar Finalizando, não o
`ProcessadorMensagem` genérico).

Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o funcionamento geral do motor.
"""

from __future__ import annotations

from models import FaseAtendimento

from services.classificador import Intencao
from services.conversacao.campos_pendentes import campos_pendentes
from services.conversacao.estados.finalizando import FINALIZANDO

from .acoes import Acao, ContextoAcao, GrupoAcoes
from .motor import RegraIntencao

_CHAVE_RESUMO_APRESENTADO = "resumo_finalizando_apresentado"


async def _executar_acao_padrao_finalizando(ctx: ContextoAcao):
    return await FINALIZANDO.tratamento_principal(ctx)


def _builder_acao_padrao_finalizando(ctx: ContextoAcao) -> GrupoAcoes:
    return GrupoAcoes(pos=[Acao("acao_padrao_finalizando", _executar_acao_padrao_finalizando)])


async def _executar_confirmar_conclusao(ctx: ContextoAcao):
    return await FINALIZANDO.concluir(ctx)


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
