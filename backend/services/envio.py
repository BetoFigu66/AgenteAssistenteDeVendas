"""Entrega de uma `Mensagem` já persistida pelo canal de saída configurado.

Ponte entre o canal (transporte puro, sem ORM — `services/canal/`) e o banco. Existe
para que os três caminhos que entregam algo ao cliente gravem o resultado do mesmo
jeito, em vez de cada um inventar o seu:

1. aprovação de mensagem pendente (`POST /api/mensagens/{id}/aprovar`, REQ-011.11)
2. resposta manual em modo HUMANO (`POST /api/atendimentos/{id}/mensagens-manuais`, REQ-008.5)
3. resposta automática do webhook quando `TWILIO_MODO_ENVIO=rest`

O caminho TwiML (`TWILIO_MODO_ENVIO=twiml`) NÃO passa por aqui: lá a entrega é a
própria resposta HTTP do webhook, e quem marca o envio é `main.py::webhook_twilio`.
"""

import logging
from typing import Optional

from models import Mensagem
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from services.canal import CanalSaida, ResultadoEnvio, obter_canal

logger = logging.getLogger(__name__)


def entregar_mensagem(db: Session, mensagem: Mensagem, canal: Optional[CanalSaida] = None) -> ResultadoEnvio:
    """Entrega `mensagem` ao cliente e registra o desfecho na própria linha.

    Nunca levanta exceção por falha de entrega: o erro vira `Mensagem.erro_envio`, que
    a interface mostra. Uma aprovação não deve virar HTTP 500 porque o WhatsApp
    recusou — a decisão humana aconteceu de verdade e precisa ficar registrada.
    """
    canal = canal or obter_canal()

    resultado = canal.enviar(mensagem.telefone, mensagem.conteudo, mensagem_id=mensagem.id)

    if resultado.entregue:
        mensagem.timestamp_envio = utc_now()
        mensagem.erro_envio = None
        if resultado.message_sid:
            mensagem.message_sid = resultado.message_sid
    elif resultado.falhou:
        mensagem.erro_envio = resultado.erro
        logger.warning("[Envio] mensagem_id=%s não entregue: %s", mensagem.id, resultado.erro)

    db.flush()
    return resultado


def marcar_entregue_por_twiml(mensagem: Mensagem) -> None:
    """Marca como entregue a mensagem que sai na resposta TwiML do webhook.

    Otimista de propósito: o TwiML foi entregue à Twilio, mas o SID e o status real
    (`sent`/`delivered`/`failed`) só chegam depois, pelo `statusCallback`. É de lá que
    sai a correção, se a entrega falhar.
    """
    mensagem.timestamp_envio = utc_now()
    mensagem.erro_envio = None
