"""Canal que não entrega nada — default do sistema."""

import logging
from typing import Optional

from .base import CanalSaida, ResultadoEnvio

logger = logging.getLogger(__name__)


class CanalSimulado(CanalSaida):
    """Registra o que seria enviado e não envia.

    É o comportamento histórico do sistema, agora explícito: aprovar uma mensagem ou
    responder manualmente sempre gravou no banco sem nada chegar ao cliente. A
    diferença é que agora isso é uma escolha declarada em `CANAL_SAIDA`, e não uma
    lacuna silenciosa.

    Não devolve `message_sid`: sem Twilio não existe SID. O reply-to continua
    funcionando na interface web, que usa o id da mensagem em vez do SID.
    """

    nome = "simulado"
    entrega_real = False

    def enviar(self, telefone: str, texto: str, *, mensagem_id: Optional[int] = None) -> ResultadoEnvio:
        logger.info(
            "[CanalSimulado] Não enviado (CANAL_SAIDA=simulado) — telefone=%s mensagem_id=%s texto=%r",
            telefone,
            mensagem_id,
            texto[:80],
        )
        return ResultadoEnvio(entregue=False)
