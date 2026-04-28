"""adiciona users e aprovacao de mensagens

Cria tabela `users` (id, nome, created_at) e acrescenta em `mensagens` os
campos `aprovador_id` (FK -> users.id) e `timestamp_aprovacao`, usados para
registrar aprovação humana de mensagens geradas pelo agente antes do envio.

Sem tratamento de login nesta etapa.

Revision ID: c5d9f1a8e3b7
Revises: a7f3e8c1d2b4
Create Date: 2026-04-23 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d9f1a8e3b7'
down_revision: Union[str, None] = 'a7f3e8c1d2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Tabela users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2) Campos de aprovação em mensagens
    op.add_column(
        'mensagens',
        sa.Column('aprovador_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'mensagens',
        sa.Column('timestamp_aprovacao', sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        'fk_mensagens_aprovador_users',
        source_table='mensagens',
        referent_table='users',
        local_cols=['aprovador_id'],
        remote_cols=['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_mensagens_aprovador_id',
        'mensagens',
        ['aprovador_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_mensagens_aprovador_id', table_name='mensagens')
    op.drop_constraint(
        'fk_mensagens_aprovador_users', 'mensagens', type_='foreignkey'
    )
    op.drop_column('mensagens', 'timestamp_aprovacao')
    op.drop_column('mensagens', 'aprovador_id')

    op.drop_table('users')
