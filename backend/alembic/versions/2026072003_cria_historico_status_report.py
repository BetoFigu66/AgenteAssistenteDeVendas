"""cria_historico_status_report

Revision ID: 2026072003
Revises: 2026072002
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026072003"
down_revision: Union[str, None] = "2026072002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-012 (Fase 8): log append-only das transições de status de um report —
    # mesmo padrão simplificado de `historico_modo_execucao`/`historico_configuracao`,
    # não a `eventos_atendimento` da Fase 6 (que exige atendimento_id, nem sempre
    # resolvível a partir de um report).
    op.create_table(
        "historico_status_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("status_anterior", sa.String(length=30), nullable=True),
        sa.Column("status_novo", sa.String(length=30), nullable=False),
        sa.Column("ator", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports_problema.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_historico_status_report_report_id"), "historico_status_report", ["report_id"]
    )
    op.create_index(
        op.f("ix_historico_status_report_timestamp"), "historico_status_report", ["timestamp"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_historico_status_report_timestamp"), table_name="historico_status_report")
    op.drop_index(op.f("ix_historico_status_report_report_id"), table_name="historico_status_report")
    op.drop_table("historico_status_report")
