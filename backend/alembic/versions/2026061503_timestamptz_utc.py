"""timestamptz UTC em colunas datetime

Converte timestamp without time zone -> timestamptz interpretando valores legados como UTC.

Revision ID: 2026061503
Revises: 2026061502
Create Date: 2026-06-15 20:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "2026061503"
down_revision: Union[str, None] = "2026061502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabela, coluna) — dados legados tratados como UTC
_DATETIME_COLUMNS: list[tuple[str, str]] = [
    ("mensagens", "timestamp"),
    ("mensagens", "timestamp_aprovacao"),
    ("users", "created_at"),
    ("empresas", "ultima_atualizacao_api"),
    ("empresas", "created_at"),
    ("empresas", "updated_at"),
    ("contatos", "created_at"),
    ("pessoas", "ultima_atualizacao_api"),
    ("pessoas", "timestamp_verificacao"),
    ("pessoas", "created_at"),
    ("pessoas", "updated_at"),
    ("atendimentos", "created_at"),
    ("atendimentos", "updated_at"),
    ("orcamentos", "created_at"),
    ("orcamentos", "updated_at"),
    ("tipos_produto", "created_at"),
    ("produtos", "created_at"),
    ("produtos", "updated_at"),
    ("documentos_conhecimento", "created_at"),
    ("documentos_conhecimento", "updated_at"),
    ("pares_qa", "criado_em"),
    ("pares_qa", "atualizado_em"),
    ("itens_negociacao", "created_at"),
    ("itens_negociacao", "updated_at"),
    ("atendimento_infos", "created_at"),
    ("atendimento_infos", "updated_at"),
    ("processamentos_mensagem", "created_at"),
    ("reports_problema", "resolvido_em"),
    ("reports_problema", "created_at"),
    ("reports_problema", "updated_at"),
    ("parametros", "created_at"),
    ("parametros", "updated_at"),
]


def _to_timestamptz(table: str, column: str) -> None:
    op.execute(
        f"""
        ALTER TABLE {table}
        ALTER COLUMN {column} TYPE TIMESTAMPTZ
        USING CASE
            WHEN {column} IS NULL THEN NULL
            ELSE {column} AT TIME ZONE 'UTC'
        END
        """
    )


def _to_timestamp(table: str, column: str) -> None:
    op.execute(
        f"""
        ALTER TABLE {table}
        ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE
        USING CASE
            WHEN {column} IS NULL THEN NULL
            ELSE {column} AT TIME ZONE 'UTC'
        END
        """
    )


def upgrade() -> None:
    for table, column in _DATETIME_COLUMNS:
        _to_timestamptz(table, column)


def downgrade() -> None:
    for table, column in reversed(_DATETIME_COLUMNS):
        _to_timestamp(table, column)
