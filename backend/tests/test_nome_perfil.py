"""Testes unitários de `utils/nome_perfil.py` (validação provisória do `ProfileName`) e das
peças sem banco da confirmação do nome de perfil."""

import pytest
from services.conversacao.confirmacao_nome_perfil import _nome_solto, contexto_confirmacao, eh_confirmacao_pura
from services.respostas import MensagemId
from services.respostas.catalogo import renderizar_mensagem
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


# ---------------------------------------------------------------------------
# Confirmação do nome de perfil (`services/conversacao/confirmacao_nome_perfil.py`)
# e os textos do catálogo que ela usa. Sem banco.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    ["sim", "Sim!", "SIM.", "pode", "pode sim", "Pode sim!", "isso", "isso mesmo", "ok", "claro",
     "sim, pode", "pode me chamar assim", "👍", "👍🏽", "✅", "claro 👍"],
)
def test_eh_confirmacao_pura(texto):
    assert eh_confirmacao_pura(texto)


@pytest.mark.parametrize(
    "texto",
    ["", "não", "Carlos", "sim, quero orçamento", "pode me mandar o catálogo?", "😊", "oi", "sim 11.222.333/0001-81"],
)
def test_nao_eh_confirmacao_pura(texto):
    assert not eh_confirmacao_pura(texto)


@pytest.mark.parametrize(
    "texto, esperado",
    [("Carlos", "Carlos"), ("carlos eduardo", "Carlos Eduardo"), ("é Carlos", "Carlos"), ("sou Cadu.", "Cadu")],
)
def test_nome_solto(texto, esperado):
    assert _nome_solto(texto) == esperado


@pytest.mark.parametrize("texto", ["oi", "bom dia", "quero orçamento", "C", "Carlos 123", "a b c d e", "obrigado"])
def test_nao_e_nome_solto(texto):
    assert _nome_solto(texto) is None


def test_texto_confirmar_nome_perfil_no_primeiro_contato_com_pedido_de_documento():
    texto, codigo = renderizar_mensagem(MensagemId.CONFIRMAR_NOME_PERFIL, contexto_confirmacao("Ana", True, True))

    assert codigo == "CONFIRMAR_NOME_PERFIL"
    assert texto == (
        "Olá, Ana! 👋 Sou o assistente da Inforrel.\n"
        "Posso te chamar assim ou seu nome é outro? "
        "E para te atender melhor, poderia me informar o CNPJ da sua empresa ou seu CPF?"
    )


def test_texto_confirmar_nome_perfil_sem_apresentacao_nem_documento():
    texto, _ = renderizar_mensagem(MensagemId.CONFIRMAR_NOME_PERFIL, contexto_confirmacao("Ana", False, False))

    assert texto == "Olá, Ana! 👋 Posso te chamar assim ou seu nome é outro?"


@pytest.mark.parametrize(
    "contexto, esperado",
    [
        ({"nome": "Ana"}, "Combinado, Ana! 😊 Em que posso te ajudar hoje?"),
        (
            {"nome": "Ana", "pedir_documento": True},
            "Combinado, Ana! 😊 Para te atender melhor, poderia me informar o CNPJ da sua empresa ou seu CPF?",
        ),
        ({"nome": "Ana", "segue_pergunta": True}, "Combinado, Ana! 😊"),
    ],
)
def test_texto_nome_anotado(contexto, esperado):
    texto, _ = renderizar_mensagem(MensagemId.NOME_ANOTADO, contexto)
    assert texto == esperado
