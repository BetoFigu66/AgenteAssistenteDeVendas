"""cria documentos_conhecimento com pgvector

Revision ID: 2026043001
Revises: b4d8f0e1c3a6
Create Date: 2026-04-30 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType


# revision identifiers, used by Alembic.
revision: str = "2026043001"
down_revision: Union[str, None] = "b4d8f0e1c3a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class Vector(UserDefinedType):
    """Tipo pgvector usado na migration."""

    cache_ok = True

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def get_col_spec(self, **kw) -> str:
        return f"vector({self.dimensions})"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documentos_conhecimento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_externo", sa.String(length=500), nullable=False),
        sa.Column("id_documento_origem", sa.String(length=500), nullable=False),
        sa.Column("id_fonte", sa.String(length=64), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conteudo_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_externo", name="uq_documentos_conhecimento_id_externo"),
    )

    op.create_index(
        "idx_documentos_conhecimento_id_documento_origem",
        "documentos_conhecimento",
        ["id_documento_origem"],
        unique=False,
    )
    op.create_index(
        "idx_documentos_conhecimento_id_fonte",
        "documentos_conhecimento",
        ["id_fonte"],
        unique=False,
    )
    op.create_index(
        "idx_documentos_conhecimento_tipo_ativo",
        "documentos_conhecimento",
        ["tipo", "ativo"],
        unique=False,
    )
    op.create_index(
        "idx_documentos_conhecimento_titulo",
        "documentos_conhecimento",
        ["titulo"],
        unique=False,
    )
    op.create_index(
        "idx_documentos_conhecimento_hash",
        "documentos_conhecimento",
        ["conteudo_hash"],
        unique=False,
    )
    op.execute(
        """
        CREATE INDEX idx_documentos_conhecimento_metadata_gin
        ON documentos_conhecimento
        USING gin (metadata)
        """
    )
    op.execute(
        """
        CREATE INDEX idx_documentos_conhecimento_embedding_cosine
        ON documentos_conhecimento
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documentos_conhecimento_embedding_cosine")
    op.execute("DROP INDEX IF EXISTS idx_documentos_conhecimento_metadata_gin")
    op.drop_index("idx_documentos_conhecimento_hash", table_name="documentos_conhecimento")
    op.drop_index("idx_documentos_conhecimento_titulo", table_name="documentos_conhecimento")
    op.drop_index("idx_documentos_conhecimento_tipo_ativo", table_name="documentos_conhecimento")
    op.drop_index("idx_documentos_conhecimento_id_fonte", table_name="documentos_conhecimento")
    op.drop_index(
        "idx_documentos_conhecimento_id_documento_origem",
        table_name="documentos_conhecimento",
    )
    op.drop_table("documentos_conhecimento")
    op.execute("DROP EXTENSION IF EXISTS vector")
