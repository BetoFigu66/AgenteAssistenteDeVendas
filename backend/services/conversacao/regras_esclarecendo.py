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

from typing import Optional

from models import AtributoAdicionalModelo, FaseAtendimento, Modelo
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.classificador import Intencao
from services.conversacao.catalogo_campos import CAMPO_FAIXA_FUNCIONARIOS
from services.conversacao.estados.esclarecendo import ESCLARECENDO
from services.conversacao.estados.finalizando import FINALIZANDO, _produto_ids_por_tipos
from services.identificador import StatusIdentificacao
from services.respostas import MensagemId

from .acoes import Acao, ContextoAcao, GrupoAcoes, garantir_atendimento_dispatch
from .motor import RegraIntencao
from .regras_encerramento import CHAVE_FECHAMENTO_PENDENTE

_CHAVE_CATALOGO_PENDENTE = "catalogo_pendente"

# Duplica `services.processador._RAG_CLARIFICACAO_PENDENTE_CHAVE` (import direto causaria
# import circular: `processador.py` importa este módulo em nível de módulo). Mesmo valor —
# se um dia o nome mudar lá, precisa mudar aqui também.
_RAG_CLARIFICACAO_PENDENTE_CHAVE = "rag_clarificacao_pendente"

# REQ-016.10: intenções de "dúvida pura" (categoria_pergunta) — dispara a pergunta de fechamento
# só quando NENHUMA outra intenção de qualificação (ex.: PEDIR_ORCAMENTO) bateu junto na
# mesma mensagem, senão uma pergunta composta ("quero orçamento, mas antes...") geraria um
# "posso ajudar em mais alguma coisa" indevido colado numa qualificação que acabou de abrir.
_INTENCOES_DUVIDA_PURA = frozenset({Intencao.PERGUNTAR_PRECO, Intencao.PERGUNTAR_PRODUTO, Intencao.FORA_CONTEXTO})

_PRODUTO_SINGULAR = {
    "catraca": "catraca",
    "relogio_ponto": "relógio de ponto",
    "cancela": "cancela",
    "leitor_facial": "leitor facial",
    "leitor_biometrico": "leitor biométrico",
    "camera": "câmera",
    "controle_de_acesso": "controle de acesso",
    "controle_por_cartao": "controle por cartão",
    "bastao_de_ronda": "bastão de ronda",
    "roteador": "roteador",
}

_PRODUTO_PLURAL = {
    "catraca": "catracas",
    "relogio_ponto": "relógios",
    "cancela": "cancelas",
    "leitor_facial": "leitores faciais",
    "leitor_biometrico": "leitores biométricos",
    "camera": "câmeras",
    "controle_de_acesso": "controles de acesso",
    "controle_por_cartao": "controles por cartão",
    "bastao_de_ronda": "bastões de ronda",
    "roteador": "roteadores",
}

_TECNOLOGIA_FRASE = {
    ("relogio_ponto", "biometria"): "relógio de ponto biométrico",
    ("relogio_ponto", "facial"): "relógio de ponto facial",
    ("relogio_ponto", "cartao"): "relógio de ponto de cartão",
    ("relogio_ponto", "cartografico"): "relógio de ponto cartográfico",
    ("relogio_ponto", "eletronico"): "relógio de ponto eletrônico",
    ("catraca", "biometria"): "catraca biométrica",
    ("catraca", "facial"): "catraca facial",
    ("catraca", "cartao"): "catraca de cartão",
    ("leitor_biometrico", "biometria"): "leitor biométrico",
    ("leitor_facial", "facial"): "leitor facial",
}


def _frase_produto(tipo_produto: str, tecnologia: Optional[str]) -> tuple[str, str]:
    """Retorna (produto singular, produto plural) para a resposta de disponibilidade.

    Ex.: ("relógio de ponto biométrico", "relógios").
    """
    if tecnologia:
        frase = _TECNOLOGIA_FRASE.get((tipo_produto, tecnologia))
        if frase:
            return frase, _PRODUTO_PLURAL.get(tipo_produto, "produtos")
    singular = _PRODUTO_SINGULAR.get(tipo_produto, tipo_produto.replace("_", " "))
    plural = _PRODUTO_PLURAL.get(tipo_produto, "produtos")
    if tecnologia:
        singular = f"{singular} com {tecnologia}"
    return singular, plural


