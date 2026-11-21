"""Cumprimentos cadastrados (`services/cumprimentos.py`): reconhecer o início de conversa
e responder no mesmo tom ("Bom dia" → "Bom dia!"), com a tabela editada no painel."""

import pytest
from services import cumprimentos
from services.classificador import Intencao, classificar_por_regras
from services.respostas import MensagemId
from services.respostas.catalogo import renderizar_mensagem


@pytest.fixture(autouse=True)
def cache_limpo():
    cumprimentos.invalidar()
    yield
    cumprimentos.invalidar()


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Bom dia.", "Bom dia!"),
        ("Boa tarde!", "Boa tarde!"),
        ("BOA NOITE!!!", "Boa noite!"),
        ("bom   dia, quero um orçamento", "Bom dia!"),
        # A mais longa escolhe: "e aí bro" vence "e aí"; "bom dia" vence "oi".
        ("E aí Bro?", "E aí?"),
        ("e ai", "E aí!"),
        ("Oi, bom dia!", "Bom dia!"),
        # "tudo bem" conta como cumprimento, mas sem resposta própria.
        ("Oi, tudo bem?", "Oi!"),
        ("tudo bem?", "Olá!"),
        ("Quero um orçamento", "Olá!"),
        ("", "Olá!"),
    ],
)
def test_resposta_no_tom_do_cliente(texto, esperado):
    assert cumprimentos.resposta_para(texto) == esperado


def test_nome_entra_antes_da_pontuacao():
    assert cumprimentos.resposta_para("Bom dia", "Ana") == "Bom dia, Ana!"
    assert cumprimentos.resposta_para("E aí Bro?", "João") == "E aí, João?"
    assert cumprimentos.resposta_para("quero orçamento", "Ana") == "Olá, Ana!"
    assert cumprimentos.com_nome("Salve", "Ana") == "Salve, Ana!"


def test_palavra_inteira_nao_casa_dentro_de_outra():
    # "oi" não está em "oito"; "hi" não está em "chip".
    assert not cumprimentos.e_cumprimento("quero oito catracas")
    assert not cumprimentos.e_cumprimento("comprei um chip")


def test_classificador_usa_o_cadastro():
    intencoes = [i for i, _ in classificar_por_regras("E aí Bro?")]
    assert intencoes == [Intencao.SAUDACAO]
    intencoes = [i for i, _ in classificar_por_regras("Bom dia, quero orçamento")]
    assert Intencao.SAUDACAO in intencoes and Intencao.PEDIR_ORCAMENTO in intencoes


def test_banco_fora_usa_os_padroes(monkeypatch):
    def falha():
        raise RuntimeError("banco fora")

    monkeypatch.setattr(cumprimentos, "_ler_banco", falha)
    cumprimentos.invalidar()
    assert cumprimentos.resposta_para("Boa tarde!") == "Boa tarde!"
    assert cumprimentos.e_cumprimento("oi")


def test_templates_de_saudacao_respondem_no_mesmo_tom():
    texto, _ = renderizar_mensagem(
        MensagemId.SAUDACAO_NOVO_CONTATO, {"mensagem_cliente": "Bom dia.", "tem_documento": False}
    )
    assert texto.startswith("Bom dia! 👋 Sou o assistente da Inforrel.")
    texto, _ = renderizar_mensagem(MensagemId.SAUDACAO_COM_NOME, {"nome": "Ana", "mensagem_cliente": "Boa tarde!"})
    assert texto == "Boa tarde, Ana! 👋 Como posso te ajudar hoje?"
    # Sem a mensagem do cliente, o "Olá" de antes.
    texto, _ = renderizar_mensagem(MensagemId.SAUDACAO_COM_NOME, {"nome": "Ana"})
    assert texto.startswith("Olá, Ana!")


def test_api_cadastra_testa_altera_e_exclui(client):
    criado = client.post("/api/cumprimentos", json={"expressao": "Fala, mano!", "resposta": "Fala!"})
    assert criado.status_code == 201, criado.text
    cid = criado.json()["id"]
    try:
        # Vale na hora, sem esperar a releitura do cache.
        teste = client.get("/api/cumprimentos/testar", params={"texto": "fala mano, tudo certo?"}).json()
        assert teste["e_cumprimento"] and teste["resposta"] == "Fala!"

        # Equivalente (só muda acento/pontuação/maiúscula) é recusado.
        repetido = client.post("/api/cumprimentos", json={"expressao": "FALA MANO", "resposta": "x"})
        assert repetido.status_code == 409

        assert client.post("/api/cumprimentos", json={"expressao": "!!!"}).status_code == 422

        desligado = client.patch(f"/api/cumprimentos/{cid}", json={"ativo": False})
        assert desligado.status_code == 200 and desligado.json()["ativo"] is False
        assert not client.get("/api/cumprimentos/testar", params={"texto": "fala mano"}).json()["e_cumprimento"]

        lista = client.get("/api/cumprimentos").json()["cumprimentos"]
        assert any(c["id"] == cid and c["atualizado_por"] for c in lista)
    finally:
        assert client.delete(f"/api/cumprimentos/{cid}").status_code == 204
    assert client.delete(f"/api/cumprimentos/{cid}").status_code == 404
