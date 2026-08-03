"""
Regras da fase Esclarecendo do motor de roteamento (`services/conversacao/motor.py`).

Unifica o dispatch que antes era diferente por `StatusIdentificacao` (NOVO/SEM_EMPRESA/
identificado) — agora todo contato em Esclarecendo reconhece as mesmas intenções,
independente de já ter fornecido CNPJ/CPF (decisão confirmada: mesma família do bug que
motivou esta migração — um contato novo não deveria ter menos capacidade de resposta só
por ainda não ter mandado documento).

A "ação padrão" (wildcard, registrada por último) é a peça central da correção do bug —
seu comportamento mora em `estados/esclarecendo.py::EsclarecendoState.tratamento_principal`
(este módulo é a camada de ROTEAMENTO, decide SE a Ação dispara; o COMPORTAMENTO mora no
Estado — GRASP Information Expert).

Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o funcionamento geral do motor.
"""

from __future__ import annotations

from models import FaseAtendimento

from services.classificador import Intencao
from services.conversacao.estados.esclarecendo import ESCLARECENDO
from services.conversacao.estados.finalizando import FINALIZANDO
from services.identificador import StatusIdentificacao
from services.respostas import MensagemId

from .acoes import Acao, ContextoAcao, GrupoAcoes, garantir_atendimento_dispatch
from .motor import RegraIntencao
from .regras_encerramento import CHAVE_FECHAMENTO_PENDENTE

_CHAVE_CATALOGO_PENDENTE = "catalogo_pendente"

# REQ-016.10: intenções de "dúvida pura" (categoria 3) — dispara a pergunta de fechamento
# só quando NENHUMA outra intenção de qualificação (ex.: PEDIR_ORCAMENTO) bateu junto na
# mesma mensagem, senão uma pergunta composta ("quero orçamento, mas antes...") geraria um
# "posso ajudar em mais alguma coisa" indevido colado numa qualificação que acabou de abrir.
_INTENCOES_DUVIDA_PURA = frozenset({Intencao.PERGUNTAR_PRECO, Intencao.PERGUNTAR_PRODUTO, Intencao.FORA_CONTEXTO})


async def _executar_pedir_orcamento(ctx: ContextoAcao):
    """PEDIR_ORCAMENTO transita para Finalizando e pergunta o primeiro campo pendente.
    Um contato totalmente novo (`StatusIdentificacao.NOVO`) ganha a saudação de
    boas-vindas junto (mesma composição de sempre); quem já conversava antes não precisa
    ser cumprimentado de novo.

    Builder de Esclarecendo disparando a entrada em Finalizando (`FINALIZANDO.entrar`) é
    inerente à transição E→F, não uma violação da linha roteamento/comportamento — fica
    aqui porque é o builder de Esclarecendo que decide disparar a transição."""
    p = ctx.processador
    era_novo = ctx.identificacao.status == StatusIdentificacao.NOVO
    entidades = ctx.resultado_class.entidades

    await garantir_atendimento_dispatch(ctx)
    partes_finalizando = await FINALIZANDO.entrar(ctx)

    if era_novo:
        if ctx.dlog:
            ctx.dlog.log("rota", "NOVO + PEDIR_ORCAMENTO → composta (Finalizando)")
        ctx_novo = {"nome": entidades.nomes[0] if entidades.nomes else None, "modo": "orcamento"}
        return await p._gerador.gerar_composta([(MensagemId.SAUDACAO_NOVO_CONTATO, ctx_novo), *partes_finalizando])

    if len(partes_finalizando) == 1:
        return partes_finalizando[0]
    return await p._gerador.gerar_composta(partes_finalizando)


# PERGUNTAR_PRECO/PERGUNTAR_PRODUTO já eram "qualificação" no roteador antigo — mesmo a
# resposta vindo do RAG, o atendimento/contato era garantido e as entidades (tipos_produto
# etc.) registradas como efeito colateral (D2). FORA_CONTEXTO nunca foi qualificação —
# dúvida totalmente fora do domínio não deveria criar atendimento sozinha.
_CATEGORIA3_GARANTE_ATENDIMENTO = frozenset({Intencao.PERGUNTAR_PRECO, Intencao.PERGUNTAR_PRODUTO})


