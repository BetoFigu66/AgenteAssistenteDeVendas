"""Testes do gerenciador do motor Intenção×Fase→Ações (`services/conversacao/motor.py`),
com Regras fictícias — não depende de `processador.py`/DB real. Cobre: precedência
global vs. fase, `exclusivo` vence tudo, composição pre+processamento+pos na ordem certa,
`fragmentos_ate_agora` visível para Ações posteriores no mesmo turno.
"""

import asyncio

from models import FaseAtendimento
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.conversacao.acoes import Acao, ContextoAcao, GrupoAcoes
from services.conversacao.motor import RegraIntencao, resolver_e_executar
from services.respostas import RespostaGerada


class _ProcessadorFake:
    """Só o suficiente para o motor chamar `ctx.processador._gerador.gerar(...)` quando
    uma Ação devolve um par (MensagemId, contexto) em vez de RespostaGerada pronta —
    nenhum teste aqui devolve tupla, então isso nunca é exercitado, mas precisa existir."""

    async def _gerador_gerar(self, *args, **kwargs):
        raise AssertionError("não deveria ser chamado nestes testes")


def _ctx(intencoes, fase=None, atendimento=None) -> ContextoAcao:
    resultado_class = ResultadoClassificacao(
        intencoes=intencoes,
        confianca=0.9,
        confianca_nivel=NivelConfianca.ALTA,
        entidades=EntidadesExtraidas(),
        origem="regra",
    )
    identificacao_fake = object()  # não usado pelas Regras fictícias destes testes
    return ContextoAcao(
        db=None,
        telefone="5511999999999",
        conteudo="teste",
        identificacao=identificacao_fake,
        resultado_class=resultado_class,
        processador=_ProcessadorFake(),
        atendimento=atendimento,
    )


def _acao_texto(texto: str, template: str = "TESTE"):
    async def _executar(ctx):
        return RespostaGerada(texto=texto, template_usado=template)

    return _executar


def test_regra_global_e_regra_de_fase_convivem():
    regra_global = RegraIntencao(
        intencao=Intencao.ESCALAR_HUMANO,
        fase=None,
        builder=lambda ctx: GrupoAcoes(exclusivo=[Acao("global", _acao_texto("global"))]),
        nome="teste_global",
    )
    regra_fase = RegraIntencao(
        intencao=Intencao.PEDIR_ORCAMENTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("fase", _acao_texto("fase"))]),
        nome="teste_fase",
    )
    ctx = _ctx([Intencao.PEDIR_ORCAMENTO])
    resposta = asyncio.run(
        resolver_e_executar(ctx, [regra_global], {FaseAtendimento.ESCLARECENDO: [regra_fase]})
    )
    assert resposta.texto == "fase"


def test_exclusivo_suprime_pre_processamento_pos():
    regra_exclusiva = RegraIntencao(
        intencao=Intencao.ESCALAR_HUMANO,
        fase=None,
        builder=lambda ctx: GrupoAcoes(exclusivo=[Acao("escalar", _acao_texto("escalado"))]),
        nome="escalar",
    )
    regra_pos = RegraIntencao(
        intencao=Intencao.PERGUNTAR_PRODUTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("produto", _acao_texto("nao deveria aparecer"))]),
        nome="produto",
    )
    ctx = _ctx([Intencao.ESCALAR_HUMANO, Intencao.PERGUNTAR_PRODUTO])
    resposta = asyncio.run(
        resolver_e_executar(ctx, [regra_exclusiva], {FaseAtendimento.ESCLARECENDO: [regra_pos]})
    )
    assert resposta.texto == "escalado"


