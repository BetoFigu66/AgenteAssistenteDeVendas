"""seed parametro janela_continuacao_atendimento_horas (REQ-016 T-A8)

Revision ID: 2026061506
Revises: 2026061505
Create Date: 2026-06-17 14:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "2026061506"
down_revision: Union[str, None] = "2026061505"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO parametros (nome, valor, descricao, created_at, updated_at)
        VALUES (
            'janela_continuacao_atendimento_horas',
            '24',
            'Duracao da janela (horas) para continuar atendimento anterior vs criar novo (REQ-016.7 / REQ-014.2C)',
            NOW(),
            NOW()
        )
        ON CONFLICT (nome) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM parametros
        WHERE nome = 'janela_continuacao_atendimento_horas';
        """
    )
