"""indice_vetorial_pares_qa

Revision ID: 2026072004
Revises: 2026072003
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026072004"
down_revision: Union[str, None] = "2026072003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-013 (Fase 9): `pares_qa.embedding` nunca teve indice vetorial — toda busca
    # semantica de QA fazia sequential scan. Mesmo padrao HNSW ja usado em
    # `documentos_conhecimento` (migration 2026071605): nao depende de tunar "lists"
    # conforme o volume, e indexa bem mesmo com a tabela ainda pequena/crescente.
    op.execute(
        """
        CREATE INDEX idx_pares_qa_embedding_cosine
        ON pares_qa
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pares_qa_embedding_cosine")
