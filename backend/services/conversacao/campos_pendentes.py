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
    CAMPOS,
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


PERGUNTA_PRIORITARIA_CHAVE = "pergunta_prioritaria_chave"
"""Chave de `AtendimentoInfo` usada por fluxos que precisam perguntar um campo fora da
ordem padrão do catálogo (ex.: `PERGUNTAR_DISPONIBILIDADE` pede a faixa de funcionários
antes do modelo — ver `estados/finalizando.py::entrar`, parâmetro `primeira_pergunta`).
Sem persistir essa prioridade, `campos_pendentes()` voltaria a colocar o campo de ordem
mais baixa (ex.: `CAMPO_MODELO`) na frente em qualquer turno seguinte, mesmo que ele nunca
tenha sido de fato perguntado ao cliente nesta conversa — reapresentando uma pergunta
("cartográfico ou eletrônico?") sem relação com o que foi realmente perguntado."""


def campos_pendentes(atendimento: Atendimento) -> list[Pergunta]:
    """C1 — Campos do catálogo ainda pendentes para este atendimento.

    Cruza o catálogo (produto + aplicabilidade, C4) com o que já foi
    capturado (C3 — `nao_perguntar_de_novo`). Retorna lista vazia se o tipo
    de produto do atendimento ainda não foi identificado — não dá para saber
    quais campos pedir sem isso (isso acontece em Esclarecendo, antes da
    transição para Finalizando).

    Se um campo foi marcado como prioritário (`PERGUNTA_PRIORITARIA_CHAVE`) e ainda está
    pendente, ele é movido para o início da lista, mantendo a ordem relativa dos demais.
    """
    tipo_produto = atendimento.tipo_produto_atual()
    if tipo_produto is None:
        return []

    valores = atendimento.valores_capturados()
    pendentes = [
        campo
        for campo in campos_do_produto(tipo_produto)
        if campo.se_aplica(tipo_produto, valores) and not nao_perguntar_de_novo(campo, atendimento)
    ]

    chave_prioritaria = valores.get(PERGUNTA_PRIORITARIA_CHAVE)
    if chave_prioritaria:
        campo_prioritario = CAMPOS.get(chave_prioritaria)
        if campo_prioritario is not None and not nao_perguntar_de_novo(campo_prioritario, atendimento):
            outros = [c for c in pendentes if c.chave != chave_prioritaria]
            return [campo_prioritario, *outros]

    return pendentes


def proxima_pergunta(atendimento: Atendimento) -> Optional[Pergunta]:
    """C2 — Primeiro campo pendente, na ordem de exibição sugerida do catálogo.

    Não é uma regra de sequência obrigatória — o cliente pode responder
    qualquer campo antes de ser perguntado (cada `Pergunta` reconhece a
    própria resposta). Isto só decide o que perguntar quando nada veio na
    mensagem atual.
    """
    pendentes = campos_pendentes(atendimento)
    return pendentes[0] if pendentes else None