def _builder_categoria3(intencao_categoria: Intencao):
    """Fábrica: uma Regra por intenção de categoria 3 (preço/produto/fora de contexto),
    todas compartilhando o mesmo wrapper de `_responder_categoria3` (D1/REQ-002.1B —
    responde via Q&A/RAG imediatamente, nunca exige documento antes).

    Se `PEDIR_ORCAMENTO` bateu junto (registrada antes na lista `pos`) e já produziu
    fragmento, a dúvida não contribui mais nada — sem essa checagem, "Quero orçamento de
    relógio de ponto" gerava uma resposta tripla e redundante (início do orçamento +
    resposta genérica de RAG sobre o mesmo produto colada atrás)."""
    garante_atendimento = intencao_categoria in _CATEGORIA3_GARANTE_ATENDIMENTO

    async def _executar(ctx: ContextoAcao):
        if ctx.fragmentos_ate_agora:
            return None
        if garante_atendimento:
            await garantir_atendimento_dispatch(ctx)
        return await ctx.processador._responder_categoria3(
            intencao_categoria, ctx.conteudo, db=ctx.db, atendimento=ctx.atendimento, dlog=ctx.dlog
        )

    def _builder(ctx: ContextoAcao) -> GrupoAcoes:
        return GrupoAcoes(pos=[Acao(f"categoria3_{intencao_categoria.value}", _executar)])

    return _builder


async def _executar_pedir_catalogo(ctx: ContextoAcao):
    """REQ-003.11 — registrada ANTES das Regras de categoria 3 em `REGISTRO_ESCLARECENDO`:
    "catálogo de catracas" bate tanto em PEDIR_CATALOGO quanto em PERGUNTAR_PRODUTO (a
    palavra "catraca"), e o catálogo deve vencer, não a resposta genérica de dúvida.

    Também é o alvo da resposta "solta" a `PEDIR_TIPO_CATALOGO` (ex.: cliente responde só
    "catracas", sem repetir a palavra "catálogo") — `_builder_pedir_catalogo` decide
    quando isso se aplica, olhando `catalogo_pendente` em `AtendimentoInfo`."""
    if ctx.fragmentos_ate_agora:
        return None
    atendimento = await garantir_atendimento_dispatch(ctx)
    p = ctx.processador
    p._remover_info_atendimento(ctx.db, atendimento.id, _CHAVE_CATALOGO_PENDENTE)
    resposta = await p._responder_pedir_catalogo(ctx.db, ctx.resultado_class, dlog=ctx.dlog)
    if resposta.template_usado == "PEDIR_TIPO_CATALOGO":
        p._salvar_info_atendimento(ctx.db, atendimento.id, _CHAVE_CATALOGO_PENDENTE, "1")
    return resposta


def _builder_pedir_catalogo(ctx: ContextoAcao) -> GrupoAcoes:
    if Intencao.PEDIR_CATALOGO in ctx.resultado_class.intencoes:
        return GrupoAcoes(pos=[Acao("pedir_catalogo", _executar_pedir_catalogo)])
    if (
        ctx.atendimento
        and ctx.resultado_class.entidades.tipos_produto
        and ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, _CHAVE_CATALOGO_PENDENTE)
    ):
        return GrupoAcoes(pos=[Acao("pedir_catalogo", _executar_pedir_catalogo)])
    return GrupoAcoes()


async def _executar_perguntar_prazo(ctx: ContextoAcao):
    await garantir_atendimento_dispatch(ctx)
    return await ctx.processador._gerador.gerar(
        MensagemId.PRAZO_NAO_PROMETIDO, personalizar=True, mensagem_cliente=ctx.conteudo,
    )


async def _executar_aprovar_orcamento(ctx: ContextoAcao):
    await garantir_atendimento_dispatch(ctx)
    return (MensagemId.ORCAMENTO_APROVADO, None)


