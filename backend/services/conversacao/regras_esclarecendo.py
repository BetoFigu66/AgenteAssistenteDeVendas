"""
Regras da fase Esclarecendo do motor de roteamento (`services/conversacao/motor.py`).

Unifica o dispatch que antes era diferente por `StatusIdentificacao` (NOVO/SEM_EMPRESA/
identificado) — agora todo contato em Esclarecendo reconhece as mesmas intenções,
independente de já ter fornecido CNPJ/CPF (decisão confirmada: mesma família do bug que
motivou esta migração — um contato novo não deveria ter menos capacidade de resposta só
por ainda não ter mandado documento).

A "ação padrão" (wildcard, registrada por último) é a peça central da correção do bug:
só age quando nada mais respondeu nada (`ctx.fragmentos_ate_agora` vazio) — sem isso,
qualquer pergunta de categoria 3 ganharia um pedido de CNPJ colado atrás, regredindo o D1
(REQ-002.1B: categoria 3 nunca exige documento). Ela também é responsável pela correção
do "documento pendente": em vez de repetir a mesma pergunta de CNPJ/CPF a cada mensagem,
registra a recusa em `AtendimentoInfo` (chave `documento_fiscal_pendente`) e para de
insistir, deixando a conversa seguir normalmente (fallback QA/NAO_ENTENDI).
"""

from __future__ import annotations

from models import FaseAtendimento

from services.classificador import Intencao
from services.identificador import StatusIdentificacao
from services.respostas import MensagemId

from .acoes import Acao, ContextoAcao, GrupoAcoes
from .motor import RegraIntencao
from .regras_encerramento import CHAVE_FECHAMENTO_PENDENTE

_CHAVE_DOC_PENDENTE = "documento_fiscal_pendente"

# REQ-016.10: intenções de "dúvida pura" (categoria 3) — dispara a pergunta de fechamento
# só quando NENHUMA outra intenção de qualificação (ex.: PEDIR_ORCAMENTO) bateu junto na
# mesma mensagem, senão uma pergunta composta ("quero orçamento, mas antes...") geraria um
# "posso ajudar em mais alguma coisa" indevido colado numa qualificação que acabou de abrir.
_INTENCOES_DUVIDA_PURA = frozenset({Intencao.PERGUNTAR_PRECO, Intencao.PERGUNTAR_PRODUTO, Intencao.FORA_CONTEXTO})


async def _garantir_atendimento_dispatch(ctx: ContextoAcao):
    """Garante que `ctx.atendimento` (e `ctx.contato`) existam, criando sob demanda — só
    na hora em que uma Ação realmente precisa persistir algo (lazy: evita poluir a base
    com atendimentos vazios de "oi" solto que nunca evoluem). Muta `ctx` in-place para que
    Ações seguintes no mesmo turno enxerguem o atendimento recém-criado."""
    if ctx.atendimento:
        return ctx.atendimento
    p = ctx.processador
    atendimento = await p._garantir_contato_e_atendimento_qualificacao(
        ctx.db, ctx.telefone, ctx.contato, ctx.resultado_class, dlog=ctx.dlog
    )
    ctx.atendimento = atendimento
    ctx.contato = atendimento.contato
    return atendimento


async def _executar_pedir_orcamento(ctx: ContextoAcao):
    """PEDIR_ORCAMENTO transita para Finalizando e pergunta o primeiro campo pendente.
    Um contato totalmente novo (`StatusIdentificacao.NOVO`) ganha a saudação de
    boas-vindas junto (mesma composição de sempre); quem já conversava antes não precisa
    ser cumprimentado de novo."""
    p = ctx.processador
    era_novo = ctx.identificacao.status == StatusIdentificacao.NOVO
    entidades = ctx.resultado_class.entidades

    atendimento = await _garantir_atendimento_dispatch(ctx)
    partes_finalizando = await p._iniciar_ou_continuar_finalizando(ctx.db, atendimento, dlog=ctx.dlog)

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
            await _garantir_atendimento_dispatch(ctx)
        return await ctx.processador._responder_categoria3(intencao_categoria, ctx.conteudo, dlog=ctx.dlog)

    def _builder(ctx: ContextoAcao) -> GrupoAcoes:
        return GrupoAcoes(pos=[Acao(f"categoria3_{intencao_categoria.value}", _executar)])

    return _builder


