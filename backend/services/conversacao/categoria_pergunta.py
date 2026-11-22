"""Comportamento de "categoria_pergunta" (REQ-002.1, categoria 3 do requisito formal —
dúvida sobre produto/preço/fora de contexto; renomeada em código pra não carregar o número
mágico, ver `.claude/skills/revisao-codigo/diretrizes.md` D03/D04).

Dono único do mapeamento "intenção → comportamento" desse grupo. Antes vivia em
`ProcessadorMensagem._responder_categoria3*` (achado de review D02/D03 — comportamento que
varia por valor de `Intencao` decidido de fora do lugar certo); agora mora aqui, perto de
onde a decisão "isso é uma dúvida de categoria_pergunta" já é tomada
(`regras_esclarecendo.py`), em vez de dentro do orquestrador genérico.

Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o motor Intenção×Fase→Ações; este
módulo é o "dono" só do sub-grupo de intenções que REQ-002.1 chama de categoria 3.
"""

from __future__ import annotations

from typing import Optional

from models import Modelo

from services.catalogo_produtos import produto_ids_por_tipos
from services.classificador import (
    Intencao,
    pedido_de_detalhes,
    pedido_lista_produtos,
    pedido_visao_geral_modelos,
    pergunta_compatibilidade,
)
from services.rag import DocumentoRecuperado
from services.respostas import MensagemId, RespostaGerada

from .acoes import ContextoAcao


def _anexar_trechos_para_auditoria(
    resposta: RespostaGerada,
    trechos: list[DocumentoRecuperado],
) -> None:
    """Popula `trechos_rag` e `rag_score_maximo` sem alterar o texto da resposta.

    Usado quando a RAG e acionada apenas para auditoria (ex: PERGUNTAR_PRECO),
    mantendo o template padrao como resposta ao cliente.
    """
    if not trechos:
        return
    resumo = [
        {
            "id": getattr(t, "id", None),
            "id_externo": getattr(t, "id_externo", None),
            "tipo": getattr(t, "tipo", None),
            "titulo": getattr(t, "titulo", None),
            "score": float(getattr(t, "score", 0.0) or 0.0),
            "distancia": float(getattr(t, "distancia", 0.0) or 0.0),
            "url": (getattr(t, "metadados", None) or {}).get("url"),
        }
        for t in trechos
    ]
    resposta.rag_utilizada = True
    resposta.trechos_rag = resumo
    resposta.rag_score_maximo = max(r["score"] for r in resumo)


async def _responder_preco(ctx: ContextoAcao) -> RespostaGerada:
    """PERGUNTAR_PRECO (Plano v1): a resposta é sempre o template padrão de
    encaminhamento. Ainda assim, roda a RAG para registrar trechos relacionados em
    auditoria."""
    p = ctx.processador
    trechos_preco = await p._retrieval.buscar_trechos(ctx.conteudo, dlog=ctx.dlog)
    resposta = await p._gerador.gerar(
        MensagemId.PRECO_NAO_NEGOCIADO,
        personalizar=True,
        mensagem_cliente=ctx.conteudo,
    )
    _anexar_trechos_para_auditoria(resposta, trechos_preco)
    return resposta


def _consulta_rag(ctx: ContextoAcao) -> str:
    """O texto consultado na base. Um pedido genérico de detalhes ("pode me fornecer mais
    detalhes?") não cita o produto e não acha nada na base; sem produto na própria
    mensagem, consulta pelo produto do atendimento (o "bastão de ronda" que acabou de ser
    apresentado)."""
    if not pedido_de_detalhes(ctx.conteudo) or ctx.resultado_class.entidades.tipos_produto:
        return ctx.conteudo
    if ctx.atendimento is None:
        return ctx.conteudo
    tipos = ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, "tipos_produto")
    if not tipos:
        return ctx.conteudo
    # Import tardio: `regras_esclarecendo` importa este módulo.
    from .regras_esclarecendo import _PRODUTO_SINGULAR

    tipo = tipos.split(",")[0].strip()
    return _PRODUTO_SINGULAR.get(tipo, tipo.replace("_", " "))


# Mesma chave de `processador._RAG_CLARIFICACAO_PENDENTE_CHAVE` (ver o espelho em
# `regras_esclarecendo.py`).
_RAG_CLARIFICACAO_PENDENTE_CHAVE = "rag_clarificacao_pendente"

_TECNOLOGIA_LEGIVEL = {
    "facial": "reconhecimento facial",
    "biometria": "biometria",
    "cartao": "cartão de proximidade",
    "qr_code": "QR Code",
    "barras": "código de barras",
}


def _tipo_produto_da_pergunta(ctx: ContextoAcao) -> Optional[str]:
    """O tipo citado na mensagem ou, sem ele, o do atendimento."""
    if ctx.resultado_class.entidades.tipos_produto:
        return ctx.resultado_class.entidades.tipos_produto[0]
    if ctx.db is None or ctx.atendimento is None:
        return None
    tipos = ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, "tipos_produto")
    return tipos.split(",")[0].strip() if tipos else None


