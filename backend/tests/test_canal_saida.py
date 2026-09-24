"""Testes do canal de saída (REQ-008, Fase 10).

Cobre as três decisões que o canal encapsula: quem entrega, quem não entrega, e o que
acontece quando a entrega falha. O `CanalTwilio` é exercitado com um cliente REST falso
— o que se testa aqui é a tradução entre a API da Twilio e `ResultadoEnvio`, não a API
da Twilio em si.
"""

import pytest
from config import settings
from services.canal import CanalSimulado, CanalTwilio
from services.canal.factory import obter_canal


class _MensagemFake:
    def __init__(self, sid):
        self.sid = sid


class _MessagesFake:
    def __init__(self, erro=None):
        self._erro = erro
        self.chamadas = []

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        if self._erro:
            raise self._erro
        return _MensagemFake("SM_teste_123")


class _ClienteFake:
    def __init__(self, erro=None):
        self.messages = _MessagesFake(erro=erro)


class _ErroTwilio(Exception):
    def __init__(self, code, msg="falhou"):
        super().__init__(msg)
        self.code = code


def _canal_twilio(modo_envio="rest", url_publica="https://exemplo.test", erro=None):
    canal = CanalTwilio(
        account_sid="AC_teste",
        numero_whatsapp="+14155238886",
        auth_token="token_teste",
        modo_envio=modo_envio,
        url_publica=url_publica,
    )
    canal._cliente_cache = _ClienteFake(erro=erro)
    return canal


# ---------------------------------------------------------------------------
# Canal simulado
# ---------------------------------------------------------------------------


def test_simulado_nao_entrega_e_nao_e_erro():
    resultado = CanalSimulado().enviar("+5519999990000", "oi", mensagem_id=7)
    assert resultado.entregue is False
    assert resultado.falhou is False
    assert resultado.erro is None
    assert resultado.message_sid is None


def test_simulado_nunca_entrega_pela_resposta_do_webhook():
    canal = CanalSimulado()
    assert canal.entrega_real is False
    assert canal.entrega_na_resposta_do_webhook() is False
    assert canal.url_status_callback(1) is None


# ---------------------------------------------------------------------------
# Canal Twilio
# ---------------------------------------------------------------------------


def test_twilio_rest_devolve_sid_na_hora():
    canal = _canal_twilio(modo_envio="rest")
    resultado = canal.enviar("+5519999990000", "olá", mensagem_id=42)

    assert resultado.entregue is True
    assert resultado.message_sid == "SM_teste_123"
    enviado = canal._cliente.messages.chamadas[0]
    # O prefixo `whatsapp:` é obrigatório nos dois lados e o número do .env não o tem.
    assert enviado["to"] == "whatsapp:+5519999990000"
    assert enviado["from_"] == "whatsapp:+14155238886"


def test_twilio_falha_vira_erro_legivel_e_nao_excecao():
    canal = _canal_twilio(erro=_ErroTwilio(63016))
    resultado = canal.enviar("+5519999990000", "olá", mensagem_id=42)

    assert resultado.entregue is False
    assert resultado.falhou is True
    # 63016 é a colisão entre o gate de aprovação e a janela de 24h: precisa ser
    # reconhecível na UI, não um traceback da API.
    assert "24h" in resultado.erro
    assert "63016" in resultado.erro


def test_twilio_modo_twiml_entrega_na_resposta_do_webhook():
    canal = _canal_twilio(modo_envio="twiml")
    assert canal.entrega_na_resposta_do_webhook() is True
    assert canal.url_status_callback(99) == "https://exemplo.test/webhook/status?mensagem_id=99"


def test_twilio_modo_rest_nao_entrega_pela_resposta_do_webhook():
    assert _canal_twilio(modo_envio="rest").entrega_na_resposta_do_webhook() is False


def test_sem_url_publica_nao_ha_status_callback():
    """Sem `APP_URL_PUBLICA` a mensagem ainda sai — só nunca descobrimos o SID dela."""
    canal = _canal_twilio(modo_envio="twiml", url_publica=None)
    assert canal.url_status_callback(99) is None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _limpar_cache_factory():
    obter_canal.cache_clear()
    yield
    obter_canal.cache_clear()


def test_factory_default_e_simulado(monkeypatch):
    monkeypatch.setattr(settings, "CANAL_SAIDA", "simulado")
    assert obter_canal().nome == "simulado"


def test_factory_sem_credenciais_cai_para_simulado(monkeypatch):
    """Falha segura: pedir twilio sem credencial não pode virar 'achei que estava
    simulando e mandei de verdade' nem derrubar o boot."""
    monkeypatch.setattr(settings, "CANAL_SAIDA", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr(settings, "TWILIO_API_KEY_SID", None)
    monkeypatch.setattr(settings, "TWILIO_API_KEY_SECRET", None)
    monkeypatch.setattr(settings, "TWILIO_WHATSAPP_NUMBER", None)

    assert obter_canal().nome == "simulado"


def test_factory_com_credenciais_monta_canal_twilio(monkeypatch):
    monkeypatch.setattr(settings, "CANAL_SAIDA", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_teste")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token_teste")
    monkeypatch.setattr(settings, "TWILIO_WHATSAPP_NUMBER", "+14155238886")
    monkeypatch.setattr(settings, "TWILIO_MODO_ENVIO", "twiml")
    monkeypatch.setattr(settings, "APP_URL_PUBLICA", "https://exemplo.test")

    canal = obter_canal()
    assert canal.nome == "twilio"
    assert canal.entrega_real is True
    assert canal.entrega_na_resposta_do_webhook() is True


def test_factory_recusa_canal_desconhecido(monkeypatch):
    monkeypatch.setattr(settings, "CANAL_SAIDA", "telegrama")
    with pytest.raises(ValueError, match="telegrama"):
        obter_canal()
