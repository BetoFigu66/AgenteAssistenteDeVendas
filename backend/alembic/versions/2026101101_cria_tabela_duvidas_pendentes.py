"""cria tabela duvidas_pendentes (dúvidas do cliente sem resposta automática)

Quando a mensagem do cliente traz uma dúvida mas cai numa ação exclusiva do motor
(pedido de atendente, reclamação, projeto complexo, confirmação do resumo, encerramento),
a dúvida não é respondida pelo agente. Esta tabela a registra para o operador, que a
responde e a marca como resolvida.

Também encerra as perguntas de data de nascimento que tenham ficado abertas na pilha: a
data deixou de ser pedida na mesma mudança, e sem definição a retomada após dúvida (D1)
ainda poderia reapresentá-las.

Revision ID: 2026101101
Revises: 2026100501
Create Date: 2026-10-11 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026101101"
down_revision: Union[str, None] = "2026100501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "duvidas_pendentes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("mensagem_id", sa.Integer(), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("intencao", sa.String(length=40), nullable=False),
        sa.Column("acao_exclusiva", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolvido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolvido_por_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"]),
        sa.ForeignKeyConstraint(["mensagem_id"], ["mensagens.id"]),
        sa.ForeignKeyConstraint(["resolvido_por_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_duvidas_pendentes_atendimento_id"), "duvidas_pendentes", ["atendimento_id"], unique=False
    )
    op.execute(
        "UPDATE perguntas_pendentes SET status = 'descartada', posicao_serial = NULL, encerrado_em = now() "
        "WHERE chave = 'data_nascimento' AND status = 'aberta'"
    )


def downgrade() -> None:
    # Tabela nova e nada aponta para ela. Descer perde só o registro das dúvidas. As
    # perguntas de data encerradas não são reabertas (a data não é mais pedida).
    op.drop_index(op.f("ix_duvidas_pendentes_atendimento_id"), table_name="duvidas_pendentes")
    op.drop_table("duvidas_pendentes")