async def _executar_perguntar_prazo(ctx: ContextoAcao):
    await _garantir_atendimento_dispatch(ctx)
    return await ctx.processador._gerador.gerar(
        MensagemId.PRAZO_NAO_PROMETIDO, personalizar=True, mensagem_cliente=ctx.conteudo,
    )


async def _executar_aprovar_orcamento(ctx: ContextoAcao):
    await _garantir_atendimento_dispatch(ctx)
    return (MensagemId.ORCAMENTO_APROVADO, None)


async def _executar_reprovar_orcamento(ctx: ContextoAcao):
    await _garantir_atendimento_dispatch(ctx)
    return (MensagemId.ORCAMENTO_REPROVADO, None)


async def _executar_acao_padrao_esclarecendo(ctx: ContextoAcao):
    """Último recurso do turno — só age se nada mais respondeu nada. Trata: (a) SAUDACAO
    pra quem já está identificado (empresa/pessoa), respondendo com o nome; (b) fallback
    QA/NAO_ENTENDI pra quem já está identificado e não disse "oi"; (c) o fluxo de
    documento fiscal pendente pra quem ainda não tem empresa/pessoa vinculada.

    (c) só pergunta documento **uma vez**: se `documento_fiscal_pendente` já está
    "solicitado" e chegamos aqui de novo, é porque esta mensagem não trouxe CNPJ/CPF (se
    tivesse, a regra global `FORNECER_CNPJ`/`FORNECER_CPF` já teria resolvido antes — nunca
    chegaríamos até aqui) — não insiste de novo, marca "recusado" e segue a conversa
    normalmente. Não depende de reconhecer a recusa por palavra (ex.: "não quero
    fornecer ainda" não bate na regra `NEGAR`, que exige a mensagem inteira ser só "não")."""
    if ctx.fragmentos_ate_agora:
        return None
    if ctx.atendimento and ctx.atendimento.fase != FaseAtendimento.ESCLARECENDO:
        return None

    p = ctx.processador

    if ctx.empresa or ctx.pessoa:
        nome = (ctx.contato.nome if ctx.contato else None) or (ctx.pessoa.nome if ctx.pessoa else None)
        if Intencao.SAUDACAO in ctx.resultado_class.intencoes:
            if nome:
                return (MensagemId.SAUDACAO_COM_NOME, {"nome": nome})
            return (MensagemId.PERGUNTAR_NOME, None)
        return await p._fallback_qa_ou_nao_entendi(ctx.conteudo, dlog=ctx.dlog)

    atendimento = await _garantir_atendimento_dispatch(ctx)
    estado_doc = p._info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE)

    if estado_doc in ("solicitado", "recusado"):
        if estado_doc == "solicitado":
            p._salvar_info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE, "recusado")
            if ctx.dlog:
                ctx.dlog.log(
                    "esclarecendo",
                    "documento pedido sem resposta → marcado 'recusado', não insiste mais",
                )
        elif ctx.dlog:
            ctx.dlog.log("esclarecendo", "documento_fiscal_pendente=recusado → não repete, cai no fallback")
        return await p._fallback_qa_ou_nao_entendi(ctx.conteudo, dlog=ctx.dlog)

    p._salvar_info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE, "solicitado")

    if ctx.identificacao.status == StatusIdentificacao.NOVO:
        entidades = ctx.resultado_class.entidades
        ctx_novo = {
            "nome": entidades.nomes[0] if entidades.nomes else None,
            "tem_documento": bool(entidades.cnpjs or entidades.cpfs),
            "modo": "identificacao",
        }
        return (MensagemId.SAUDACAO_NOVO_CONTATO, ctx_novo)

    nome_contato = atendimento.contato.nome if atendimento.contato else None
    return (MensagemId.PERGUNTAR_CNPJ, {"nome": nome_contato})


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
