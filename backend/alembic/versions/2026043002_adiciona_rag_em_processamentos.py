"""adiciona campos de RAG em processamentos_mensagem

Revision ID: 2026043002
Revises: 2026043001
Create Date: 2026-04-30 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2026043002"
down_revision: Union[str, None] = "2026043001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "processamentos_mensagem",
        sa.Column(
            "rag_utilizada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "processamentos_mensagem",
        sa.Column(
            "rag_trechos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "processamentos_mensagem",
        sa.Column(
            "rag_score_maximo",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
    )
    # Remove o server_default apos o backfill implicito (proximas linhas usam
    # o default da aplicacao).
    op.alter_column(
        "processamentos_mensagem",
        "rag_utilizada",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("processamentos_mensagem", "rag_score_maximo")
    op.drop_column("processamentos_mensagem", "rag_trechos")
    op.drop_column("processamentos_mensagem", "rag_utilizada")
