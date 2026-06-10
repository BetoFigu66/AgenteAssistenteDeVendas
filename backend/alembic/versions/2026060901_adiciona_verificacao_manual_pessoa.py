"""adiciona_verificacao_manual_pessoa

Acrescenta em `pessoas` os campos `user_id_verificador` (FK -> users.id) e
`timestamp_verificacao`, para registrar confirmação manual dos dados de PF
(CPF, nome, data de nascimento) sem API externa.

Revision ID: 2026060901
Revises: 2026060601
Create Date: 2026-06-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2026060901'
down_revision: Union[str, None] = '2026060601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pessoas', sa.Column('user_id_verificador', sa.Integer(), nullable=True))
    op.add_column('pessoas', sa.Column('timestamp_verificacao', sa.DateTime(), nullable=True))
    op.create_index(
        op.f('ix_pessoas_user_id_verificador'),
        'pessoas',
        ['user_id_verificador'],
        unique=False,
    )
    op.create_foreign_key(
        op.f('fk_pessoas_user_id_verificador_users'),
        'pessoas',
        'users',
        ['user_id_verificador'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f('fk_pessoas_user_id_verificador_users'),
        'pessoas',
        type_='foreignkey',
    )
    op.drop_index(op.f('ix_pessoas_user_id_verificador'), table_name='pessoas')
    op.drop_column('pessoas', 'timestamp_verificacao')
    op.drop_column('pessoas', 'user_id_verificador')
