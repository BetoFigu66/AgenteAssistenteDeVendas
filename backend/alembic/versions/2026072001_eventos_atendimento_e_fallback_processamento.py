"""eventos_atendimento_e_fallback_processamento

Revision ID: 2026072001
Revises: 2026071703
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026072001"
down_revision: Union[str, None] = "2026071703"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-005 (Fase 6): tabela genérica de eventos auditáveis do Atendimento —
    # consolida os padrões simplificados das Fases 1 (encerrar/reabrir) e 5
    # (escalonamento), sem substituir as colunas de "estado atual" já existentes em
    # `atendimentos` (continuam servindo de snapshot rápido). `tipo` é string livre
    # (sem CHECK) para admitir novos valores futuros (ex.: orcamento_* na Fase 14).
    op.create_table(
        "eventos_atendimento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("estado_anterior", sa.String(length=50), nullable=True),
        sa.Column("estado_novo", sa.String(length=50), nullable=True),
        sa.Column("ator", sa.String(length=50), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("mensagem_id", sa.Integer(), nullable=True),
        sa.Column("processamento_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"]),
        sa.ForeignKeyConstraint(["mensagem_id"], ["mensagens.id"]),
        sa.ForeignKeyConstraint(["processamento_id"], ["processamentos_mensagem.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eventos_atendimento_atendimento_id"), "eventos_atendimento", ["atendimento_id"])
    op.create_index(op.f("ix_eventos_atendimento_tipo"), "eventos_atendimento", ["tipo"])
    op.create_index(op.f("ix_eventos_atendimento_timestamp"), "eventos_atendimento", ["timestamp"])

    # REQ-003.7/REQ-004.9: campos de auditoria do fallback final do cérebro (QA /
    # escalonamento por baixa confiança / NAO_ENTENDI genérico), hoje só implícitos no
    # fluxo de `_fallback_qa_ou_nao_entendi` e nunca persistidos.
    op.add_column(
        "processamentos_mensagem",
        sa.Column("fallback_req003", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "processamentos_mensagem",
        sa.Column("resultado_fallback", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "processamentos_mensagem",
        sa.Column("justificativa_curta", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("processamentos_mensagem", "justificativa_curta")
    op.drop_column("processamentos_mensagem", "resultado_fallback")
    op.drop_column("processamentos_mensagem", "fallback_req003")

    op.drop_index(op.f("ix_eventos_atendimento_timestamp"), table_name="eventos_atendimento")
    op.drop_index(op.f("ix_eventos_atendimento_tipo"), table_name="eventos_atendimento")
    op.drop_index(op.f("ix_eventos_atendimento_atendimento_id"), table_name="eventos_atendimento")
    op.drop_table("eventos_atendimento")
