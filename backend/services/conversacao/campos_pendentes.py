"""
Motor de campos pendentes (MVP Continuidade, jul/2026 — Fase C).

Cruza o catálogo declarativo (`catalogo_campos.py`) com o que já foi
capturado no atendimento (`AtendimentoInfo` + `ItemAtendimento`) para decidir
quais campos ainda faltam perguntar. Ao contrário de `catalogo_campos.py`,
este módulo conhece o ORM — é aqui que a ponte catálogo ↔ banco acontece.
"""

from __future__ import annotations

from typing import Optional

from models import Atendimento

from .catalogo_campos import (
    DESTINO_ITEM_ATENDIMENTO_PRODUTO_ID,
    CampoDef,
    Valores,
    campos_do_produto,
)

# Chave de AtendimentoInfo onde o tipo de produto de interesse é registrado
# hoje (backend/services/processador.py::_atualizar_infos_atendimento).
# Ainda não migrado para ItemAtendimento.tipo_produto_id (ver risco/decisão #1
# em §8 do plano de MVP) — isolado aqui para trocar depois sem afetar o resto
# do módulo. MVP: só relógio de ponto, então o primeiro valor da lista basta.
_CHAVE_TIPOS_PRODUTO = "tipos_produto"


def _tipo_produto_atual(atendimento: Atendimento) -> Optional[str]:
    """Tipo de produto de interesse do atendimento, se já identificado."""
    for info in atendimento.informacoes:
        if info.chave == _CHAVE_TIPOS_PRODUTO and info.valor:
            primeiro = info.valor.split(",")[0].strip()
            return primeiro or None
    return None


def _valores_capturados(atendimento: Atendimento) -> Valores:
    """Snapshot chave -> valor de tudo já capturado em `AtendimentoInfo`."""
    return {info.chave: info.valor for info in atendimento.informacoes if info.valor is not None}


def _modelo_ja_resolvido(atendimento: Atendimento) -> bool:
    """True se algum `ItemAtendimento` do atendimento já tem `produto_id` (modelo) resolvido.

    `modelo_produto` não passa por `AtendimentoInfo` — resolve direto para uma
    linha real do catálogo (ver `CampoDef.destino`).
    """
    return any(item.produto_id is not None for item in atendimento.itens)


def nao_perguntar_de_novo(campo: CampoDef, atendimento: Atendimento) -> bool:
    """C3 — True se `campo` já tem valor capturado (não deve ser perguntado de novo).

    Nome espelha o efeito `nao_perguntar_de_novo` do catálogo de conversação
    (`catalogo_conversacao/README.md`).
    """
    if campo.destino == DESTINO_ITEM_ATENDIMENTO_PRODUTO_ID:
        return _modelo_ja_resolvido(atendimento)
    return bool(_valores_capturados(atendimento).get(campo.chave))


def campos_pendentes(atendimento: Atendimento) -> list[CampoDef]:
    """C1 — Campos do catálogo ainda pendentes para este atendimento.

    Cruza o catálogo (produto + aplicabilidade, C4) com o que já foi
    capturado (C3 — `nao_perguntar_de_novo`). Retorna lista vazia se o tipo
    de produto do atendimento ainda não foi identificado — não dá para saber
    quais campos pedir sem isso (isso acontece em Esclarecendo, antes da
    transição para Finalizando).
    """
    tipo_produto = _tipo_produto_atual(atendimento)
    if tipo_produto is None:
        return []

    valores = _valores_capturados(atendimento)
    return [
        campo
        for campo in campos_do_produto(tipo_produto)
        if campo.se_aplica(tipo_produto, valores) and not nao_perguntar_de_novo(campo, atendimento)
    ]


def proxima_pergunta(atendimento: Atendimento) -> Optional[CampoDef]:
    """C2 — Primeiro campo pendente, na ordem de exibição sugerida do catálogo.

    Não é uma regra de sequência obrigatória — o cliente pode responder
    qualquer campo antes de ser perguntado (cada `Pergunta` reconhece a
    própria resposta). Isto só decide o que perguntar quando nada veio na
    mensagem atual.
    """
    pendentes = campos_pendentes(atendimento)
    return pendentes[0] if pendentes else None
