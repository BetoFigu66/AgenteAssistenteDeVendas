"""adiciona fase_atendimento em processamentos_mensagem (debug "Raciocínio do cérebro")

Guarda a fase do atendimento (esclarecendo/finalizando/em_orcamentacao) no momento em
que a mensagem foi analisada — snapshot pré-decisão, não a fase atual do atendimento
(que pode já ter mudado desde então, ex.: a própria mensagem pode ter disparado a
transição). Coluna `String` solta (não FK/enum) — é só um snapshot textual para debug,
não precisa acompanhar o ciclo de vida do enum `faseatendimento`.

Revision ID: 2026071401
Revises: 2026071102
Create Date: 2026-07-14 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026071401"
down_revision: Union[str, None] = "2026071102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "processamentos_mensagem",
        sa.Column("fase_atendimento", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("processamentos_mensagem", "fase_atendimento")
