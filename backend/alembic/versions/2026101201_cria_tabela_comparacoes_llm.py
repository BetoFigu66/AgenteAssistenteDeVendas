"""cria tabela comparacoes_llm (o que o sistema faria sem o LLM e o que fez com ele)

Uma linha por ponto do processamento de uma mensagem que usou ou usaria o LLM
(classificação, resposta da base de conhecimento, personalização de template), com o
resultado sem LLM, o do LLM e a situação (ok, erro, vazio, indisponível). Aponta para a
mensagem do cliente e para a mensagem de resposta que levou o texto.

Revision ID: 2026101201
Revises: 2026101101
Create Date: 2026-10-12 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026101201"
down_revision: Union[str, None] = "2026101101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comparacoes_llm",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mensagem_id", sa.Integer(), sa.ForeignKey("mensagens.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "resposta_mensagem_id", sa.Integer(), sa.ForeignKey("mensagens.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "processamento_id",
            sa.Integer(),
            sa.ForeignKey("processamentos_mensagem.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("etapa", sa.String(20), nullable=False),
        sa.Column("situacao", sa.String(20), nullable=False),
        sa.Column("sem_llm", sa.Text(), nullable=False),
        sa.Column("com_llm", sa.Text(), nullable=True),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("provedor", sa.String(30), nullable=True),
        sa.Column("modelo", sa.String(100), nullable=True),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comparacoes_llm_mensagem_id", "comparacoes_llm", ["mensagem_id"])
    op.create_index("ix_comparacoes_llm_situacao", "comparacoes_llm", ["situacao"])
    op.create_index("ix_comparacoes_llm_created_at", "comparacoes_llm", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_comparacoes_llm_created_at", table_name="comparacoes_llm")
    op.drop_index("ix_comparacoes_llm_situacao", table_name="comparacoes_llm")
    op.drop_index("ix_comparacoes_llm_mensagem_id", table_name="comparacoes_llm")
    op.drop_table("comparacoes_llm")
