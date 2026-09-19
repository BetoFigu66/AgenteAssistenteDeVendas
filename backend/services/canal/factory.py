"""Factory do canal de saída — mesmo padrão de `services/llm` e `services/embeddings`."""

import logging
from functools import lru_cache

from config import settings

from .base import CanalSaida
from .simulado import CanalSimulado
from .twilio_canal import CanalTwilio

logger = logging.getLogger(__name__)

_MODOS_ENVIO = {"twiml", "rest"}


@lru_cache(maxsize=1)
def obter_canal() -> CanalSaida:
    """Instância única do canal configurado em `CANAL_SAIDA`.

    Cai para `CanalSimulado` quando `twilio` está pedido mas faltam credenciais: é a
    falha segura. O contrário (subir achando que está simulando e mandar mensagem de
    verdade) seria o erro caro.
    """
    canal = (settings.CANAL_SAIDA or "simulado").lower()

    if canal == "simulado":
        return CanalSimulado()

    if canal != "twilio":
        raise ValueError(f"CANAL_SAIDA '{canal}' não suportado. Opções: simulado, twilio")

    account_sid = settings.TWILIO_ACCOUNT_SID
    numero = settings.TWILIO_WHATSAPP_NUMBER
    faltando = [
        nome
        for nome, valor in (
            ("TWILIO_ACCOUNT_SID", account_sid),
            ("TWILIO_WHATSAPP_NUMBER", numero),
        )
        if not valor
    ]
    tem_credencial = settings.TWILIO_AUTH_TOKEN or (settings.TWILIO_API_KEY_SID and settings.TWILIO_API_KEY_SECRET)
    if not tem_credencial:
        faltando.append("TWILIO_AUTH_TOKEN (ou TWILIO_API_KEY_SID + TWILIO_API_KEY_SECRET)")

    if faltando or not account_sid or not numero:
        logger.error(
            "CANAL_SAIDA=twilio mas faltam variáveis no .env: %s. Caindo para o canal simulado — "
            "nenhuma mensagem será entregue.",
            ", ".join(faltando),
        )
        return CanalSimulado()

    modo = (settings.TWILIO_MODO_ENVIO or "twiml").lower()
    if modo not in _MODOS_ENVIO:
        raise ValueError(f"TWILIO_MODO_ENVIO '{modo}' não suportado. Opções: twiml, rest")

    logger.warning(
        "CANAL_SAIDA=twilio (modo=%s) — mensagens aprovadas CHEGAM ao cliente real pelo WhatsApp.",
        modo,
    )
    return CanalTwilio(
        account_sid=account_sid,
        numero_whatsapp=numero,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        api_key_sid=settings.TWILIO_API_KEY_SID,
        api_key_secret=settings.TWILIO_API_KEY_SECRET,
        modo_envio=modo,
        url_publica=settings.APP_URL_PUBLICA,
    )