def _listar_marcas(marcas: list[str]) -> str:
    """Junta marcas em texto legível com artigo. Ex.: ["Topdata", "Control-ID"] ->
    "as marcas Topdata e Control-ID"."""
    if not marcas:
        return "as principais marcas do mercado"
    if len(marcas) == 1:
        return f"a marca {marcas[0]}"
    *iniciais, ultima = marcas
    return f"as marcas {', '.join(iniciais)} e {ultima}"


def _buscar_marcas_produto(
    db: Session,
    tipos_produto: list[str],
    tecnologia: Optional[str] = None,
) -> list[str]:
    """Busca marcas ativas dos modelos que casam com o tipo de produto e, opcionalmente,
    a tecnologia de leitura (ex.: biometria)."""
    produto_ids = _produto_ids_por_tipos(db, tipos_produto)
    if not produto_ids:
        return []

    query = (
        select(Modelo.marca)
        .where(
            Modelo.ativo.is_(True),
            Modelo.marca.isnot(None),
            Modelo.produto_id.in_(produto_ids),
        )
        .distinct()
    )

    if tecnologia:
        query = query.join(AtributoAdicionalModelo).where(
            AtributoAdicionalModelo.ativo.is_(True),
            AtributoAdicionalModelo.chave == "tecnologia_leitura",
            AtributoAdicionalModelo.valor == tecnologia,
        )

    return sorted({m[0].strip() for m in db.execute(query).all() if m[0]})


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


async def _executar_perguntar_disponibilidade(ctx: ContextoAcao):
    """PERGUNTAR_DISPONIBILIDADE: 'vocês vendem X?' / 'trabalham com X?'.

    Confirma que vende, lista marcas do catálogo para o produto/tecnologia mencionados
    e inicia a qualificação perguntando a faixa de funcionários. Aproveita a entrada em
    Finalizando para manter o fluxo de orçamento coeso."""
    p = ctx.processador
    era_novo = ctx.identificacao.status == StatusIdentificacao.NOVO
    entidades = ctx.resultado_class.entidades

    await garantir_atendimento_dispatch(ctx)

    # A disponibilidade respondeu com sucesso ao produto perguntado — qualquer ciclo de
    # clarificação pendente de uma dúvida anterior (categoria_pergunta) não relacionada a esta
    # resposta fica obsoleto. Sem isso, uma dúvida futura sobre o MESMO produto (ex.:
    # "pode explicar as características?") escalaria direto para humano, contando essa
    # disponibilidade como se fosse a "1ª pergunta de clarificação" já feita (REQ-003.7).
    if p._info_atendimento(ctx.db, ctx.atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE):
        p._remover_info_atendimento(ctx.db, ctx.atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE)

    tipo = entidades.tipos_produto[0] if entidades.tipos_produto else None
    tecnologia_bruta = entidades.tipo_leitor_mencionado or entidades.atributos.get("tecnologia_leitura")
    tecnologia = tecnologia_bruta.split(",")[0] if tecnologia_bruta else None

    if tipo:
        marcas = _buscar_marcas_produto(ctx.db, [tipo], tecnologia)
    else:
        marcas = []

    produto, produto_plural = _frase_produto(tipo or "produto", tecnologia)
    ctx_disponibilidade = {
        "marcas": _listar_marcas(marcas),
        "produto": produto,
        "produto_plural": produto_plural,
    }

    partes_finalizando = await FINALIZANDO.entrar(
        ctx,
        mensagem_abertura=MensagemId.DISPONIBILIDADE_PRODUTO,
        abertura_contexto=ctx_disponibilidade,
        primeira_pergunta=CAMPO_FAIXA_FUNCIONARIOS,
    )

    if era_novo:
        if ctx.dlog:
            ctx.dlog.log("rota", "NOVO + PERGUNTAR_DISPONIBILIDADE → composta (Finalizando)")
        ctx_novo = {"nome": entidades.nomes[0] if entidades.nomes else None, "modo": "orcamento"}
        return await p._gerador.gerar_composta([(MensagemId.SAUDACAO_NOVO_CONTATO, ctx_novo), *partes_finalizando])

    if len(partes_finalizando) == 1:
        return partes_finalizando[0]
    return await p._gerador.gerar_composta(partes_finalizando)


