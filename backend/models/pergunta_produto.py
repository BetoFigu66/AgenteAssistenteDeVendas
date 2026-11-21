"""Texto de uma pergunta do roteiro de qualificação para um produto específico."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime
from .catalogo import Produto


class PerguntaProduto(Base):
    """
    Texto que substitui, para um produto (linha de `produtos`), a pergunta de um campo
    do roteiro de qualificação (`campo` = chave em `services/conversacao/catalogo_campos.py`,
    ex.: `modelo_produto`). Sem linha ativa, vale o texto do código. Editado no painel,
    aba Parâmetros, e lido por `services/perguntas_produto.py`.

    O texto aceita os mesmos placeholders do template do campo (ex.: `{produto}` na
    faixa de pessoas).
    """

    __tablename__ = "perguntas_produto"
    __table_args__ = (UniqueConstraint("produto_id", "campo"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True)
    campo: Mapped[str] = mapped_column(String(60), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    atualizado_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)

    produto: Mapped[Produto] = relationship()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "produto": self.produto.descricao if self.produto else None,
            "campo": self.campo,
            "texto": self.texto,
            "ativo": self.ativo,
            "atualizado_por": self.atualizado_por,
            "updated_at": serialize_utc_datetime(self.updated_at),
        }
