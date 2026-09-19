"""Mensagem recebida sem texto no `POST /webhook` (caso da mensagem só com mídia).

A Twilio entrega foto, áudio e documento com `NumMedia>0` e `Body` vazio. Enquanto o
`Body` era obrigatório na assinatura do endpoint, o FastAPI devolvia 422 para a Twilio
e a mensagem do cliente se perdia: nem registro, nem resposta.

O que se verifica aqui: o webhook aceita a mensagem, grava a linha no histórico (com
marcador que distingue "só mídia" de "vazia de verdade") e não inventa resposta nenhuma
sobre um conteúdo que o sistema não leu.
"""

from xml.etree import ElementTree

import pytest
from database import Database
from models import Mensagem, ModoExecucao, OrigemMensagem
from services.canal.factory import obter_canal
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import MODO_EXECUCAO, ParametroService


@pytest.fixture(autouse=True)
def _canal_limpo():
    obter_canal.cache_clear()
    yield
    obter_canal.cache_clear()


@pytest.fixture(autouse=True)
def _execucao_normal():
    """Modo mais permissivo de propósito: se alguma resposta fosse gerada para uma
    mensagem sem texto, é aqui que ela apareceria no TwiML."""
    database = Database()
    with database.get_session() as session:
        ParametroService(session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        session.commit()


def _limpar(telefone):
    database = Database()
    with database.get_session() as session:
        apagar_dados_telefone(session, telefone)
        session.commit()


def _mensagens(telefone, origem):
    """Conteúdos das mensagens do telefone, em ordem de gravação.

    Devolve strings e não entidades: a sessão fecha ao sair do `with` e qualquer
    acesso posterior daria `DetachedInstanceError`.
    """
    database = Database()
    with database.get_session() as session:
        return [
            m.conteudo
            for m in session.query(Mensagem)
            .filter_by(telefone=telefone, origem=origem)
            .order_by(Mensagem.id.asc())
            .all()
        ]


def _assert_twiml_vazio(resposta):
    """200 com TwiML bem formado e sem `<Message>` — nada sai para o cliente."""
    assert resposta.status_code == 200, resposta.text
    raiz = ElementTree.fromstring(resposta.text)
    assert raiz.tag == "Response"
    assert list(raiz) == []


def test_body_vazio_com_midia_e_aceito_e_registrado():
    """Mensagem só com mídia: 200, TwiML vazio e a mensagem do cliente no histórico."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977001"
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "", "NumMedia": "2"},
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        # O marcador diz o que de fato chegou, sem afirmar nada sobre o conteúdo da mídia.
        assert "mídia recebida sem texto" in recebidas[0]
        assert "2 anexo" in recebidas[0]

        # Nenhuma resposta automática: o sistema não leu a mídia e não finge que leu.
        assert _mensagens(telefone, OrigemMensagem.SYSTEM) == []
    finally:
        _limpar(telefone)


def test_body_vazio_sem_midia_e_aceito_e_registrado():
    """Mensagem vazia de verdade (`NumMedia=0`): também é aceita e registrada, com
    marcador diferente — `NumMedia` é o que permite separar os dois casos."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977002"
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "", "NumMedia": "0"},
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        assert "sem conteúdo" in recebidas[0]
        assert "anexo" not in recebidas[0]

        assert _mensagens(telefone, OrigemMensagem.SYSTEM) == []
    finally:
        _limpar(telefone)


def test_campo_body_ausente_nao_devolve_422():
    """A Twilio pode nem mandar o campo. Antes isso era 422; agora vale como sem texto."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977003"
    try:
        with TestClient(main.app) as client:
            resposta = client.post("/webhook", data={"From": f"whatsapp:{telefone}", "NumMedia": "1"})
        _assert_twiml_vazio(resposta)
        assert len(_mensagens(telefone, OrigemMensagem.USER)) == 1
    finally:
        _limpar(telefone)


def test_chamada_da_twilio_com_midia_tambem_e_registrada(monkeypatch):
    """Com `AccountSid` (chamada real da Twilio) o comportamento é o mesmo: registra e
    devolve TwiML vazio. O caminho local não é privilegiado aqui porque não há resposta
    gerada para nenhum dos dois lerem."""
    import main
    from config import settings
    from fastapi.testclient import TestClient

    telefone = "5511999977004"
    monkeypatch.setattr(settings, "CANAL_SAIDA", "simulado")
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={
                    "From": f"whatsapp:{telefone}",
                    "Body": "",
                    "NumMedia": "1",
                    "AccountSid": "AC_real",
                    "MessageSid": "SM_midia_teste_001",
                },
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        assert "mídia recebida sem texto" in recebidas[0]
    finally:
        _limpar(telefone)


def test_num_media_invalido_conta_como_sem_midia():
    """`NumMedia` vem como string de formulário: lixo não pode derrubar o webhook."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977005"
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "   ", "NumMedia": "nao-e-numero"},
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        assert "sem conteúdo" in recebidas[0]
    finally:
        _limpar(telefone)