def _builder_perguntar_disponibilidade(ctx: ContextoAcao) -> GrupoAcoes:
    if Intencao.PERGUNTAR_DISPONIBILIDADE not in ctx.resultado_class.intencoes:
        return GrupoAcoes()
    if not ctx.resultado_class.entidades.tipos_produto:
        return GrupoAcoes()
    return GrupoAcoes(pos=[Acao("perguntar_disponibilidade", _executar_perguntar_disponibilidade)])


# PERGUNTAR_PRECO/PERGUNTAR_PRODUTO já eram "qualificação" no roteador antigo — mesmo a
# resposta vindo do RAG, o atendimento/contato era garantido e as entidades (tipos_produto
# etc.) registradas como efeito colateral (D2). FORA_CONTEXTO nunca foi qualificação —
# dúvida totalmente fora do domínio não deveria criar atendimento sozinha.
_CATEGORIA_PERGUNTA_GARANTE_ATENDIMENTO = frozenset({Intencao.PERGUNTAR_PRECO, Intencao.PERGUNTAR_PRODUTO})


def _builder_categoria_pergunta(intencao_categoria: Intencao):
    """Fábrica: uma Regra por intenção de categoria_pergunta (preço/produto/fora de contexto),
    todas compartilhando o mesmo wrapper de `_responder_categoria_pergunta` (D1/REQ-002.1B —
    responde via Q&A/RAG imediatamente, nunca exige documento antes).

    Se `PEDIR_ORCAMENTO` bateu junto (registrada antes na lista `pos`) e já produziu
    fragmento, a dúvida não contribui mais nada — sem essa checagem, "Quero orçamento de
    relógio de ponto" gerava uma resposta tripla e redundante (início do orçamento +
    resposta genérica de RAG sobre o mesmo produto colada atrás)."""
    garante_atendimento = intencao_categoria in _CATEGORIA_PERGUNTA_GARANTE_ATENDIMENTO

    async def _executar(ctx: ContextoAcao):
        if ctx.fragmentos_ate_agora:
            return None
        if garante_atendimento:
            await garantir_atendimento_dispatch(ctx)
        return await ctx.processador._responder_categoria_pergunta(
            intencao_categoria, ctx.conteudo, db=ctx.db, atendimento=ctx.atendimento, dlog=ctx.dlog
        )

    def _builder(ctx: ContextoAcao) -> GrupoAcoes:
        return GrupoAcoes(pos=[Acao(f"categoria_pergunta_{intencao_categoria.value}", _executar)])

    return _builder


async def _executar_pedir_catalogo(ctx: ContextoAcao):
    """REQ-003.11 — registrada ANTES das Regras de categoria_pergunta em `REGISTRO_ESCLARECENDO`:
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
    if not (intencoes & _INTENCOES_DUVIDA_PURA):
        return GrupoAcoes()
    if Intencao.PEDIR_ORCAMENTO in intencoes or Intencao.PERGUNTAR_DISPONIBILIDADE in intencoes:
        return GrupoAcoes()
    return GrupoAcoes(pos=[Acao("disparar_fechamento_apos_duvida", _executar_disparar_fechamento)])


REGISTRO_ESCLARECENDO: list[RegraIntencao] = [
    RegraIntencao(
        intencao=Intencao.PERGUNTAR_DISPONIBILIDADE,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_perguntar_disponibilidade,
        nome="perguntar_disponibilidade",
    ),
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
        builder=_builder_categoria_pergunta(Intencao.PERGUNTAR_PRECO),
        nome="categoria_pergunta_preco",
    ),
    RegraIntencao(
        intencao=Intencao.PERGUNTAR_PRODUTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_categoria_pergunta(Intencao.PERGUNTAR_PRODUTO),
        nome="categoria_pergunta_produto",
    ),
    RegraIntencao(
        intencao=Intencao.FORA_CONTEXTO,
        fase=FaseAtendimento.ESCLARECENDO,
        builder=_builder_categoria_pergunta(Intencao.FORA_CONTEXTO),
        nome="categoria_pergunta_fora_contexto",
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
