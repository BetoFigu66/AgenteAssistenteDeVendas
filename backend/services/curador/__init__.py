"""Serviços do fluxo [curador_conhecimento]."""

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "montar_pacote_analise":
        from .pacote_analise import montar_pacote_analise

        return montar_pacote_analise
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["montar_pacote_analise"]
