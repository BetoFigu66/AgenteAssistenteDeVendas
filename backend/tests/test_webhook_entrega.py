"""Testes da entrega pelo webhook (REQ-008, Fase 10).

O que se verifica aqui é a tabela de decisão de `_entregar_resposta_do_webhook` — quem
recebe o texto no TwiML e quem não recebe — mais o `/webhook/status`, que é o único
lugar de onde o SID de uma mensagem enviada por TwiML pode vir.
"""

from types import SimpleNamespace

import pytest
from config import settings
from database import Database
from models import Mensagem, ModoExecucao, OrigemMensagem
from services.canal import CanalSimulado, CanalTwilio
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
    """O webhook só entrega quando há resposta para entregar."""
    database = Database()
    with database.get_session() as session:
        ParametroService(session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        session.commit()


def _limpar(telefone):
    database = Database()
    with database.get_session() as session:
        apagar_dados_telefone(session, telefone)
        session.commit()


def _post_webhook(client, telefone, corpo, **extra):
    dados = {"From": f"whatsapp:{telefone}", "Body": corpo}
    dados.update(extra)
    return client.post("/webhook", data=dados)


class _Snapshot(SimpleNamespace):
    """Campos da mensagem copiados para fora da sessão.

    Devolver a entidade daria `DetachedInstanceError` no primeiro acesso: a sessão
    fecha ao sair do `with`, e o commit do endpoint já expirou os atributos.
    """


def _msg_out(telefone):
    database = Database()
    with database.get_session() as session:
        msg = (
            session.query(Mensagem)
            .filter_by(telefone=telefone, origem=OrigemMensagem.SYSTEM)
            .order_by(Mensagem.id.desc())
            .first()
        )
        if msg is None:
            return None
        return _Snapshot(
            id=msg.id,
            conteudo=msg.conteudo,
            message_sid=msg.message_sid,
            timestamp_envio=msg.timestamp_envio,
            erro_envio=msg.erro_envio,
        )


class _CanalTwilioFake(CanalTwilio):
    """CanalTwilio sem rede: registra o que teria sido enviado pela API."""

    def __init__(self, modo_envio):
        super().__init__(
            account_sid="AC_teste",
            numero_whatsapp="+14155238886",
            auth_token="token_teste",
            modo_envio=modo_envio,
            url_publica="https://exemplo.test",
        )
        self.enviados = []

    def enviar(self, telefone, texto, *, mensagem_id=None):
        from services.canal.base import ResultadoEnvio

        self.enviados.append((telefone, texto, mensagem_id))
        return ResultadoEnvio(entregue=True, message_sid=f"SM_fake_{mensagem_id}")


def test_chamada_local_recebe_o_texto_no_twiml(client):
    """O testador de conversas e o simulador leem a resposta pelo TwiML. Sem
    `AccountSid`, sabemos que a chamada não veio da Twilio e nada sai para o WhatsApp."""
    telefone = "5511999966001"
    try:
        r = _post_webhook(client, telefone, "Quero orçamento de catraca")
        assert r.status_code == 200
        assert "<Message>" in r.text
        assert "</Message>" in r.text
    finally:
        _limpar(telefone)


def test_canal_simulado_nao_entrega_para_a_twilio(monkeypatch, client):
    """A trava do `CANAL_SAIDA=simulado` vale também no webhook: com `AccountSid`
    presente (a chamada veio mesmo da Twilio), o TwiML volta vazio."""
    telefone = "5511999966002"
    monkeypatch.setattr(settings, "CANAL_SAIDA", "simulado")
    try:
        r = _post_webhook(client, telefone, "Quero orçamento de catraca", AccountSid="AC_real")
        assert r.status_code == 200
        assert "<Message>" not in r.text

        # A resposta continua gravada: o que muda é só a entrega.
        msg = _msg_out(telefone)
        assert msg is not None and msg.conteudo
        assert msg.timestamp_envio is None
    finally:
        _limpar(telefone)


def test_twilio_modo_twiml_responde_com_status_callback(monkeypatch, client):
    telefone = "5511999966003"
    canal = _CanalTwilioFake(modo_envio="twiml")
    monkeypatch.setattr("main.obter_canal", lambda: canal)
    try:
        r = _post_webhook(client, telefone, "Quero orçamento de catraca", AccountSid="AC_real")
        assert r.status_code == 200
        assert "<Message statusCallback=" in r.text

        msg = _msg_out(telefone)
        assert "mensagem_id=" + str(msg.id) in r.text
        # Otimista: o TwiML foi entregue à Twilio. O desfecho real chega no statusCallback.
        assert msg.timestamp_envio is not None
        # Em modo twiml nada sai pela API REST.
        assert canal.enviados == []
    finally:
        _limpar(telefone)


def test_twilio_modo_rest_envia_pela_api_e_devolve_twiml_vazio(monkeypatch, client):
    telefone = "5511999966004"
    canal = _CanalTwilioFake(modo_envio="rest")
    monkeypatch.setattr("main.obter_canal", lambda: canal)
    try:
        r = _post_webhook(client, telefone, "Quero orçamento de catraca", AccountSid="AC_real")
        assert r.status_code == 200
        assert "<Message" not in r.text

        assert len(canal.enviados) == 1
        msg = _msg_out(telefone)
        assert msg.message_sid == f"SM_fake_{msg.id}"
        assert msg.timestamp_envio is not None
    finally:
        _limpar(telefone)


def test_status_callback_grava_o_sid(client):
    telefone = "5511999966005"
    try:
        _post_webhook(client, telefone, "Quero orçamento de catraca")
        msg = _msg_out(telefone)

        r = client.post(
            f"/webhook/status?mensagem_id={msg.id}",
            data={"MessageSid": "SM_callback_001", "MessageStatus": "sent"},
        )
        assert r.status_code == 200

        assert _msg_out(telefone).message_sid == "SM_callback_001"
    finally:
        _limpar(telefone)


def test_status_callback_repetido_nao_sobrescreve(client):
    """A Twilio chama várias vezes por mensagem (queued, sent, delivered, read).
    `message_sid` é unique: sobrescrever trocaria a identidade da mensagem."""
    telefone = "5511999966006"
    try:
        _post_webhook(client, telefone, "Quero orçamento de catraca")
        msg = _msg_out(telefone)

        for status in ("queued", "sent", "delivered"):
            client.post(
                f"/webhook/status?mensagem_id={msg.id}",
                data={"MessageSid": "SM_callback_002", "MessageStatus": status},
            )
        client.post(
            f"/webhook/status?mensagem_id={msg.id}",
            data={"MessageSid": "SM_OUTRO_SID", "MessageStatus": "sent"},
        )

        assert _msg_out(telefone).message_sid == "SM_callback_002"
    finally:
        _limpar(telefone)


def test_status_callback_de_falha_desfaz_o_envio_otimista(client):
    telefone = "5511999966007"
    try:
        _post_webhook(client, telefone, "Quero orçamento de catraca")
        msg = _msg_out(telefone)

        client.post(
            f"/webhook/status?mensagem_id={msg.id}",
            data={
                "MessageSid": "SM_callback_003",
                "MessageStatus": "failed",
                "ErrorCode": "63016",
                "ErrorMessage": "fora da janela",
            },
        )

        atualizada = _msg_out(telefone)
        assert atualizada.timestamp_envio is None
        assert "63016" in atualizada.erro_envio
    finally:
        _limpar(telefone)


def test_status_callback_de_mensagem_inexistente_nao_quebra(client):
    r = client.post("/webhook/status?mensagem_id=999999999", data={"MessageSid": "SM_x"})
    assert r.status_code == 200
    assert r.json()["status"] == "ignorado"


def test_assinatura_invalida_recusa_webhook(monkeypatch, client):
    monkeypatch.setattr(settings, "TWILIO_VALIDAR_ASSINATURA", True)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token_teste")
    monkeypatch.setattr(settings, "APP_URL_PUBLICA", "https://exemplo.test")

    r = _post_webhook(client, "5511999966008", "oi", AccountSid="AC_real")
    assert r.status_code == 403


def test_validacao_ligada_sem_auth_token_recusa(monkeypatch, client):
    """A validação usa o Auth Token da conta; API Key não serve. Sem ele, recusar é a
    única resposta honesta — seguir em frente seria fingir que validamos."""
    monkeypatch.setattr(settings, "TWILIO_VALIDAR_ASSINATURA", True)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)

    r = _post_webhook(client, "5511999966009", "oi", AccountSid="AC_real")
    assert r.status_code == 503


def test_canal_simulado_reportado_na_config(client):
    r = client.get("/api/config/execucao")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["canal_saida"] == CanalSimulado.nome
    assert corpo["entrega_real"] is False
