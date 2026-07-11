"""renomeia itens_negociacao para itens_atendimento (debito tecnico A0)

Conclui a renomeacao Negociacao -> Atendimento (REQ-016 v2.0 / migration
2026061501) para a ultima tabela que ainda usava o nome antigo. Renomeia
tabela, sequence, indices e constraints (PK/FK).

A FK de atendimento_id foi encontrada na base local com nome divergente
("itens_atendimentao_atendimentao_id_fkey" - com typo "atendimentao"),
sinal de um ALTER manual feito fora do Alembic em algum momento. Por isso
as constraints sao localizadas dinamicamente pela coluna que envolvem, em
vez de assumir um nome fixo — a migration funciona tanto nessa base com
drift quanto em uma base nova, criada do zero a partir do historico de
migrations.

Revision ID: 2026071001
Revises: 2026061506
Create Date: 2026-07-10 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "2026071001"
down_revision: Union[str, None] = "2026061506"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_index(old: str, new: str) -> None:
    op.execute(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"')


def _rename_constraint_by_column(table: str, column: str, contype: str, new_name: str) -> None:
    """Renomeia a constraint (pk='p'/fk='f') que envolve `column` em `table`, seja qual for o nome atual."""
    conn = op.get_bind()
    row = conn.execute(
        text(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.conrelid = CAST(:table AS regclass)
              AND c.contype = :contype
              AND a.attname = :column
            """
        ),
        {"table": table, "contype": contype, "column": column},
    ).fetchone()
    if row and row[0] != new_name:
        conn.execute(text(f'ALTER TABLE {table} RENAME CONSTRAINT "{row[0]}" TO "{new_name}"'))


def _dropar_fantasma_vazia(table: str) -> None:
    """Remove uma tabela fantasma (0 linhas) criada por `Base.metadata.create_all()` fora do Alembic.

    Este projeto roda `Base.metadata.create_all()` no startup do backend (`database.py`), que pode
    criar uma tabela nova casando com o `__tablename__` atual do model antes da migration de rename
    ser aplicada (ex.: dev editou o model e o `--reload` do uvicorn subiu antes do `alembic upgrade`).
    Só remove se a tabela existir e estiver vazia — nunca apaga dados.
    """
    conn = op.get_bind()
    existe = conn.execute(
        text("SELECT to_regclass(:table) IS NOT NULL"), {"table": table}
    ).scalar()
    if not existe:
        return
    total = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
    if total:
        raise RuntimeError(
            f"Tabela fantasma '{table}' tem {total} linha(s) — não removendo automaticamente. "
            "Investigar manualmente antes de rodar esta migration."
        )
    op.execute(f'DROP TABLE "{table}"')


def upgrade() -> None:
    # 0. Remove tabela fantasma "itens_atendimento" se `create_all()` já tiver criado uma vazia
    #    (ver `_dropar_fantasma_vazia`) antes de tentar o rename abaixo.
    _dropar_fantasma_vazia("itens_atendimento")

    # 1. Tabela
    op.rename_table("itens_negociacao", "itens_atendimento")

    # 2. Sequence (Postgres nao renomeia automaticamente ao renomear a tabela)
    op.execute('ALTER SEQUENCE IF EXISTS "itens_negociacao_id_seq" RENAME TO "itens_atendimento_id_seq"')

    # 3. PK (renomear a constraint renomeia junto o indice subjacente)
    _rename_constraint_by_column("itens_atendimento", "id", "p", "itens_atendimento_pkey")

    # 4. Indices simples (nao ligados a constraint)
    _rename_index("ix_itens_negociacao_atendimento_id", "ix_itens_atendimento_atendimento_id")
    _rename_index("ix_itens_negociacao_produto_id", "ix_itens_atendimento_produto_id")
    _rename_index("ix_itens_negociacao_tipo_produto_id", "ix_itens_atendimento_tipo_produto_id")

    # 5. FKs - busca dinamica por coluna (corrige o drift "atendimentao" encontrado no ambiente local)
    _rename_constraint_by_column(
        "itens_atendimento", "atendimento_id", "f", "itens_atendimento_atendimento_id_fkey"
    )
    _rename_constraint_by_column("itens_atendimento", "produto_id", "f", "itens_atendimento_produto_id_fkey")
    _rename_constraint_by_column(
        "itens_atendimento", "tipo_produto_id", "f", "itens_atendimento_tipo_produto_id_fkey"
    )


def downgrade() -> None:
    _rename_constraint_by_column(
        "itens_atendimento", "tipo_produto_id", "f", "itens_negociacao_tipo_produto_id_fkey"
    )
    _rename_constraint_by_column("itens_atendimento", "produto_id", "f", "itens_negociacao_produto_id_fkey")
    _rename_constraint_by_column(
        "itens_atendimento", "atendimento_id", "f", "itens_negociacao_atendimento_id_fkey"
    )

    _rename_index("ix_itens_atendimento_tipo_produto_id", "ix_itens_negociacao_tipo_produto_id")
    _rename_index("ix_itens_atendimento_produto_id", "ix_itens_negociacao_produto_id")
    _rename_index("ix_itens_atendimento_atendimento_id", "ix_itens_negociacao_atendimento_id")

    _rename_constraint_by_column("itens_atendimento", "id", "p", "itens_negociacao_pkey")

    op.execute('ALTER SEQUENCE IF EXISTS "itens_atendimento_id_seq" RENAME TO "itens_negociacao_id_seq"')

    op.rename_table("itens_atendimento", "itens_negociacao")
