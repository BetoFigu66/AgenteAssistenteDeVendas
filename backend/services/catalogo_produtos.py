"""Ligação entre o tipo de produto da conversa (`relogio_ponto`, `catraca`) e as linhas
da tabela `produtos` ("Relógio de Ponto", "Catraca").

A conversa só conhece o tipo (o classificador o extrai do texto); o catálogo comercial e
as perguntas por produto (`services/perguntas_produto.py`) são por linha de `produtos`. A
ligação é por nome: os tokens do tipo aparecem na descrição do produto.
"""

from __future__ import annotations

import unicodedata

from models import Produto
from sqlalchemy.orm import Session


def normalizar_sem_acento(texto: str) -> str:
    """Remove acentos para comparações case-insensitive em português."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


def produto_ids_por_tipos(db: Session, tipos_produto: list[str]) -> list[int]:
    """Busca produtos ativos cujo nome contenha os tokens do tipo extraído."""
    if not tipos_produto:
        return []
    produtos = db.query(Produto).filter(Produto.ativo.is_(True)).all()
    ids: set[int] = set()
    for tipo in tipos_produto:
        tipo_norm = normalizar_sem_acento(tipo.replace("_", " "))
        partes = [p for p in tipo_norm.split() if len(p) > 2]
        for produto in produtos:
            desc_norm = normalizar_sem_acento(produto.descricao)
            if tipo_norm in desc_norm or all(part in desc_norm for part in partes):
                ids.add(produto.id)
    return list(ids)
