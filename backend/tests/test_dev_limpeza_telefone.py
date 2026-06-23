"""Testes da limpeza de dados por telefone (dev)."""

from unittest.mock import MagicMock

from services.dev_limpeza_telefone import _coletar_contatos


def test_coletar_contatos_vazio():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    assert _coletar_contatos(db, "+5511999999999") == []
