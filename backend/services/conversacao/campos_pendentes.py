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


def proxima_nunca_perguntada(atendimento: Atendimento) -> Optional[Pergunta]:
    """O primeiro campo pendente que nunca foi perguntado neste atendimento (não tem
    registro na pilha, aberto ou não). Usado quando cada pergunta deve sair uma vez só
    (transferência de projeto complexo adiada)."""
    perguntados = {p.chave for p in atendimento.perguntas_pendentes}
    return next((c for c in campos_pendentes(atendimento) if c.chave not in perguntados), None)


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


# Situação de uma pergunta para o painel, da melhor para a pior: a pergunta vale pela
# melhor mensagem que a levou (reapresentada e aprovada na segunda vez = enviada).
ENVIADA = "enviada"
AGUARDANDO_APROVACAO = "aguardando_aprovacao"
REPROVADA = "reprovada"
NAO_ENVIADA = "nao_enviada"
_PRIORIDADE_SITUACAO = (ENVIADA, AGUARDANDO_APROVACAO, REPROVADA)


def _situacao(registros: list, situacao_mensagens: dict[int, str]) -> str:
    situacoes = {situacao_mensagens.get(mid) for p in registros for mid in p.mensagens_ids or []}
    return next((s for s in _PRIORIDADE_SITUACAO if s in situacoes), NAO_ENVIADA)


def perguntas_para_painel(
    atendimento: Atendimento, situacao_mensagens: dict[int, str], textos_produto: Optional[dict[str, str]] = None
) -> list[dict]:
    """O que o painel mostra como pendente, com a indicação de se já chegou ao cliente.

    Junta duas fontes: as perguntas abertas na pilha (feitas e sem resposta, mesmo que
    o catálogo não as liste agora, como a faixa de pessoas antes de saber o software) e
    os campos do catálogo ainda sem valor. As abertas vêm primeiro, da mais antiga para
    o topo, com o texto que de fato saiu; as demais, na ordem do catálogo, com a pergunta
    do catálogo e a situação de um registro antigo da pilha, se houver (pergunta
    descartada pelo teto chegou ao cliente, mas não é mais esperada).

    `situacao_mensagens` mapeia o id de cada `Mensagem` de saída para enviada,
    aguardando_aprovacao ou reprovada, e `textos_produto` dá o texto cadastrado para o
    produto (`perguntas_produto`) por chave de campo (quem consulta o banco é o endpoint).
    """
    itens: list[dict] = []
    for pergunta in sorted(atendimento.perguntas_pendentes, key=lambda p: p.ordem):
        if pergunta.aberta:
            situacao = _situacao([pergunta], situacao_mensagens)
            itens.append({"chave": pergunta.chave, "pergunta": pergunta.texto, "situacao": situacao})
    abertas_chaves = {item["chave"] for item in itens}
    for campo in campos_pendentes(atendimento):
        if campo.chave in abertas_chaves:
            continue
        registros = [p for p in atendimento.perguntas_pendentes if p.chave == campo.chave]
        situacao = _situacao(registros, situacao_mensagens)
        texto = (textos_produto or {}).get(campo.chave) or campo.pergunta
        itens.append({"chave": campo.chave, "pergunta": texto, "situacao": situacao})
    return itens
