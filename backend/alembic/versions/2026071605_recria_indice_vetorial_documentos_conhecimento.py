"""recria_indice_vetorial_documentos_conhecimento

Revision ID: 2026071605
Revises: 2026071604
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026071605"
down_revision: Union[str, None] = "2026071604"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Indice vetorial de documentos_conhecimento.embedding foi removido pela
    # migration 3699280dbfe7 (adiciona_pares_qa) e nunca recriado no upgrade().
    # Usa HNSW (recomendado pelo pgvector sobre ivfflat) por nao depender de
    # tunar "lists" conforme o volume de linhas e por indexar bem mesmo com a
    # tabela ainda pequena/crescente.
    op.execute(
        """
        CREATE INDEX idx_documentos_conhecimento_embedding_cosine
        ON documentos_conhecimento
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documentos_conhecimento_embedding_cosine")
