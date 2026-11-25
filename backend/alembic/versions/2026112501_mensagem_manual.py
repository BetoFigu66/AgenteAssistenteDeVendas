"""mensagens: coluna `manual` (resposta escrita pelo atendente)

Até aqui a mensagem manual do atendente (`POST /api/atendimentos/{id}/mensagens-manuais`) e a
resposta gerada pela IA eram gravadas iguais (`origem=system`, aprovadas), e nada no banco dizia
quem escreveu. O App Android mostra a diferença na conversa, como o goal app-android-04 pede.

As mensagens existentes ficam `false`: em 25/11/2026 o banco não tinha nenhuma mensagem manual
(todas as do sistema vinham do processador).

Revision ID: 2026112501
Revises: 2026112201
Create Date: 2026-11-25 09:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026112501"
down_revision: Union[str, None] = "2026112201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mensagens",
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("mensagens", "manual")