def _linha_modelo(modelo: Modelo) -> str:
    """"- Catraca X: reconhecimento facial, aplicação típica em academias"."""
    tecnologias = [
        _TECNOLOGIA_LEGIVEL.get(a.valor, a.valor)
        for a in modelo.atributos
        if a.ativo and a.chave == "tecnologia_leitura"
    ]
    detalhes = []
    if tecnologias:
        detalhes.append(" e ".join(tecnologias))
    if modelo.aplicacao:
        detalhes.append(f"aplicação típica em {modelo.aplicacao[:1].lower()}{modelo.aplicacao[1:]}")
    return f"- {modelo.descricao}: {', '.join(detalhes)}" if detalhes else f"- {modelo.descricao}"


async def _responder_visao_geral(ctx: ContextoAcao, pedido: bool = False) -> Optional[RespostaGerada]:
    """Report #1435: "como cada modelo de catraca funciona?" pede a linha toda, e nenhum
    trecho isolado da base passa do limiar da RAG para uma pergunta assim (caía no pedido
    de clarificação e depois escalava). O catálogo tem o que foi pedido: marca, tecnologia
    de leitura e aplicação de cada modelo. `None` quando não é visão geral ou o catálogo
    não tem modelos do tipo (segue para a RAG). `pedido=True` dispensa o texto de visão
    geral: quem chama já sabe que a linha toda serve de resposta."""
    if ctx.db is None or not (pedido or pedido_visao_geral_modelos(ctx.conteudo)):
        return None
    tipo = _tipo_produto_da_pergunta(ctx)
    produto_ids = produto_ids_por_tipos(ctx.db, [tipo]) if tipo else []
    if not produto_ids:
        return None
    modelos = (
        ctx.db.query(Modelo)
        .filter(Modelo.ativo.is_(True), Modelo.produto_id.in_(produto_ids))
        .all()
    )
    if not modelos:
        return None

    por_marca: dict[str, list[Modelo]] = {}
    # Modelos sem marca vão por último.
    for modelo in sorted(modelos, key=lambda m: (m.marca is None, (m.marca or "").lower(), m.descricao.lower())):
        por_marca.setdefault(modelo.marca or "Outros modelos", []).append(modelo)
    blocos = [
        "\n".join([f"{marca}:", *(_linha_modelo(m) for m in lista)]) for marca, lista in por_marca.items()
    ]

    # Pergunta respondida: um ciclo de clarificação pendente (REQ-003.7) fica obsoleto.
    p = ctx.processador
    atendimento = ctx.atendimento
    if atendimento is not None and p._info_atendimento(ctx.db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE):
        p._remover_info_atendimento(ctx.db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE)
    if ctx.dlog:
        ctx.dlog.log("categoria_pergunta", f"visão geral de {tipo} → {len(modelos)} modelos do catálogo")

    # Import tardio: `regras_esclarecendo` importa este módulo.
    from .regras_esclarecendo import _PRODUTO_SINGULAR

    return await p._gerador.gerar(
        MensagemId.MODELOS_DO_PRODUTO,
        {"produto": _PRODUTO_SINGULAR.get(tipo, tipo.replace("_", " ")), "lista": "\n\n".join(blocos)},
    )


# "Controle de acesso" não é uma linha da tabela `produtos`, é uma família delas: perguntar
# pelos produtos de controle de acesso é perguntar por estas linhas (report #1736).
_LINHAS_DA_FAMILIA = {
    "controle_de_acesso": (
        "catraca", "cancela", "leitor_facial", "leitor_biometrico", "leitor_qr_code", "controle_por_cartao",
    ),
}


async def _responder_lista_produtos(ctx: ContextoAcao) -> Optional[RespostaGerada]:
    """Report #1736: "quais produtos vocês vendem para controle de acesso?" pede o que há
    na linha (catraca biométrica, catraca facial, cancela...), ainda sem marcas. Lista cada
    linha da família pelas tecnologias de leitura dos modelos ativos do catálogo. `None`
    quando não é esse pedido ou o catálogo não tem nada (segue para a visão geral e a RAG)."""
    # Só a linha citada na mensagem: "quais produtos a Inforrel vende?" é sobre a empresa
    # toda e fica com o Q&A/RAG, não com o produto do atendimento.
    tipos = ctx.resultado_class.entidades.tipos_produto
    if ctx.db is None or not tipos or not pedido_lista_produtos(ctx.conteudo):
        return None
    tipo = tipos[0]

    # Import tardio: `regras_esclarecendo` importa este módulo.
    from .regras_esclarecendo import _PRODUTO_SINGULAR, _TECNOLOGIA_FRASE

    itens: list[str] = []
    for linha in _LINHAS_DA_FAMILIA.get(tipo, (tipo,)):
        produto_ids = produto_ids_por_tipos(ctx.db, [linha])
        modelos = (
            ctx.db.query(Modelo).filter(Modelo.ativo.is_(True), Modelo.produto_id.in_(produto_ids)).all()
            if produto_ids
            else []
        )
        if not modelos:
            continue
        nome = _PRODUTO_SINGULAR.get(linha, linha.replace("_", " "))
        tecnologias = sorted(
            {a.valor for m in modelos for a in m.atributos if a.ativo and a.chave == "tecnologia_leitura"}
        )
        frases = [
            _TECNOLOGIA_FRASE.get((linha, t)) or f"{nome} com {_TECNOLOGIA_LEGIVEL.get(t, t)}" for t in tecnologias
        ] or [nome]
        for frase in frases:
            item = f"- {frase[:1].upper()}{frase[1:]}"
            if item not in itens:
                itens.append(item)
    if not itens:
        return None

    p = ctx.processador
    atendimento = ctx.atendimento
    if atendimento is not None and p._info_atendimento(ctx.db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE):
        p._remover_info_atendimento(ctx.db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE)
    if ctx.dlog:
        ctx.dlog.log("categoria_pergunta", f"lista de produtos de {tipo} → {len(itens)} itens do catálogo")
    return await p._gerador.gerar(
        MensagemId.PRODUTOS_DA_LINHA,
        {"produto": _PRODUTO_SINGULAR.get(tipo, tipo.replace("_", " ")), "lista": "\n".join(itens)},
    )


