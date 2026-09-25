"""Testes unitários de `utils/nome_perfil.py` (validação provisória do `ProfileName`)."""

import pytest
from utils.nome_perfil import nome_perfil_aproveitavel


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Beto", "Beto"),
        ("Ana", "Ana"),  # exatamente o mínimo de 3 letras
        ("José", "José"),
        ("Zé Lú", "Zé Lú"),  # 4 letras acentuadas contando através do espaço
        ("Ana Souza", "Ana Souza"),
        ("  Ana   Souza  ", "Ana Souza"),  # espaços aparados e colapsados
        ("Ana 😊", "Ana 😊"),  # emoji junto de letras: vale, mantido como veio
        ("😊Bia😊", "😊Bia😊"),
        ("José", "José"),  # acento combinante (NFD) vira NFC
    ],
)
def test_nome_aproveitavel(entrada, esperado):
    assert nome_perfil_aproveitavel(entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    [
        None,
        "",
        "   ",
        "~~~",
        "😊",
        "😊😊😊",
        "Jo",
        "Jo 😊",  # emoji não conta como letra
        "J.",
        "123",
        "A1 B2",  # só 2 letras
        "a" * 201,  # não caberia em `Contato.nome`
    ],
)
def test_nome_nao_aproveitavel(entrada):
    assert nome_perfil_aproveitavel(entrada) is None
