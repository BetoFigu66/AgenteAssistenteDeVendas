"""Regressões achadas pela bateria do testador de conversas de 08/10/2026 (skill
`testar-backend`): classificação por regras, sem LLM."""

import asyncio

import pytest
from services.classificador import Intencao, classificar, extrair_entidades


def _intencoes(texto):
    return asyncio.run(classificar(texto)).intencoes


@pytest.mark.parametrize(
    "texto",
    ["comprei um relógio semana passada e não chegou", "isso é um absurdo, ninguém me responde"],
)
def test_reclamacao_de_pos_venda(texto):
    assert Intencao.RECLAMAR in _intencoes(texto)


@pytest.mark.parametrize("texto", ["bom dia, quero falar com o Ivan", "posso falar com a Rita?"])
def test_pedido_de_humano_pelo_nome(texto):
    assert Intencao.ESCALAR_HUMANO in _intencoes(texto)


def test_falar_com_alguem_da_propria_empresa_nao_e_pedido_de_humano():
    assert Intencao.ESCALAR_HUMANO not in _intencoes("vou falar com o RH e te retorno")


def test_pessoa_fisica_nao_e_pedido_de_humano():
    assert Intencao.ESCALAR_HUMANO not in _intencoes("oi, não tenho empresa, sou pessoa física")
    assert Intencao.ESCALAR_HUMANO in _intencoes("quero falar com uma pessoa")


@pytest.mark.parametrize("texto", ["tudo bem?", "Tudo bom?", "como vai?"])
def test_cortesia_e_saudacao(texto):
    assert _intencoes(texto) == [Intencao.SAUDACAO]


@pytest.mark.parametrize(
    "texto",
    ["preciso de relógio de ponto", "preciso de um controle de acesso", "o que eu preciso é catraca"],
)
def test_necessidade_com_produto_e_pedido_de_orcamento(texto):
    assert Intencao.PEDIR_ORCAMENTO in _intencoes(texto)


@pytest.mark.parametrize("texto", ["quero cancelar", "quero saber sobre catraca", "preciso de ajuda"])
def test_necessidade_sem_produto_ou_de_informacao_nao_e_orcamento(texto):
    assert Intencao.PEDIR_ORCAMENTO not in _intencoes(texto)


@pytest.mark.parametrize(
    "texto, campo, esperado",
    [
        ("quero cancelar", "tipos_produto", []),
        ("preciso de uma cancela", "tipos_produto", ["cancela"]),
        ("levo uns dias pra decidir", "software_acesso", None),
        ("usamos o EVO", "software_acesso", "EVO"),
        ("faço a busca amanhã", "software_acesso", None),
        ("o reparo foi feito", "tipos_produto", []),
        ("vou casar mês que vem", "aplicacao", None),
    ],
)
def test_termos_casam_como_palavra_inteira(texto, campo, esperado):
    assert getattr(extrair_entidades(texto), campo) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "vocês têm relógio de ponto que funciona com o Domínio?",
        "então funciona ou não funciona?",
        "o fornecedor disse que qualquer REP serve, confirma?",
        "a catraca integra com o EVO?",
    ],
)
def test_compatibilidade_e_duvida_de_produto_nao_reclamacao(texto):
    intencoes = _intencoes(texto)
    assert Intencao.PERGUNTAR_PRODUTO in intencoes
    assert Intencao.RECLAMAR not in intencoes


def test_nao_funciona_continua_sendo_reclamacao():
    assert Intencao.RECLAMAR in _intencoes("o relógio não funciona mais")