def test_ordem_pre_processamento_pos_e_respeitada():
    regra_pos = RegraIntencao(
        intencao=Intencao.SAUDACAO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("pos", _acao_texto("C"))]),
        nome="pos",
    )
    regra_pre = RegraIntencao(
        intencao=Intencao.SAUDACAO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pre=[Acao("pre", _acao_texto("A"))]),
        nome="pre",
    )
    regra_proc = RegraIntencao(
        intencao=Intencao.SAUDACAO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(processamento=[Acao("proc", _acao_texto("B"))]),
        nome="proc",
    )
    ctx = _ctx([Intencao.SAUDACAO])
    # Registradas fora de ordem de propósito — o motor deve montar pre+processamento+pos
    # independente da ordem de registro das regras, só respeitando o TIPO de cada ação.
    resposta = asyncio.run(
        resolver_e_executar(
            ctx, [], {FaseAtendimento.ESCLARECENDO: [regra_pos, regra_pre, regra_proc]}
        )
    )
    assert resposta.texto == "A\n\nB\n\nC"
    assert resposta.template_usado == "TESTE+TESTE+TESTE"


def test_fragmentos_ate_agora_visivel_para_acao_posterior_no_mesmo_turno():
    """A ação padrão (wildcard) só age se nada respondeu ainda — simula exatamente o
    achado #1 do plano: greeting/produto respondem primeiro, o "fallback" olha
    `ctx.fragmentos_ate_agora` e se cala."""

    async def _acao_produto(ctx):
        return RespostaGerada(texto="resposta do produto", template_usado="PRODUTO")

    async def _acao_padrao(ctx):
        if ctx.fragmentos_ate_agora:
            return None
        return RespostaGerada(texto="pedido de documento", template_usado="DOC")

    regra_produto = RegraIntencao(
        intencao=Intencao.PERGUNTAR_PRODUTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("produto", _acao_produto)]),
        nome="produto",
    )
    regra_padrao = RegraIntencao(
        intencao=None,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("padrao", _acao_padrao)]),
        nome="padrao",
    )
    # regra_padrao registrada DEPOIS de regra_produto — ordem de registro importa.
    ctx = _ctx([Intencao.PERGUNTAR_PRODUTO])
    resposta = asyncio.run(
        resolver_e_executar(ctx, [], {FaseAtendimento.ESCLARECENDO: [regra_produto, regra_padrao]})
    )
    assert resposta.texto == "resposta do produto"
    assert "pedido de documento" not in resposta.texto


def test_fragmentos_ate_agora_vazio_acao_padrao_age():
    async def _acao_padrao(ctx):
        if ctx.fragmentos_ate_agora:
            return None
        return RespostaGerada(texto="pedido de documento", template_usado="DOC")

    regra_padrao = RegraIntencao(
        intencao=None,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("padrao", _acao_padrao)]),
        nome="padrao",
    )
    ctx = _ctx([Intencao.DESCONHECIDO])
    resposta = asyncio.run(resolver_e_executar(ctx, [], {FaseAtendimento.ESCLARECENDO: [regra_padrao]}))
    assert resposta.texto == "pedido de documento"


def test_fase_efetiva_sem_atendimento_e_esclarecendo():
    regra = RegraIntencao(
        intencao=Intencao.SAUDACAO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=lambda ctx: GrupoAcoes(pos=[Acao("x", _acao_texto("bateu"))]),
        nome="x",
    )
    ctx = _ctx([Intencao.SAUDACAO], atendimento=None)
    resposta = asyncio.run(resolver_e_executar(ctx, [], {FaseAtendimento.ESCLARECENDO: [regra]}))
    assert resposta.texto == "bateu"


def test_nenhuma_regra_bate_retorna_none():
    ctx = _ctx([Intencao.DESCONHECIDO])
    resposta = asyncio.run(resolver_e_executar(ctx, [], {}))
    assert resposta is None


def test_acao_que_devolve_none_nao_produz_fragmento():
    async def _silenciosa(ctx):
        return None

    regra = RegraIntencao(
        intencao=Intencao.FORNECER_NOME,
        fase=None,
        builder=lambda ctx: GrupoAcoes(pre=[Acao("silenciosa", _silenciosa)]),
        nome="silenciosa",
    )
    ctx = _ctx([Intencao.FORNECER_NOME])
    resposta = asyncio.run(resolver_e_executar(ctx, [regra], {}))
    assert resposta is None
    assert ctx.fragmentos_ate_agora == []
