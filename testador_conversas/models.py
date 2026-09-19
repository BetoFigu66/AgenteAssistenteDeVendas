"""Modelos do testador — tabelas próprias no schema `teste_conversas`.

Não reaproveita `backend/models` de propósito: este é "outro sistema", que só
conversa com o backend real por HTTP. Acoplar os dois pelo ORM criaria uma
dependência de import que a separação inteira existe pra evitar.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from config import SCHEMA
from sqlalchemy import DateTime, ForeignKey, MetaData, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class StatusNumero(str, enum.Enum):
    LIVRE = "livre"
    EM_USO = "em_uso"


class StatusExecucao(str, enum.Enum):
    RODANDO = "rodando"
    CONCLUIDA = "concluida"
    ABORTADA = "abortada"


class Veredito(str, enum.Enum):
    ACEITO_AUTOMATICO = "aceito_automatico"
    ACEITO_MANUAL = "aceito_manual"
    REJEITADO = "rejeitado"


def _enum_coluna(tipo_enum, nome: str):
    return SAEnum(tipo_enum, values_callable=lambda x: [e.value for e in x], name=nome, inherit_schema=True)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Cenario(Base):
    """Um roteiro de conversa — o que enviar, em que ordem (`turnos`)."""

    __tablename__ = "cenarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)

    turnos: Mapped[list["Turno"]] = relationship(
        back_populates="cenario", cascade="all, delete-orphan", order_by="Turno.ordem"
    )


class Turno(Base):
    """Um turno dentro de um cenário: uma mensagem enviada, na ordem `ordem`."""

    __tablename__ = "turnos"
    __table_args__ = (UniqueConstraint("cenario_id", "ordem", name="uq_turno_cenario_ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cenario_id: Mapped[int] = mapped_column(ForeignKey("cenarios.id"), nullable=False)
    ordem: Mapped[int] = mapped_column(nullable=False)
    mensagem_enviada: Mapped[str] = mapped_column(Text, nullable=False)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cenario: Mapped["Cenario"] = relationship(back_populates="turnos")
    respostas_aceitas: Mapped[list["RespostaAceita"]] = relationship(
        back_populates="turno", cascade="all, delete-orphan", order_by="RespostaAceita.id"
    )


class RespostaAceita(Base):
    """Uma resposta considerada válida para um turno — um turno pode ter várias
    (o sistema evolui, a redação muda, aceitamos novas variações ao longo do
    tempo sem perder o histórico das antigas — `ativo=False` em vez de apagar)."""

    __tablename__ = "respostas_aceitas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id"), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    ativo: Mapped[bool] = mapped_column(default=True, nullable=False)
    criado_por: Mapped[str] = mapped_column(String(50), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)

    turno: Mapped["Turno"] = relationship(back_populates="respostas_aceitas")


class NumeroTeste(Base):
    """Pool de números de telefone reservados pro testador usar."""

    __tablename__ = "numeros_teste"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status: Mapped[StatusNumero] = mapped_column(
        _enum_coluna(StatusNumero, "status_numero"), default=StatusNumero.LIVRE, nullable=False
    )
    cenario_atual_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cenarios.id"), nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=_utc_now, nullable=False
    )


class Execucao(Base):
    """Uma rodada de um cenário (histórico de execuções)."""

    __tablename__ = "execucoes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cenario_id: Mapped[int] = mapped_column(ForeignKey("cenarios.id"), nullable=False)
    numero_usado: Mapped[str] = mapped_column(String(20), nullable=False)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()", nullable=False)
    finalizado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[StatusExecucao] = mapped_column(
        _enum_coluna(StatusExecucao, "status_execucao"), default=StatusExecucao.RODANDO, nullable=False
    )

    cenario: Mapped["Cenario"] = relationship()
    resultados: Mapped[list["ResultadoTurno"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan", order_by="ResultadoTurno.id"
    )


class ResultadoTurno(Base):
    """O que foi observado e decidido, turno a turno, numa execução."""

    __tablename__ = "resultados_turno"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    execucao_id: Mapped[int] = mapped_column(ForeignKey("execucoes.id"), nullable=False)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id"), nullable=False)
    # Snapshot do que foi de fato enviado nesta execução — o turno pode mudar depois.
    mensagem_enviada: Mapped[str] = mapped_column(Text, nullable=False)
    resposta_observada: Mapped[str] = mapped_column(Text, nullable=False)
    veredito: Mapped[Veredito] = mapped_column(_enum_coluna(Veredito, "veredito"), nullable=False)
    decidido_por: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    decidido_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    execucao: Mapped["Execucao"] = relationship(back_populates="resultados")
    turno: Mapped["Turno"] = relationship()
