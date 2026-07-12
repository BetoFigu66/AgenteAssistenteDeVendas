"""adiciona fase em atendimentos (MVP Continuidade, passo A2)

Cria o ENUM `faseatendimento` (esclarecendo, finalizando, em_orcamentacao) e
adiciona a coluna `fase` em `atendimentos` com default 'esclarecendo' —
eixo ortogonal a `status` (REQ-016): `status` indica se o atendimento está
aberto pra interação (ativo/encerrado); `fase` indica em que ponto do fluxo
guiado ele está enquanto ativo. Ver `FaseAtendimento` em `models.py` e
`docs/dicionario_termos.md` (entrada "Fase (do atendimento)").

Segue o mesmo padrão da migration e8a2b6c4f9d1 (adiciona modo_operacao).

Revision ID: 2026071101
Revises: 2026071002
Create Date: 2026-07-11 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2026071101"
down_revision: Union[str, None] = "2026071002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FASE_VALUES = ("esclarecendo", "finalizando", "em_orcamentacao")


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Cria o TYPE ENUM no Postgres
    postgresql.ENUM(*FASE_VALUES, name="faseatendimento").create(bind, checkfirst=True)

    fase_enum = postgresql.ENUM(*FASE_VALUES, name="faseatendimento", create_type=False)

    # 2) Adiciona a coluna com default 'esclarecendo' (respeita atendimentos existentes)
    op.add_column(
        "atendimentos",
        sa.Column("fase", fase_enum, nullable=False, server_default="esclarecendo"),
    )

    # 3) Índice para consulta rápida por fase
    op.create_index("ix_atendimentos_fase", "atendimentos", ["fase"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_atendimentos_fase", table_name="atendimentos")
    op.drop_column("atendimentos", "fase")

    postgresql.ENUM(name="faseatendimento").drop(bind, checkfirst=True)
