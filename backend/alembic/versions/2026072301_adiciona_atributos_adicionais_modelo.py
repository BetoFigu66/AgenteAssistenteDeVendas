"""adiciona atributos adicionais modelo

Revision ID: 2026072301
Revises: 2026072216
Create Date: 2026-07-23 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026072301"
down_revision: Union[str, None] = "2026072216"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "atributos_adicionais_modelo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("valor", sa.String(length=300), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()"), onupdate=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["modelo_id"], ["modelos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("modelo_id", "chave", "valor", name="uq_atributos_modelo_chave_valor"),
    )
    op.create_index("ix_atributos_modelo_modelo_id", "atributos_adicionais_modelo", ["modelo_id"])
    op.create_index("ix_atributos_modelo_chave", "atributos_adicionais_modelo", ["chave"])
    op.create_index("ix_atributos_modelo_valor", "atributos_adicionais_modelo", ["valor"])


def downgrade() -> None:
    op.drop_index("ix_atributos_modelo_valor", table_name="atributos_adicionais_modelo")
    op.drop_index("ix_atributos_modelo_chave", table_name="atributos_adicionais_modelo")
    op.drop_index("ix_atributos_modelo_modelo_id", table_name="atributos_adicionais_modelo")
    op.drop_table("atributos_adicionais_modelo")
