"""afrouxa_empresa_id_contato_negociacao

Torna empresa_id nullable em contatos e negociacoes, permitindo
contato/negociacao anonimos (antes do cliente fornecer CNPJ).

Revision ID: 2026060402
Revises: 2026060401
Create Date: 2026-06-06 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2026060402'
down_revision: Union[str, None] = '2026060401'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('contatos', 'empresa_id', nullable=True)
    op.alter_column('negociacoes', 'empresa_id', nullable=True)


def downgrade() -> None:
    # ATENCAO: o downgrade falhara se existirem linhas com empresa_id NULL.
    # Limpe/preencha esses registros antes de reverter.
    op.alter_column('negociacoes', 'empresa_id', nullable=False)
    op.alter_column('contatos', 'empresa_id', nullable=False)
