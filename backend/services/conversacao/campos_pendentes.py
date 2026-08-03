"""
Motor de campos pendentes.

Cruza o catálogo declarativo (`catalogo_campos.py`) com o que já foi
capturado no atendimento (`AtendimentoInfo` + `ItemAtendimento`) para decidir
quais campos ainda faltam perguntar. Ao contrário de `catalogo_campos.py`,
este módulo conhece o ORM — é aqui que a ponte catálogo ↔ banco acontece.
"""

from __future__ import annotations

from typing import Optional

from models import Atendimento

from .catalogo_campos import (
    DESTINO_ITEM_ATENDIMENTO_MODELO_ID,
    Pergunta,
    campos_do_produto,
    chave_perguntado,
)


def nao_perguntar_de_novo(campo: Pergunta, atendimento: Atendimento) -> bool:
    """C3 — True se `campo` já tem valor capturado (não deve ser perguntado de novo).

    Nome espelha o efeito `nao_perguntar_de_novo` do catálogo de conversação
    (`catalogo_conversacao/README.md`).

    Campos **não obrigatórios** (`campo.obrigatorio = False`) também contam como
    "não perguntar de novo" quando já foram perguntados uma vez
    (`chave_perguntado`), mesmo sem valor capturado — são alertas/orientações que
    não devem insistir nem bloquear o fluxo (ver `Pergunta.obrigatorio`).
    """
    if campo.destino == DESTINO_ITEM_ATENDIMENTO_MODELO_ID:
        return atendimento.modelo_ja_resolvido()
    valores = atendimento.valores_capturados()
    if bool(valores.get(campo.chave)):
        return True
    if not campo.obrigatorio and bool(valores.get(chave_perguntado(campo))):
        return True
    return False


def campos_pendentes(atendimento: Atendimento) -> list[Pergunta]:
    """C1 — Campos do catálogo ainda pendentes para este atendimento.

    Cruza o catálogo (produto + aplicabilidade, C4) com o que já foi
    capturado (C3 — `nao_perguntar_de_novo`). Retorna lista vazia se o tipo
    de produto do atendimento ainda não foi identificado — não dá para saber
    quais campos pedir sem isso (isso acontece em Esclarecendo, antes da
    transição para Finalizando).
    """
    tipo_produto = atendimento.tipo_produto_atual()
    if tipo_produto is None:
        return []

    valores = atendimento.valores_capturados()
    return [
        campo
        for campo in campos_do_produto(tipo_produto)
        if campo.se_aplica(tipo_produto, valores) and not nao_perguntar_de_novo(campo, atendimento)
    ]


def proxima_pergunta(atendimento: Atendimento) -> Optional[Pergunta]:
    """C2 — Primeiro campo pendente, na ordem de exibição sugerida do catálogo.

    Não é uma regra de sequência obrigatória — o cliente pode responder
    qualquer campo antes de ser perguntado (cada `Pergunta` reconhece a
    própria resposta). Isto só decide o que perguntar quando nada veio na
    mensagem atual.
    """
    pendentes = campos_pendentes(atendimento)
    return pendentes[0] if pendentes else None
