"""motivos concluido_conversao/desistencia + auditoria mínima de transição (REQ-016 Fase 1)

Revision ID: 2026071603
Revises: 2026071602
Create Date: 2026-07-16 15:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026071603"
down_revision: Union[str, None] = "2026071602"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MOTIVOS_LEGADOS = (
    "concluido_pelo_cliente",
    "abandono",
    "manual_vendedor",
    "inatividade",
    "ganha_legado",
    "perdida_legado",
)
_MOTIVOS_NOVOS = ("concluido_conversao", "desistencia")


def _recriar_constraint(motivos: Sequence[str]) -> None:
    op.drop_constraint("ck_atendimentos_motivo_encerramento", "atendimentos", type_="check")
    motivos_sql = ", ".join(f"'{m}'" for m in motivos)
    op.create_check_constraint(
        "ck_atendimentos_motivo_encerramento",
        "atendimentos",
        f"""(
            (status = 'ativo' AND motivo_encerramento IS NULL)
            OR (
                status = 'encerrado'
                AND motivo_encerramento IS NOT NULL
                AND motivo_encerramento IN ({motivos_sql})
            )
        )""",
    )


def upgrade() -> None:
    _recriar_constraint((*_MOTIVOS_LEGADOS, *_MOTIVOS_NOVOS))

    op.add_column("atendimentos", sa.Column("encerrado_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("atendimentos", sa.Column("encerrado_por", sa.String(length=50), nullable=True))
    op.add_column("atendimentos", sa.Column("reaberto_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("atendimentos", sa.Column("reaberto_por", sa.String(length=50), nullable=True))
    op.add_column("atendimentos", sa.Column("reabertura_justificativa", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("atendimentos", "reabertura_justificativa")
    op.drop_column("atendimentos", "reaberto_por")
    op.drop_column("atendimentos", "reaberto_em")
    op.drop_column("atendimentos", "encerrado_por")
    op.drop_column("atendimentos", "encerrado_em")

    _recriar_constraint(_MOTIVOS_LEGADOS)
