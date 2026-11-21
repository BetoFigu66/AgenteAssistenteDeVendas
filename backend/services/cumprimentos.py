"""
Cumprimentos: reconhecer o início de conversa e responder no mesmo tom.

A tabela `cumprimentos` (editada no painel, aba Parâmetros) é a fonte única de duas
coisas que antes estavam separadas e fixas no código:

- o que conta como cumprimento: o classificador marca `SAUDACAO` quando a mensagem traz
  uma expressão cadastrada (`e_cumprimento`), no lugar da regex que existia;
- a primeira frase da resposta: "Bom dia" recebe "Bom dia!", "E aí Bro?" recebe "E aí?",
  e o que não casa com nada recebe "Olá!" (`resposta_para`).

Comparação: sem acento, pontuação e maiúsculas, por palavra inteira, em qualquer ponto da
mensagem. Com mais de uma expressão na mensagem, a mais longa escolhe a resposta ("Oi, bom
dia" → "Bom dia!"; "E aí Bro?" casa com "e aí" e "e aí bro" → "E aí?"). Expressão com
resposta vazia ("tudo bem") conta como cumprimento mas não escolhe a resposta.

As linhas ficam em memória e são relidas a cada `_VALIDADE_SEGUNDOS`, ou na hora quando o
painel muda alguma (`invalidar`). Se o banco falhar, valem os `_PADROES` abaixo (os mesmos
do seed da migração), para o classificador não perder as saudações.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

RESPOSTA_PADRAO = "Olá!"
_VALIDADE_SEGUNDOS = 60.0

# Usados só se a tabela não puder ser lida. Espelham o seed de `2026110101`.
_PADROES: tuple[tuple[str, str], ...] = (
    ("oi", "Oi!"), ("olá", "Olá!"), ("bom dia", "Bom dia!"), ("boa tarde", "Boa tarde!"),
    ("boa noite", "Boa noite!"), ("e aí", "E aí!"), ("eai", "E aí!"), ("e aí bro", "E aí?"),
    ("salve", "Salve!"), ("hey", "Olá!"), ("hi", "Olá!"), ("hello", "Olá!"),
    ("tudo bem", ""), ("tudo bom", ""), ("tudo certo", ""), ("tudo joia", ""), ("como vai", ""),
)

_trava = threading.Lock()
_cache: Optional[list[tuple[str, str]]] = None
_carregado_em = 0.0
_db = None


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, só letras e dígitos separados por um espaço."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def invalidar() -> None:
    """Força a releitura na próxima consulta (chamado quando o painel grava)."""
    global _cache
    with _trava:
        _cache = None


def _ler_banco() -> list[tuple[str, str]]:
    global _db
    from database import Database
    from models import Cumprimento

    if _db is None:
        _db = Database()
    with _db.get_session() as session:
        linhas = session.query(Cumprimento).filter(Cumprimento.ativo.is_(True)).all()
        return [(c.expressao_normalizada, c.resposta or "") for c in linhas]


def _cadastrados() -> list[tuple[str, str]]:
    global _cache, _carregado_em
    with _trava:
        if _cache is not None and time.monotonic() - _carregado_em < _VALIDADE_SEGUNDOS:
            return _cache
        try:
            _cache = _ler_banco()
        except Exception as e:
            logger.warning(f"[Cumprimentos] tabela indisponível, usando os padrões: {e}")
            _cache = [(normalizar(e), r) for e, r in _PADROES]
        _carregado_em = time.monotonic()
        return _cache


def encontrados(texto: str) -> list[tuple[str, str]]:
    """As expressões cadastradas presentes no texto, da mais longa para a mais curta."""
    alvo = f" {normalizar(texto)} "
    if not alvo.strip():
        return []
    achados = [(e, r) for e, r in _cadastrados() if e and f" {e} " in alvo]
    return sorted(achados, key=lambda par: len(par[0]), reverse=True)


def e_cumprimento(texto: str) -> bool:
    return bool(encontrados(texto))


def palavras() -> frozenset[str]:
    """Palavras das expressões cadastradas: não servem de nome ("E aí Bro" não é o Bro)."""
    return frozenset(p for e, _ in _cadastrados() for p in e.split() if len(p) >= 2)


def com_nome(resposta: str, nome: Optional[str]) -> str:
    """Encaixa o nome antes da pontuação final: "Bom dia!" → "Bom dia, João!"."""
    resposta = resposta.strip()
    if not nome:
        return resposta
    base = resposta.rstrip("!?.…")
    sinal = resposta[len(base):] or "!"
    return f"{base.rstrip(' ,')}, {nome}{sinal}"


def resposta_para(texto: Optional[str], nome: Optional[str] = None) -> str:
    """A primeira frase da saudação para a mensagem do cliente, com o nome se houver."""
    for _, resposta in encontrados(texto or ""):
        if resposta.strip():
            return com_nome(resposta, nome)
    return com_nome(RESPOSTA_PADRAO, nome)
