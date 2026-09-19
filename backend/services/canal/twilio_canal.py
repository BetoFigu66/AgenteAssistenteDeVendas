"""Canal de saída real, via Twilio WhatsApp (REQ-008, Fase 10).

Dois caminhos de entrega, escolhidos por `TWILIO_MODO_ENVIO`:

- **twiml**: a resposta síncrona do webhook carrega o texto. É o único que funciona em
  conta trial/Sandbox — lá a API recusa texto livre (erro 21654, exige `ContentSid`, e
  a Content API pede conta paga). O preço é não saber o SID na hora; ele chega depois
  pelo `statusCallback`.
- **rest**: o webhook devolve TwiML vazio e a mensagem sai pela API, que devolve o SID
  na mesma chamada. Exige conta paga.

Aprovação e resposta manual usam REST nos dois modos: nesses caminhos não há webhook
aberto para responder.

Histórico do que foi descoberto na prática (números de erro, pegadinhas do Sandbox,
o porquê do `statusCallback`): `AnotacoesPessoais/Beto/spike_twilio/STATUS.md`.
"""

import logging
from typing import Optional
from urllib.parse import quote

from .base import CanalSaida, ResultadoEnvio

logger = logging.getLogger(__name__)

# Erros da Twilio que valem uma mensagem em português em vez do texto cru da API.
# 63016 é a colisão entre o gate de aprovação (REQ-011) e a janela de 24h do WhatsApp:
# uma resposta aprovada tarde demais não é entregue sem template aprovado.
_ERROS_CONHECIDOS = {
    63016: (
        "Fora da janela de 24h do WhatsApp: o cliente não manda mensagem há mais de "
        "24 horas e texto livre não é mais aceito. Só um template aprovado reabre a conversa."
    ),
    21654: (
        "O Sandbox da Twilio não aceita texto livre pela API (exige um template). "
        "Use TWILIO_MODO_ENVIO=twiml enquanto a conta for trial."
    ),
    63015: "Número de destino não está pareado com o Sandbox do WhatsApp.",
}


def _com_prefixo_whatsapp(numero: str) -> str:
    return numero if numero.startswith("whatsapp:") else f"whatsapp:{numero}"


class CanalTwilio(CanalSaida):
    """Entrega mensagens pelo WhatsApp da Twilio."""

    nome = "twilio"
    entrega_real = True

    def __init__(
        self,
        *,
        account_sid: str,
        numero_whatsapp: str,
        auth_token: Optional[str] = None,
        api_key_sid: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        modo_envio: str = "twiml",
        url_publica: Optional[str] = None,
    ):
        self._account_sid = account_sid
        self._numero = _com_prefixo_whatsapp(numero_whatsapp)
        self._auth_token = auth_token
        self._api_key_sid = api_key_sid
        self._api_key_secret = api_key_secret
        self._modo_envio = (modo_envio or "twiml").lower()
        self._url_publica = (url_publica or "").rstrip("/") or None
        self._cliente_cache = None

        if self._modo_envio == "twiml" and not self._url_publica:
            logger.warning(
                "[CanalTwilio] TWILIO_MODO_ENVIO=twiml sem APP_URL_PUBLICA: as mensagens saem, "
                "mas o SID de saída nunca é capturado e o 'Responder' do WhatsApp fica sem resolver."
            )

    # ------------------------------------------------------------------
    # Cliente REST (preguiçoso: em modo twiml ele pode nunca ser usado)
    # ------------------------------------------------------------------

    @property
    def _cliente(self):
        if self._cliente_cache is None:
            from twilio.rest import Client

            if self._api_key_sid and self._api_key_secret:
                # Com API Key a assinatura é (key_sid, secret, account_sid) — a chave
                # entra no lugar do usuário e a conta vira o terceiro argumento.
                self._cliente_cache = Client(self._api_key_sid, self._api_key_secret, self._account_sid)
            else:
                self._cliente_cache = Client(self._account_sid, self._auth_token)
        return self._cliente_cache

    # ------------------------------------------------------------------
    # Contrato
    # ------------------------------------------------------------------

    def entrega_na_resposta_do_webhook(self) -> bool:
        return self._modo_envio == "twiml"

    def url_status_callback(self, mensagem_id: int) -> Optional[str]:
        if not self._url_publica:
            return None
        return f"{self._url_publica}/webhook/status?mensagem_id={quote(str(mensagem_id))}"

    def enviar(self, telefone: str, texto: str, *, mensagem_id: Optional[int] = None) -> ResultadoEnvio:
        destino = _com_prefixo_whatsapp(telefone)
        callback = self.url_status_callback(mensagem_id) if mensagem_id is not None else None

        try:
            extras = {"status_callback": callback} if callback else {}
            msg = self._cliente.messages.create(from_=self._numero, to=destino, body=texto, **extras)
        except Exception as e:  # noqa: BLE001 — qualquer falha aqui vira erro registrado, não exceção
            erro = self._descrever_erro(e)
            logger.warning("[CanalTwilio] Falha ao enviar para %s (mensagem_id=%s): %s", destino, mensagem_id, erro)
            return ResultadoEnvio(entregue=False, erro=erro)

        logger.info("[CanalTwilio] Enviado para %s — sid=%s mensagem_id=%s", destino, msg.sid, mensagem_id)
        return ResultadoEnvio(entregue=True, message_sid=msg.sid)

    @staticmethod
    def _descrever_erro(excecao: Exception) -> str:
        codigo = getattr(excecao, "code", None)
        conhecido = _ERROS_CONHECIDOS.get(codigo) if isinstance(codigo, int) else None
        if conhecido:
            return f"[Twilio {codigo}] {conhecido}"
        if codigo:
            return f"[Twilio {codigo}] {str(excecao)[:300]}"
        return str(excecao)[:300]
