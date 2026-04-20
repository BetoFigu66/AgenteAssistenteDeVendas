"""Initial schema - tabela mensagens

Revision ID: 001
Revises: 
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mensagens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telefone', sa.String(length=20), nullable=False),
        sa.Column('conteudo', sa.Text(), nullable=False),
        sa.Column('origem', sa.Enum('user', 'system', name='origemmensagem'), nullable=False),
        sa.Column('message_sid', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_sid')
    )
    op.create_index('idx_mensagens_telefone', 'mensagens', ['telefone'], unique=False)
    op.create_index('idx_mensagens_telefone_timestamp', 'mensagens', ['telefone', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_mensagens_telefone_timestamp', table_name='mensagens')
    op.drop_index('idx_mensagens_telefone', table_name='mensagens')
    op.drop_table('mensagens')
    op.execute("DROP TYPE IF EXISTS origemmensagem")
