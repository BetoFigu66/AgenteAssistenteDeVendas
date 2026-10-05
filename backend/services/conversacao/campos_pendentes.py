"""
Motor de campos pendentes.

Cruza o catálogo declarativo (`catalogo_campos.py`) com o que já foi
capturado no atendimento (`AtendimentoInfo` + `ItemAtendimento`) para decidir
quais campos ainda faltam perguntar. Ao contrário de `catalogo_campos.py`,
este módulo conhece o ORM — é aqui que a ponte catálogo ↔ banco acontece.
"""

from __future__ import annotations

from typing import Optional

from models import Atendimento, StatusPergunta

from .catalogo_campos import (
    CAMPOS,
    DESTINO_ITEM_ATENDIMENTO_MODELO_ID,
    Pergunta,
    campos_do_produto,
)


def nao_perguntar_de_novo(campo: Pergunta, atendimento: Atendimento) -> bool:
    """C3 — True se `campo` já tem valor capturado (não deve ser perguntado de novo).

    Nome espelha o efeito `nao_perguntar_de_novo` do catálogo de conversação
    (`catalogo_conversacao/README.md`).

    Também conta como "não perguntar de novo" o campo cuja pergunta esgotou as
    tentativas na pilha (`Pergunta.max_tentativas`), mesmo sem valor capturado: são
    alertas/orientações que não devem insistir nem bloquear o fluxo.
    """
    if campo.destino == DESTINO_ITEM_ATENDIMENTO_MODELO_ID:
        return atendimento.modelo_ja_resolvido()
    valores = atendimento.valores_capturados()
    if bool(valores.get(campo.chave)):
        return True
    return any(
        p.chave == campo.chave and p.status == StatusPergunta.ESGOTADA.value for p in atendimento.perguntas_pendentes
    )


def campos_pendentes(atendimento: Atendimento) -> list[Pergunta]:
    """C1 — Campos do catálogo ainda pendentes para este atendimento.

    Cruza o catálogo (produto + aplicabilidade, C4) com o que já foi
    capturado (C3 — `nao_perguntar_de_novo`). Retorna lista vazia se o tipo
    de produto do atendimento ainda não foi identificado — não dá para saber
    quais campos pedir sem isso (isso acontece em Esclarecendo, antes da
    transição para Finalizando).

    A ordem é a do catálogo. Qual campo perguntar agora é `proxima_pergunta`, que
    considera também o que já foi perguntado (a pilha).
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
    """C2 — O campo a perguntar agora.

    Se um campo já foi perguntado e segue sem resposta (está aberto na pilha), é ele, a
    começar pelo topo: o cliente precisa ver de novo a pergunta que de fato recebeu.
    Senão, o primeiro pendente na ordem do catálogo.

    Uma pergunta feita vale até ser respondida mesmo fora da aplicabilidade do catálogo:
    "vocês vendem X?" pergunta a faixa de pessoas logo de cara, antes de saber o
    software de ponto do qual ela depende.

    Era o buraco que `pergunta_prioritaria_chave` tapava: sem registro do que foi
    perguntado, um fluxo que pedia a faixa de funcionários antes do modelo via o turno
    seguinte voltar a "cartográfico ou eletrônico?", pergunta que o cliente nunca tinha
    recebido.
    """
    if atendimento.tipo_produto_atual() is None:
        return None
    for pergunta in sorted(atendimento.perguntas_pendentes, key=lambda p: p.ordem, reverse=True):
        campo = CAMPOS.get(pergunta.chave)
        if pergunta.aberta and campo is not None and not nao_perguntar_de_novo(campo, atendimento):
            return campo
    pendentes = campos_pendentes(atendimento)
    return pendentes[0] if pendentes else None
