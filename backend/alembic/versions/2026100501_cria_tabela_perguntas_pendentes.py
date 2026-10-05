"""cria tabela perguntas_pendentes (a pilha de perguntas pendentes)

Registro do que o sistema perguntou ao cliente e ainda espera resposta: qual pergunta,
em qual mensagem de saída, lida por qual tratador, com contadores de tentativa e de
reapresentação. Substitui as chaves ad hoc de `atendimento_infos` que cada fluxo usava
para lembrar o que tinha perguntado (`pergunta_prioritaria_chave` é a primeira a sair).

Vale para perguntas feitas a partir desta migração: atendimentos em curso seguem sem
pilha e o motor volta a perguntar o próximo campo pendente, como antes.

Revision ID: 2026100501
Revises: 2026092801
Create Date: 2026-10-05 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026100501"
down_revision: Union[str, None] = "2026092801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "perguntas_pendentes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(length=60), nullable=False),
        sa.Column("tratador", sa.String(length=40), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("leva_criacao", sa.Integer(), nullable=False),
        sa.Column("leva_ultima", sa.Integer(), nullable=False),
        sa.Column("mensagens_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("posicao_serial", sa.Integer(), nullable=True),
        sa.Column("tentativas_captura", sa.Integer(), nullable=False),
        sa.Column("reapresentacoes", sa.Integer(), nullable=False),
        sa.Column("dados", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("valor_capturado", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("encerrado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_perguntas_pendentes_atendimento_id"), "perguntas_pendentes", ["atendimento_id"], unique=False
    )
    op.create_index(
        "idx_perguntas_pendentes_atendimento_status",
        "perguntas_pendentes",
        ["atendimento_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    # Tabela nova e nada aponta para ela. Descer perde o registro das perguntas feitas,
    # e o motor volta a recalcular o próximo campo a cada turno.
    op.drop_index("idx_perguntas_pendentes_atendimento_status", table_name="perguntas_pendentes")
    op.drop_index(op.f("ix_perguntas_pendentes_atendimento_id"), table_name="perguntas_pendentes")
    op.drop_table("perguntas_pendentes")
