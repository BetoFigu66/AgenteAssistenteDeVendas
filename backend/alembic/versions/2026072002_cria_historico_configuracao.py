"""cria_historico_configuracao

Revision ID: 2026072002
Revises: 2026072001
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026072002"
down_revision: Union[str, None] = "2026072001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-014 (Fase 7): log append-only de alterações de parâmetros de configuração —
    # mesmo padrão simplificado de `historico_modo_execucao` (REQ-011), não a
    # `eventos_atendimento` da Fase 6 (que exige atendimento_id, não aplicável aqui).
    op.create_table(
        "historico_configuracao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_novo", sa.Text(), nullable=True),
        sa.Column("ator", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_historico_configuracao_nome"), "historico_configuracao", ["nome"])
    op.create_index(op.f("ix_historico_configuracao_timestamp"), "historico_configuracao", ["timestamp"])


def downgrade() -> None:
    op.drop_index(op.f("ix_historico_configuracao_timestamp"), table_name="historico_configuracao")
    op.drop_index(op.f("ix_historico_configuracao_nome"), table_name="historico_configuracao")
    op.drop_table("historico_configuracao")
