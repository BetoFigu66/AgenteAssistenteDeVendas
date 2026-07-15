"""adiciona intencoes (lista) em processamentos_mensagem — motor Intenção×Fase→Ações

O classificador passou a coletar TODAS as intenções que baterem numa mensagem (não só a
de maior prioridade — era essa a raiz de um bug real: "Bom dia, quero orçamento" perdia a
intenção de orçamento porque a saudação vinha primeiro na lista de regras). A coluna
`intencao` (string única) é mantida como a "intenção principal" para auditoria/exibição
simples, sem exigir mudança de frontend; `intencoes` guarda a lista completa.

Revision ID: 2026071601
Revises: 2026071401
Create Date: 2026-07-15 09:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026071601"
down_revision: Union[str, None] = "2026071401"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "processamentos_mensagem",
        sa.Column("intencoes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("processamentos_mensagem", "intencoes")
