"""renomeia PKs remanescentes da renomeacao Negociacao -> Atendimento

A migration 2026061501 (rename negociacoes -> atendimentos) renomeou tabelas,
colunas FK e indices, mas nao tocou nas constraints de PRIMARY KEY -- elas
ficaram com o nome antigo ("negociacoes_pkey", "negociacao_infos_pkey").
Achado ao implementar o passo A2 do MVP Continuidade (2026-07-11).

Renomear a constraint de PK no Postgres tambem renomeia o indice subjacente
que a sustenta (mesmo objeto, um nome so) -- nao ha passo separado para isso.

Revision ID: 2026071102
Revises: 2026071101
Create Date: 2026-07-12 09:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "2026071102"
down_revision: Union[str, None] = "2026071101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_constraint(table: str, old: str, new: str) -> None:
    """Renomeia a constraint `old` -> `new` em `table`, só se `old` existir com esse nome."""
    conn = op.get_bind()
    existe = conn.execute(
        text("SELECT 1 FROM pg_constraint WHERE conrelid = CAST(:table AS regclass) AND conname = :old"),
        {"table": table, "old": old},
    ).scalar()
    if existe:
        op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old}" TO "{new}"')


def upgrade() -> None:
    _rename_constraint("atendimentos", "negociacoes_pkey", "atendimentos_pkey")
    _rename_constraint("atendimento_infos", "negociacao_infos_pkey", "atendimento_infos_pkey")


def downgrade() -> None:
    _rename_constraint("atendimento_infos", "atendimento_infos_pkey", "negociacao_infos_pkey")
    _rename_constraint("atendimentos", "atendimentos_pkey", "negociacoes_pkey")
