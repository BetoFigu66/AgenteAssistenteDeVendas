"""coluna ultima_mensagem_at em atendimentos

Revision ID: 2026061504
Revises: 2026061503
Create Date: 2026-06-16 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "2026061504"
down_revision: Union[str, None] = "2026061503"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "atendimentos",
        sa.Column("ultima_mensagem_at", sa.DateTime(timezone=True), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        text(
            """
            UPDATE atendimentos a
            SET ultima_mensagem_at = sub.max_ts
            FROM (
                SELECT atendimento_id, MAX(timestamp) AS max_ts
                FROM mensagens
                WHERE atendimento_id IS NOT NULL
                  AND origem::text = 'user'
                GROUP BY atendimento_id
            ) sub
            WHERE a.id = sub.atendimento_id
            """
        )
    )


def downgrade() -> None:
    op.drop_column("atendimentos", "ultima_mensagem_at")
