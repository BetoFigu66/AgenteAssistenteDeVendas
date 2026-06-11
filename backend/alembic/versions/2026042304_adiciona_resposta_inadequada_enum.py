"""adiciona resposta_inadequada ao enum categoriareport

Adiciona o valor 'resposta_inadequada' ao enum CategoriaReport no PostgreSQL.

Revision ID: a3c7e8f9d2b5
Revises: f8e3b5a2c9d4
Create Date: 2026-04-23 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c7e8f9d2b5'
down_revision: Union[str, None] = 'f8e3b5a2c9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona novo valor ao enum CategoriaReport no PostgreSQL
    op.execute("ALTER TYPE categoriareport ADD VALUE 'resposta_inadequada'")


def downgrade() -> None:
    # Remover valor de enum é complexo no PostgreSQL - requer recriar o tipo
    # Para simplificar, não suportamos downgrade desta migration
    pass