async def _responder_produto(ctx: ContextoAcao) -> RespostaGerada:
    """PERGUNTAR_PRODUTO: com atendimento garantido, aplica clarificação/escalonamento
    (REQ-003.7); sem ele, cai no fallback genérico de sempre.

    Compatibilidade com sistema de terceiro nunca vai para a RAG: a regra de negócio é
    encaminhar para validação técnica, sem afirmar nem negar."""
    p = ctx.processador
    if pergunta_compatibilidade(ctx.conteudo):
        if ctx.dlog:
            ctx.dlog.log("categoria_pergunta", "pergunta de compatibilidade → COMPATIBILIDADE_SISTEMA")
        return await p._gerador.gerar(MensagemId.COMPATIBILIDADE_SISTEMA)
    lista = await _responder_lista_produtos(ctx)
    if lista is not None:
        return lista
    visao_geral = await _responder_visao_geral(ctx)
    if visao_geral is not None:
        return visao_geral
    if ctx.db is not None and ctx.atendimento is not None:
        # Report #1583: "não conheço, pode explicar?" logo depois das marcas apresentadas.
        # Sem trecho na base, pedir "explique com outras palavras" não ajuda: o catálogo
        # explica a linha (marcas, tecnologia e aplicação de cada modelo).
        sem_conteudo = (lambda: _responder_visao_geral(ctx, pedido=True)) if pedido_de_detalhes(ctx.conteudo) else None
        return await p._responder_produto_com_clarificacao(
            ctx.db,
            ctx.atendimento,
            ctx.conteudo,
            dlog=ctx.dlog,
            resultado_class=ctx.resultado_class,
            consulta=_consulta_rag(ctx),
            sem_conteudo=sem_conteudo,
        )
    return await p._responder_com_rag(
        conteudo_cliente=ctx.conteudo,
        template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO,
        dlog=ctx.dlog,
    )


async def _responder_prazo(ctx: ContextoAcao) -> RespostaGerada:
    """PERGUNTAR_PRAZO no meio da coleta (Finalizando): o mesmo template sem compromisso do
    Esclarecendo (regra de negócio: nunca prometer prazo)."""
    return await ctx.processador._gerador.gerar(
        MensagemId.PRAZO_NAO_PROMETIDO, personalizar=True, mensagem_cliente=ctx.conteudo,
    )


async def _responder_fora_contexto(ctx: ContextoAcao) -> RespostaGerada:
    """FORA_CONTEXTO — e qualquer intenção de categoria_pergunta não mapeada
    explicitamente em `_HANDLERS` (mesmo fallback que o `else` implícito cobria antes)."""
    p = ctx.processador
    return await p._responder_com_rag(
        conteudo_cliente=ctx.conteudo,
        template_fallback=MensagemId.FORA_CONTEXTO,
        dlog=ctx.dlog,
    )


_HANDLERS = {
    Intencao.PERGUNTAR_PRECO: _responder_preco,
    Intencao.PERGUNTAR_PRAZO: _responder_prazo,
    Intencao.PERGUNTAR_PRODUTO: _responder_produto,
}


async def responder_categoria_pergunta(intencao: Intencao, ctx: ContextoAcao) -> RespostaGerada:
    """Única função de dispatch em runtime deste módulo — usada só onde a intenção não é
    conhecida estaticamente (`estados/finalizando.py::_retomar_apos_duvida`, F3). Os 3
    `RegraIntencao` de `regras_esclarecendo.py` já sabem qual caso é cada um (a fábrica
    `_builder_categoria_pergunta` recebe a intenção fixa) e chamam o handler direto, sem
    passar por aqui — ver D04 (evitar redespachar algo que o chamador já sabia)."""
    handler = _HANDLERS.get(intencao, _responder_fora_contexto)
    return await handler(ctx)
