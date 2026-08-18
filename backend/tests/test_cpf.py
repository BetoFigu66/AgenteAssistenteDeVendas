"""
Testes para validação e extração de CPF em services.cpf.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from services.classificador import extrair_entidades
from services.cpf.validacao import (
    extrair_cpfs,
    formatar_cpf,
    mascarar_cpf,
    normalizar_cpf,
    parse_data_nascimento,
    validar_cpf,
)


@pytest.mark.parametrize(
    "cpf,valido",
    [
        ("529.982.247-25", True),
        ("52998224725", True),
        ("529 982 247 25", True),
        ("111.111.111-11", False),
        ("00000000000", False),
        ("12345678900", False),
        ("123", False),
    ],
)
def test_validar_cpf(cpf, valido):
    assert validar_cpf(cpf) is valido


def test_formatar_e_mascarar_cpf():
    cpf = "52998224725"
    assert formatar_cpf(cpf) == "529.982.247-25"
    assert mascarar_cpf(cpf) == "***.982.247-**"
    assert normalizar_cpf("529.982.247-25") == "52998224725"


def test_extrair_cpfs_de_texto():
    texto = "Meu CPF é 529.982.247-25 e nasci em 15/03/1985"
    cpfs = extrair_cpfs(texto)
    assert "52998224725" in cpfs


def test_parse_data_nascimento():
    assert parse_data_nascimento("nascimento 15/03/1985") == date(1985, 3, 15)
    assert parse_data_nascimento("15/03/1985") == date(1985, 3, 15)
    assert parse_data_nascimento("data inválida 99/99/9999") is None


def test_classificador_extrai_cpf_e_data():
    texto = "CPF 529.982.247-25, nascimento 10/05/1990"
    ent = extrair_entidades(texto)
    assert "52998224725" in ent.cpfs
    assert ent.datas_nascimento == ["1990-05-10"]


def test_data_nascimento_nao_vira_quantidade():
    """Regressão: dia/mês/ano de uma data não devem gerar entidade quantidades,
    senão o gatilho de projeto complexo dispara em mensagens como '28/12/1965'."""
    ent = extrair_entidades("28/12/1965")
    assert ent.datas_nascimento == ["1965-12-28"]
    assert ent.quantidades == []
