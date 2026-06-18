"""coluna numero_atendimento_cliente em atendimentos (REQ-016 T-A4)

Revision ID: 2026061505
Revises: 2026061504
Create Date: 2026-06-17 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "2026061505"
down_revision: Union[str, None] = "2026061504"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "atendimentos",
        sa.Column("numero_atendimento_cliente", sa.Integer(), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        text(
            """
            WITH numbered AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY contato_id
                           ORDER BY created_at ASC, id ASC
                       ) AS num
                FROM atendimentos
            )
            UPDATE atendimentos a
            SET numero_atendimento_cliente = numbered.num
            FROM numbered
            WHERE a.id = numbered.id
            """
        )
    )

    op.alter_column("atendimentos", "numero_atendimento_cliente", nullable=False)

    op.create_unique_constraint(
        "uq_atendimentos_contato_numero",
        "atendimentos",
        ["contato_id", "numero_atendimento_cliente"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_atendimentos_contato_numero", "atendimentos", type_="unique")
    op.drop_column("atendimentos", "numero_atendimento_cliente")
