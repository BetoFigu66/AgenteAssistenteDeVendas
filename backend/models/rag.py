"""Base de conhecimento para RAG e pares Q&A curados."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime, Vector


class DocumentoConhecimento(Base):
    """
    Chunk/documento de conhecimento usado pela RAG.

    A coluna no banco chama-se `metadata`, mas no modelo usamos `metadados`
    porque `metadata` e reservado pelo SQLAlchemy Declarative.
    """

    __tablename__ = "documentos_conhecimento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_externo: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    id_documento_origem: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    id_fonte: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    metadados: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    conteudo_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_documentos_conhecimento_tipo_ativo", "tipo", "ativo"),
        Index("idx_documentos_conhecimento_titulo", "titulo"),
        Index("idx_documentos_conhecimento_hash", "conteudo_hash"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "id_externo": self.id_externo,
            "id_documento_origem": self.id_documento_origem,
            "id_fonte": self.id_fonte,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "conteudo": self.conteudo,
            "metadata": self.metadados,
            "conteudo_hash": self.conteudo_hash,
            "ativo": self.ativo,
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
        }


class ParQA(Base):
    """
    Par Pergunta+Resposta curado para busca semântica.

    O embedding é gerado a partir do campo `pergunta` (não da resposta),
    maximizando a similaridade cosseno com queries dos usuários.
    """

    __tablename__ = "pares_qa"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_externo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    pergunta: Mapped[str] = mapped_column(Text, nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    contexto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    pergunta_tsv: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aprovado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criado_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_pares_qa_contexto_ativo", "contexto", "ativo"),
        Index("idx_pares_qa_aprovado_ativo", "aprovado", "ativo"),
        Index("idx_pares_qa_pergunta_tsv", "pergunta_tsv", postgresql_using="gin"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "id_externo": self.id_externo,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "contexto": self.contexto,
            "tags": self.tags or [],
            "ativo": self.ativo,
            "aprovado": self.aprovado,
            "criado_por": self.criado_por,
            "criado_em": serialize_utc_datetime(self.criado_em),
            "atualizado_em": serialize_utc_datetime(self.atualizado_em),
        }
