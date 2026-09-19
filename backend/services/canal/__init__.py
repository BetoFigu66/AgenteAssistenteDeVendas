"""Canal de saída: por onde uma mensagem gerada chega (ou não) ao cliente."""

from .base import CanalSaida, ResultadoEnvio
from .factory import obter_canal
from .simulado import CanalSimulado
from .twilio_canal import CanalTwilio

__all__ = [
    "CanalSaida",
    "CanalSimulado",
    "CanalTwilio",
    "ResultadoEnvio",
    "obter_canal",
]
