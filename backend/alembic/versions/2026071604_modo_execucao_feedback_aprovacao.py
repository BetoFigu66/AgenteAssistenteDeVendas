"""feedback_aprovacao em mensagens + historico_modo_execucao (REQ-011 Fase 2)

Revision ID: 2026071604
Revises: 2026071603
Create Date: 2026-07-16 16:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026071604"
down_revision: Union[str, None] = "2026071603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mensagens", sa.Column("feedback_aprovacao", sa.Text(), nullable=True))

    op.create_table(
        "historico_modo_execucao",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("modo_anterior", sa.String(length=30), nullable=True),
        sa.Column("modo_novo", sa.String(length=30), nullable=False),
        sa.Column("ator", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("historico_modo_execucao")
    op.drop_column("mensagens", "feedback_aprovacao")