async def _executar_reprovar_orcamento(ctx: ContextoAcao):
    await garantir_atendimento_dispatch(ctx)
    return (MensagemId.ORCAMENTO_REPROVADO, None)


async def _executar_acao_padrao_esclarecendo(ctx: ContextoAcao):
    return await ESCLARECENDO.tratamento_principal(ctx)


async def _executar_disparar_fechamento(ctx: ContextoAcao):
    """REQ-016.10: dispara "Posso te ajudar em mais alguma coisa?" logo após uma dúvida
    pura ser respondida (nenhuma qualificação em aberto) — não insiste se já está
    aguardando resposta a essa mesma pergunta."""
    atendimento = ctx.atendimento
    if not atendimento or atendimento.fase != FaseAtendimento.ESCLARECENDO:
        return None
    if not ctx.fragmentos_ate_agora:
        return None  # nenhuma dúvida foi respondida ainda nesta mensagem

    p = ctx.processador
    if p._info_atendimento(ctx.db, atendimento.id, CHAVE_FECHAMENTO_PENDENTE) == "aguardando":
        return None  # já perguntado, aguardando resposta — não insiste de novo

    p._salvar_info_atendimento(ctx.db, atendimento.id, CHAVE_FECHAMENTO_PENDENTE, "aguardando")
    if ctx.dlog:
        ctx.dlog.log(
            "esclarecendo",
            f"dúvida respondida sem qualificação aberta → pergunta de fechamento (atendimento {atendimento.id})",
        )
    return (MensagemId.PERGUNTA_FECHAMENTO_ATENDIMENTO, None)


def _builder_disparar_fechamento(ctx: ContextoAcao) -> GrupoAcoes:
    intencoes = set(ctx.resultado_class.intencoes)
    if not (intencoes & _INTENCOES_DUVIDA_PURA) or Intencao.PEDIR_ORCAMENTO in intencoes:
        return GrupoAcoes()
    return GrupoAcoes(pos=[Acao("disparar_fechamento_apos_duvida", _executar_disparar_fechamento)])


REGISTRO_ESCLARECENDO: list[RegraIntencao] = [
    RegraIntencao(
        intencao=Intencao.PEDIR_ORCAMENTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("pedir_orcamento", _executar_pedir_orcamento)]),
        nome="pedir_orcamento",
    ),
    RegraIntencao(
        intencao=None,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_pedir_catalogo,
        nome="pedir_catalogo",
    ),
    RegraIntencao(
        intencao=Intencao.PERGUNTAR_PRECO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_categoria3(Intencao.PERGUNTAR_PRECO),
        nome="categoria3_preco",
    ),
    RegraIntencao(
        intencao=Intencao.PERGUNTAR_PRODUTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_categoria3(Intencao.PERGUNTAR_PRODUTO),
        nome="categoria3_produto",
    ),
    RegraIntencao(
        intencao=Intencao.FORA_CONTEXTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_categoria3(Intencao.FORA_CONTEXTO),
        nome="categoria3_fora_contexto",
    ),
    RegraIntencao(
        intencao=None,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_disparar_fechamento,
        nome="disparar_fechamento_apos_duvida",
    ),
    RegraIntencao(
        intencao=Intencao.PERGUNTAR_PRAZO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("perguntar_prazo", _executar_perguntar_prazo)]),
        nome="perguntar_prazo",
    ),
    RegraIntencao(
        intencao=Intencao.APROVAR_ORCAMENTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("aprovar_orcamento", _executar_aprovar_orcamento)]),
        nome="aprovar_orcamento",
    ),
    RegraIntencao(
        intencao=Intencao.REPROVAR_ORCAMENTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("reprovar_orcamento", _executar_reprovar_orcamento)]),
        nome="reprovar_orcamento",
    ),
    RegraIntencao(
        intencao=None,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("acao_padrao_esclarecendo", _executar_acao_padrao_esclarecendo)]),
        nome="acao_padrao_esclarecendo",
    ),
]
