"""Cumprimentos cadastrados no painel: o que conta como início de conversa e como responder."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime


class Cumprimento(Base):
    """
    Expressão de cumprimento ("bom dia", "e aí bro") e a resposta que abre a mensagem do
    assistente ("Bom dia!", "E aí?"). Lida por `services/cumprimentos.py`, que alimenta o
    classificador (a mensagem com uma expressão cadastrada é `SAUDACAO`) e a primeira
    frase das saudações.

    `resposta` vazia: a expressão conta como cumprimento mas não escolhe a resposta (ex.:
    "tudo bem"); vale outra expressão da mesma mensagem, ou "Olá!".
    """

    __tablename__ = "cumprimentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    expressao: Mapped[str] = mapped_column(String(100), nullable=False)
    """Como foi digitada no painel."""
    expressao_normalizada: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    """Sem acento, pontuação e maiúsculas: é o que se compara com a mensagem."""
    resposta: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    atualizado_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expressao": self.expressao,
            "resposta": self.resposta,
            "ativo": self.ativo,
            "atualizado_por": self.atualizado_por,
            "updated_at": serialize_utc_datetime(self.updated_at),
        }
