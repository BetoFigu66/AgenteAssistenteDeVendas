"""cria tabela escalonamentos (gatilho, evidências e avaliação humana)

REQ-004.5B: além do motivo (categoria, que já fica em `atendimentos.motivo_escalonamento`
e no `eventos_atendimento` do tipo `escalado`), cada escalonamento passa a registrar os
gatilhos concretos que dispararam e as evidências (valores extraídos, limiares vigentes,
intenção/confiança e origem da classificação).

REQ-004.5C: a mesma linha guarda a avaliação humana (procedente/indevido, comentário,
quem e quando). Uma tabela só porque a avaliação é sempre de um escalonamento e vale a
última: não há histórico de avaliações a guardar.

Vale só para escalonamentos a partir desta migração; os anteriores não ganham linha aqui
(decisão do Beto, 26/09/2026).

Revision ID: 2026092601
Revises: 2026092201
Create Date: 2026-09-26 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026092601"
down_revision: Union[str, None] = "2026092201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escalonamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("evento_id", sa.Integer(), nullable=True),
        sa.Column("mensagem_id", sa.Integer(), nullable=True),
        sa.Column("processamento_id", sa.Integer(), nullable=True),
        sa.Column("motivo", sa.String(length=30), nullable=False),
        sa.Column("gatilhos", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidencias", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ator", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avaliacao", sa.String(length=20), nullable=True),
        sa.Column("avaliacao_comentario", sa.Text(), nullable=True),
        sa.Column("avaliado_por", sa.String(length=100), nullable=True),
        sa.Column("avaliado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"]),
        sa.ForeignKeyConstraint(["evento_id"], ["eventos_atendimento.id"]),
        sa.ForeignKeyConstraint(["mensagem_id"], ["mensagens.id"]),
        sa.ForeignKeyConstraint(["processamento_id"], ["processamentos_mensagem.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_escalonamentos_atendimento_id"), "escalonamentos", ["atendimento_id"], unique=False)
    op.create_index(op.f("ix_escalonamentos_evento_id"), "escalonamentos", ["evento_id"], unique=False)
    op.create_index(op.f("ix_escalonamentos_motivo"), "escalonamentos", ["motivo"], unique=False)
    op.create_index(op.f("ix_escalonamentos_timestamp"), "escalonamentos", ["timestamp"], unique=False)
    op.create_index(op.f("ix_escalonamentos_avaliacao"), "escalonamentos", ["avaliacao"], unique=False)


def downgrade() -> None:
    # A tabela é nova e nada aponta para ela: descer é só removê-la (os escalonamentos
    # continuam com motivo em `atendimentos` e `eventos_atendimento`, como antes).
    op.drop_index(op.f("ix_escalonamentos_avaliacao"), table_name="escalonamentos")
    op.drop_index(op.f("ix_escalonamentos_timestamp"), table_name="escalonamentos")
    op.drop_index(op.f("ix_escalonamentos_motivo"), table_name="escalonamentos")
    op.drop_index(op.f("ix_escalonamentos_evento_id"), table_name="escalonamentos")
    op.drop_index(op.f("ix_escalonamentos_atendimento_id"), table_name="escalonamentos")
    op.drop_table("escalonamentos")
