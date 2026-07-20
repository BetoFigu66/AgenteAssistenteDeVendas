"""torna preco tabela modelo opcional

Revision ID: 2026071703
Revises: 2026071702
Create Date: 2026-07-17 17:03:02.310292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026071703"
down_revision: Union[str, None] = "2026071702"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "modelos",
        "preco_tabela",
        existing_type=sa.Numeric(precision=15, scale=2),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "modelos",
        "preco_tabela",
        existing_type=sa.Numeric(precision=15, scale=2),
        nullable=False,
    )
