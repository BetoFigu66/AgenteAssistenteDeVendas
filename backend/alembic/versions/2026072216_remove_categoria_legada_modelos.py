"""remove categoria legada modelos

Revision ID: 2026072216
Revises: 2026072114
Create Date: 2026-07-22 16:32:31.123539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026072216'
down_revision: Union[str, None] = '2026072114'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("modelos", "categoria")


def downgrade() -> None:
    op.add_column("modelos", sa.Column("categoria", sa.String(length=100), nullable=True))
