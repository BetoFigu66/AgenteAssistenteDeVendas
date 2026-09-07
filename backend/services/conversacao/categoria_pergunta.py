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

from services.classificador import Intencao
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


async def _responder_produto(ctx: ContextoAcao) -> RespostaGerada:
    """PERGUNTAR_PRODUTO: com atendimento garantido, aplica clarificação/escalonamento
    (REQ-003.7); sem ele, cai no fallback genérico de sempre."""
    p = ctx.processador
    if ctx.db is not None and ctx.atendimento is not None:
        return await p._responder_produto_com_clarificacao(
            ctx.db, ctx.atendimento, ctx.conteudo, dlog=ctx.dlog
        )
    return await p._responder_com_rag(
        conteudo_cliente=ctx.conteudo,
        template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO,
        dlog=ctx.dlog,
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
