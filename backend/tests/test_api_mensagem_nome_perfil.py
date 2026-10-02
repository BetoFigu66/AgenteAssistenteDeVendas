"""`POST /api/mensagem` repassa o nome do perfil simulado no Chat ao processador.

O simulador da interface web deixa digitar o nome que o WhatsApp mandaria em
`ProfileName`; o endpoint só precisa entregá-lo no mesmo parâmetro que o webhook usa.
"""

import pytest
from services.processador import ResultadoProcessamento


@pytest.fixture
def cerebro(monkeypatch):
    import main

    chamadas = []

    async def _dubla(telefone, conteudo, message_sid, responde_a_message_sid=None,
                     responde_a_mensagem_id=None, nome_perfil=None):
        chamadas.append({"telefone": telefone, "nome_perfil": nome_perfil})
        return ResultadoProcessamento(resposta="ok")

    monkeypatch.setattr(main, "_processar_via_cerebro", _dubla)
    return chamadas


def test_repassa_nome_perfil(client, cerebro):
    corpo = {"telefone": "+5511900000001", "mensagem": "oi", "nome_perfil": "Maria"}
    resposta = client.post("/api/mensagem", json=corpo)
    assert resposta.status_code == 200, resposta.text
    assert cerebro == [{"telefone": "+5511900000001", "nome_perfil": "Maria"}]


def test_sem_nome_perfil_continua_none(client, cerebro):
    resposta = client.post("/api/mensagem", json={"telefone": "+5511900000001", "mensagem": "oi"})
    assert resposta.status_code == 200, resposta.text
    assert cerebro[0]["nome_perfil"] is None
