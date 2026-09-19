"""generaliza historico de report para qualquer campo

REQ-012.8: edição de categoria e severidade na triagem também precisa registrar
histórico, não só a transição de status.

A tabela `historico_status_report` já era "um registro por alteração", então foi
generalizada em vez de ganhar uma irmã: as colunas de status viram genéricas
(`valor_anterior`/`valor_novo`) e entra `campo` dizendo o que mudou. O rename
preserva as linhas já gravadas, e o `server_default='status'` faz o back-fill
delas — é exatamente o que elas sempre foram. O default é removido em seguida
para que toda linha nova declare o campo explicitamente.

Revision ID: 2026091901
Revises: 2026091601
Create Date: 2026-09-19 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026091901"
down_revision: Union[str, None] = "2026091601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("historico_status_report", "status_anterior", new_column_name="valor_anterior")
    op.alter_column("historico_status_report", "status_novo", new_column_name="valor_novo")
    op.add_column(
        "historico_status_report",
        sa.Column("campo", sa.String(length=30), nullable=False, server_default="status"),
    )
    op.alter_column("historico_status_report", "campo", server_default=None)


def downgrade() -> None:
    # Linhas de categoria/severidade não existiam antes desta migração e não cabem
    # no formato antigo (a tabela só sabia falar de status): são descartadas, e as
    # de status voltam ao nome original com os mesmos valores.
    op.execute("DELETE FROM historico_status_report WHERE campo <> 'status'")
    op.drop_column("historico_status_report", "campo")
    op.alter_column("historico_status_report", "valor_novo", new_column_name="status_novo")
    op.alter_column("historico_status_report", "valor_anterior", new_column_name="status_anterior")
