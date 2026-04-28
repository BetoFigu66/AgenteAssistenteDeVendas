"""check: processamento_id ou mensagem_id deve ser not null

Adiciona constraint CHECK para garantir que pelo menos um dos campos
(processamento_id ou mensagem_id) seja preenchido em reports_problema.

Revision ID: b4d8f0e1c3a6
Revises: a3c7e8f9d2b5
Create Date: 2026-04-23 11:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d8f0e1c3a6'
down_revision: Union[str, None] = 'a3c7e8f9d2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove NOT NULL de processamento_id para permitir reports vinculados apenas a mensagem
    op.alter_column(
        'reports_problema',
        'processamento_id',
        existing_type=sa.Integer(),
        nullable=True
    )

    # Adiciona constraint CHECK para garantir que pelo menos um campo esteja preenchido
    op.execute("""
        ALTER TABLE reports_problema 
        ADD CONSTRAINT chk_processamento_ou_mensagem_not_null 
        CHECK (processamento_id IS NOT NULL OR mensagem_id IS NOT NULL)
    """)


def downgrade() -> None:
    # Remove a constraint
    op.execute("""
        ALTER TABLE reports_problema 
        DROP CONSTRAINT IF EXISTS chk_processamento_ou_mensagem_not_null
    """)
