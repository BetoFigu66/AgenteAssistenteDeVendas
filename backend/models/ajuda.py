"""
Modulo de ajuda contextual do painel (FAQ por tela).

Proposital e importante: estas tabelas sao **independentes** de `pares_qa` /
`documentos_conhecimento`, que alimentam as respostas enviadas ao cliente no
WhatsApp. Sao publicos diferentes (operador interno x cliente final) e misturar
os dois arriscaria um texto de ajuda do painel ser enviado a um cliente.
Nada aqui e consultado pelo `ProcessadorMensagem`.

Camadas de conteudo de ajuda no projeto:
  1. `frontend/src/ajuda/<tela>.md` — explicacao completa da tela (versionada em git).
  2. `ajuda_conteudos` (aqui)       — perguntas pontuais, editaveis pelo painel.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.datetime_utils import serialize_utc_datetime, utc_now

from .base import Base, UTCDateTime, Vector


class AjudaContexto(Base):
    """
    Catalogo dos "lugares" do painel que podem ter ajuda.

    Existe para dar integridade referencial a `chave`: sem o catalogo, um typo no
    contexto ("parametro" em vez de "parametros") faria o conteudo simplesmente
    nunca aparecer, sem erro nenhum. Tambem guarda o rotulo amigavel num lugar so.

    A `chave` acompanha a convencao ja usada no frontend (`tela` ou `tela.subarea`,
    ex.: "reports", "reports.detalhe") e casa com os arquivos
    `frontend/src/ajuda/<chave>.md`.
    """

    __tablename__ = "ajuda_contextos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    rotulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    conteudos: Mapped[List["AjudaConteudo"]] = relationship(back_populates="contexto")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chave": self.chave,
            "rotulo": self.rotulo,
            "descricao": self.descricao,
            "ativo": self.ativo,
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
        }


class AjudaConteudo(Base):
    """
    Par pergunta/resposta de ajuda, opcionalmente amarrado a um contexto.

    `contexto_id` nulo significa ajuda **global**: vale em qualquer tela (ex.:
    "como troco minha senha"). A busca considera o contexto pedido, seus ancestrais
    e os globais, nessa ordem de preferencia.

    Como em `pares_qa`, o embedding e gerado a partir da *pergunta* (nao da
    resposta) — e a pergunta que se parece com o que o usuario digita. Diferente de
    `pares_qa`, aqui nao ha workflow de aprovacao: o publico e interno e o risco de
    uma resposta ruim e baixo, entao a friccao de duas etapas nao se paga.

    `embedding` e nullable de proposito: se o provider de embeddings estiver
    indisponivel na hora de salvar, o conteudo e gravado mesmo assim e continua
    encontravel por full-text — degradacao graciosa em vez de bloquear a edicao.
    """

    __tablename__ = "ajuda_conteudos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contexto_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ajuda_contextos.id"), nullable=True, index=True
    )
    pergunta: Mapped[str] = mapped_column(Text, nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    # Ordena as sugestoes exibidas quando o usuario abre a ajuda sem perguntar nada
    # (maior primeiro). Nao influencia a busca por pergunta.
    prioridade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    pergunta_tsv: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    criado_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    contexto: Mapped[Optional["AjudaContexto"]] = relationship(back_populates="conteudos")

    __table_args__ = (
        Index("idx_ajuda_conteudos_contexto_ativo", "contexto_id", "ativo"),
        Index("idx_ajuda_conteudos_pergunta_tsv", "pergunta_tsv", postgresql_using="gin"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contexto_id": self.contexto_id,
            "contexto_chave": self.contexto.chave if self.contexto else None,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "tags": self.tags or [],
            "prioridade": self.prioridade,
            "ativo": self.ativo,
            # Nao serializa o vetor (1536 floats); expoe so se ele existe, que e o
            # que o painel precisa saber para avisar "sem busca semantica".
            "tem_embedding": self.embedding is not None,
            "criado_por": self.criado_por,
            "created_at": serialize_utc_datetime(self.created_at),
            "updated_at": serialize_utc_datetime(self.updated_at),
        }


class AjudaConsulta(Base):
    """
    Registro de cada pergunta feita a ajuda — inclusive as que acharam resposta.

    Guardar tudo (e nao so as falhas) custa o mesmo e responde duas perguntas em vez
    de uma: "o que falta escrever" (`WHERE NOT encontrou`) e "o que mais perguntam"
    (agrupando as que encontraram). O contexto e gravado como texto, nao como FK,
    porque a tela pode mandar um contexto que nem existe no catalogo — e justamente
    isso que se quer enxergar.
    """

    __tablename__ = "ajuda_consultas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pergunta: Mapped[str] = mapped_column(Text, nullable=False)
    contexto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    encontrou: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    conteudo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ajuda_conteudos.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # "fulltext" | "embedding" | None (quando nao encontrou).
    origem_busca: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    usuario: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_ajuda_consultas_encontrou_data", "encontrou", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pergunta": self.pergunta,
            "contexto": self.contexto,
            "encontrou": self.encontrou,
            "conteudo_id": self.conteudo_id,
            "score": self.score,
            "origem_busca": self.origem_busca,
            "usuario": self.usuario,
            "created_at": serialize_utc_datetime(self.created_at),
        }
