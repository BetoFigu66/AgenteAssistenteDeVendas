"""
Perguntas do roteiro de qualificação com texto por produto.

A tabela `perguntas_produto` (editada no painel, aba Parâmetros) troca, para um produto
(linha de `produtos`), o texto de uma pergunta do roteiro (`catalogo_campos.py`). Ex.: a
pergunta do modelo do Relógio de Ponto lista cartográfico, cartão, biometria e facial; a da
Catraca, cartão, biometria, facial e QR Code. Sem linha ativa, vale o texto do código.

O atendimento só conhece o tipo de produto da conversa (`relogio_ponto`); a ligação com a
linha de `produtos` é a de `catalogo_produtos.produto_ids_por_tipos`. Se mais de um
produto casa com o tipo e mais de um tem texto, vale o de menor id (o cadastrado antes).

As linhas ficam em memória como em `services/cumprimentos.py`: relidas a cada
`_VALIDADE_SEGUNDOS`, ou na hora quando o painel grava (`invalidar`). Se o banco falhar,
vale o texto do código.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from sqlalchemy.orm import Session

from services.catalogo_produtos import produto_ids_por_tipos

logger = logging.getLogger(__name__)

_VALIDADE_SEGUNDOS = 60.0

_trava = threading.Lock()
_cache: Optional[dict[tuple[int, str], str]] = None
_carregado_em = 0.0
_db = None


def invalidar() -> None:
    """Força a releitura na próxima consulta (chamado quando o painel grava)."""
    global _cache
    with _trava:
        _cache = None


def _ler_banco() -> dict[tuple[int, str], str]:
    # Sessão própria: uma falha aqui não pode abortar a transação do processamento.
    global _db
    from database import Database
    from models import PerguntaProduto

    if _db is None:
        _db = Database()
    with _db.get_session() as session:
        linhas = session.query(PerguntaProduto).filter(PerguntaProduto.ativo.is_(True)).all()
        return {(p.produto_id, p.campo): p.texto for p in linhas if p.texto.strip()}


def _cadastradas() -> dict[tuple[int, str], str]:
    global _cache, _carregado_em
    with _trava:
        if _cache is not None and time.monotonic() - _carregado_em < _VALIDADE_SEGUNDOS:
            return _cache
        try:
            _cache = _ler_banco()
        except Exception as e:
            logger.warning(f"[PerguntasProduto] tabela indisponível, usando os textos do código: {e}")
            _cache = {}
        _carregado_em = time.monotonic()
        return _cache


def texto_para(db: Session, campo: str, tipo_produto: Optional[str]) -> Optional[str]:
    """O texto cadastrado para a pergunta `campo` no produto do tipo `tipo_produto`, ou
    None (vale o do código)."""
    if not tipo_produto:
        return None
    cadastradas = _cadastradas()
    if not any(c == campo for _, c in cadastradas):
        return None
    for produto_id in sorted(produto_ids_por_tipos(db, [tipo_produto])):
        texto = cadastradas.get((produto_id, campo))
        if texto:
            return texto
    return None
