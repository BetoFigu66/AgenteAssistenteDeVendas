"""Geração de respostas para o cliente."""

from .catalogo import CATALOGO, MensagemId, MensagemTemplate, renderizar_mensagem

__all__ = [
    "CATALOGO",
    "GeradorRespostas",
    "MensagemId",
    "MensagemTemplate",
    "RespostaGerada",
    "renderizar_mensagem",
]


def __getattr__(name: str):
    if name == "GeradorRespostas":
        from .gerador import GeradorRespostas

        return GeradorRespostas
    if name == "RespostaGerada":
        from .gerador import RespostaGerada

        return RespostaGerada
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
