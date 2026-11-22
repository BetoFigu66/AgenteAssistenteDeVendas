"""report: categorias Dúvida e Sugestão e tabela de respostas

- `categoriareport` ganha `duvida` e `sugestao`: quem reporta pode perguntar ou propor algo,
  não só apontar defeito.
- `respostas_report`: respostas a um report (sobretudo à Dúvida), escritas pelo Claude (goal
  da ponte `backend/scripts/ponte_reports_goals.py`) ou pela equipe, com a origem para a tela
  indicar quem respondeu. Várias por report: o Claude responde e a equipe pode complementar.

`ALTER TYPE ... ADD VALUE` roda dentro da transação da migração (Postgres 12+); os valores
novos só são usados depois do commit, e esta migração não os usa.

Revision ID: 2026112201
Revises: 2026112101
Create Date: 2026-11-22 10:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026112201"
down_revision: Union[str, None] = "2026112101"
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
    "escalonamento_indevido",
)


def upgrade() -> None:
    op.execute("ALTER TYPE categoriareport ADD VALUE IF NOT EXISTS 'duvida'")
    op.execute("ALTER TYPE categoriareport ADD VALUE IF NOT EXISTS 'sugestao'")

    origem = postgresql.ENUM("claude", "equipe", name="origemrespostareport", create_type=False)
    origem.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "respostas_report",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("origem", origem, nullable=False),
        sa.Column("autor", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports_problema.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_respostas_report_report_id"), "respostas_report", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_respostas_report_report_id"), table_name="respostas_report")
    op.drop_table("respostas_report")
    op.execute("DROP TYPE IF EXISTS origemrespostareport")

    # Postgres não remove valor de enum: o tipo é recriado sem eles, e os reports com as
    # categorias novas descem para `outro`.
    op.execute("UPDATE reports_problema SET categoria = 'outro' WHERE categoria IN ('duvida', 'sugestao')")
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
