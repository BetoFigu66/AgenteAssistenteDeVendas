"""report: correção automática por goal do Claude

`correcao_automatica` é marcado na triagem e põe o report na fila da ponte
(`backend/scripts/ponte_reports_goals.py`), que cria um goal para o Claude analisar a causa
raiz, escrever o teste que falha, corrigir, publicar e fazer o deploy. `goal_id` registra o
goal criado; nulo enquanto o report espera na fila.

Revision ID: 2026112101
Revises: 2026110201
Create Date: 2026-11-21 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026112101"
down_revision: Union[str, None] = "2026110201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports_problema",
        sa.Column("correcao_automatica", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("reports_problema", sa.Column("goal_id", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("reports_problema", "goal_id")
    op.drop_column("reports_problema", "correcao_automatica")
