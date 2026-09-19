"""Contrato do canal de saída: por onde uma mensagem gerada chega ao cliente.

Eixo independente do `ModoExecucao` (`models/parametro.py`), que decide *se* a
mensagem pode sair (aprovação humana). Este decide *por onde* sai, depois que já
pode. Configurado em `CANAL_SAIDA` (`.env`), não no banco, porque é trava de
ambiente: trocar o modo de execução pelo painel nunca deve, sozinho, começar a
mandar mensagem de verdade para um cliente real.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResultadoEnvio:
    """O que aconteceu com uma tentativa de entrega.

    Três estados possíveis, e o do meio é o que costuma ser esquecido:

    - entregue=True                  → saiu, `message_sid` preenchido.
    - entregue=False, erro=None      → o canal não entrega (simulado). Não é falha:
                                       a mensagem fica registrada e ninguém recebeu.
    - entregue=False, erro="..."     → tentamos e falhou (ex.: janela de 24h vencida).
    """

    entregue: bool
    message_sid: Optional[str] = None
    erro: Optional[str] = None

    @property
    def falhou(self) -> bool:
        return self.erro is not None


class CanalSaida(ABC):
    """Interface mínima de um canal de saída."""

    nome: str = "abstrato"
    # `False` quando nada chega de fato ao cliente. Quem chama usa isso para decidir
    # se vale marcar `Mensagem.timestamp_envio`.
    entrega_real: bool = False

    @abstractmethod
    def enviar(self, telefone: str, texto: str, *, mensagem_id: Optional[int] = None) -> ResultadoEnvio:
        """Entrega `texto` a `telefone` fora de qualquer webhook em andamento.

        É o caminho de aprovação (REQ-011.11) e de resposta manual (REQ-008.5): nesses
        dois não existe requisição da Twilio aberta para responder, então não há como
        usar TwiML.

        `mensagem_id` é só para correlação (URL de `statusCallback` e log). O canal
        não escreve no banco — quem chamou é que persiste o resultado.
        """

    def entrega_na_resposta_do_webhook(self) -> bool:
        """True quando a entrega síncrona acontece respondendo o próprio POST do webhook.

        É o caso do TwiML: a mensagem sai como resposta HTTP, não por chamada de API.
        Quem responde o webhook precisa saber disso para não entregar duas vezes.
        """
        return False

    def url_status_callback(self, mensagem_id: int) -> Optional[str]:
        """URL que a Twilio chama com o SID da mensagem que acabou de enviar.

        É a única forma de descobrir o SID de algo enviado por TwiML: a resposta do
        webhook não devolve SID nenhum. `None` quando o canal não precisa disso ou
        quando falta `APP_URL_PUBLICA`.
        """
        return None
