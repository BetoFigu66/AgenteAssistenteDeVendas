"""report automático para escalonamento avaliado como indevido

REQ-004.5C (decisão do Beto, 27/09/2026): avaliar um escalonamento como "indevido" abre
um `ReportProblema` na fila de triagem.

- `categoriareport` ganha o valor `escalonamento_indevido`. Nenhuma categoria existente
  servia: um escalonamento indevido pode ser culpa da extração, da regra ou do limiar, e a
  camada só se sabe na triagem (que pode recategorizar).
- `escalonamentos.report_id` guarda o report aberto, para não abrir outro se o operador
  marcar "indevido" de novo ou só trocar o comentário. `ON DELETE SET NULL`: apagar o
  report (ex.: limpeza de telefone de teste) não bloqueia nem apaga o escalonamento.

`ALTER TYPE ... ADD VALUE` roda dentro da transação da migração (Postgres 12+ permite);
o valor novo só pode ser usado depois do commit, e esta migração não o usa.

Revision ID: 2026092701
Revises: 2026092601
Create Date: 2026-09-27 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026092701"
down_revision: Union[str, None] = "2026092601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Valores de `categoriareport` antes desta migração, na ordem em que existem no banco.
CATEGORIAS_ANTERIORES = (
    "classificacao",
    "fluxo",
    "template",
    "dados",
    "llm",
    "outro",
    "resposta_inadequada",
)


def upgrade() -> None:
    op.execute("ALTER TYPE categoriareport ADD VALUE IF NOT EXISTS 'escalonamento_indevido'")

    op.add_column("escalonamentos", sa.Column("report_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_escalonamentos_report_id",
        "escalonamentos",
        "reports_problema",
        ["report_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_escalonamentos_report_id"), "escalonamentos", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_escalonamentos_report_id"), table_name="escalonamentos")
    op.drop_constraint("fk_escalonamentos_report_id", "escalonamentos", type_="foreignkey")
    op.drop_column("escalonamentos", "report_id")

    # Postgres não remove valor de enum: o tipo é recriado sem ele. Os reports já abertos
    # com a categoria nova descem para `outro` (perde-se só a categoria; a descrição diz
    # que veio de um escalonamento indevido, e o histórico do report fica como está).
    op.execute("UPDATE reports_problema SET categoria = 'outro' WHERE categoria = 'escalonamento_indevido'")
    op.execute("ALTER TABLE reports_problema ALTER COLUMN categoria DROP DEFAULT")
    op.execute("ALTER TYPE categoriareport RENAME TO categoriareport_antigo")
    valores = ", ".join(f"'{v}'" for v in CATEGORIAS_ANTERIORES)
    op.execute(f"CREATE TYPE categoriareport AS ENUM ({valores})")
    op.execute(
        "ALTER TABLE reports_problema ALTER COLUMN categoria TYPE categoriareport "
        "USING categoria::text::categoriareport"
    )
    op.execute("ALTER TABLE reports_problema ALTER COLUMN categoria SET DEFAULT 'outro'")
    op.execute("DROP TYPE categoriareport_antigo")
