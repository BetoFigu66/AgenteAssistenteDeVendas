"""adiciona_login_senha_users

Revision ID: 2026071701
Revises: 2026071606
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026071701"
down_revision: Union[str, None] = "2026071606"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-010 (Fase 4): autenticação mínima. Nullable porque usuários criados antes
    # desta fase (ex.: seeds de teste) não têm senha até alguém definir uma via
    # PATCH /api/users/{id}/senha.
    op.add_column("users", sa.Column("login", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("senha_hash", sa.String(length=255), nullable=True))
    op.create_index("ix_users_login", "users", ["login"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_login", table_name="users")
    op.drop_column("users", "senha_hash")
    op.drop_column("users", "login")
