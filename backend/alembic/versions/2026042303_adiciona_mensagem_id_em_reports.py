"""adiciona mensagem_id em reports_problema

Adiciona coluna mensagem_id (FK -> mensagens.id, nullable) na tabela
reports_problema para vincular reports a mensagens específicas quando
o usuário reprovar uma mensagem gerada pelo agente.

Revision ID: f8e3b5a2c9d4
Revises: e8a2b6c4f9d1
Create Date: 2026-04-23 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8e3b5a2c9d4'
down_revision: Union[str, None] = 'e8a2b6c4f9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Torna processamento_id nullable (para permitir reports de mensagens sem processamento)
    op.alter_column(
        'reports_problema',
        'processamento_id',
        existing_type=sa.Integer(),
        nullable=True
    )
    
    # Adiciona coluna mensagem_id
    op.add_column(
        'reports_problema',
        sa.Column('mensagem_id', sa.Integer(), nullable=True)
    )
    
    # Cria índice
    op.create_index(
        'idx_reports_mensagem_id',
        'reports_problema',
        ['mensagem_id']
    )
    
    # Cria foreign key
    op.create_foreign_key(
        'fk_reports_problema_mensagem_id',
        'reports_problema',
        'mensagens',
        ['mensagem_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove foreign key
    op.drop_constraint('fk_reports_problema_mensagem_id', 'reports_problema', type_='foreignkey')
    
    # Remove índice
    op.drop_index('idx_reports_mensagem_id', 'reports_problema')
    
    # Remove coluna
    op.drop_column('reports_problema', 'mensagem_id')
    
    # Restaura processamento_id como not null
    op.alter_column(
        'reports_problema',
        'processamento_id',
        existing_type=sa.Integer(),
        nullable=False
    )
