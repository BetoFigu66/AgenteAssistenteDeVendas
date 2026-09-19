"""adiciona reply-to e rastreio de envio em mensagens

Suporte ao REQ-008 (Fase 10):

- `resposta_a_mensagem_id` / `resposta_a_message_sid`: qual mensagem esta responde.
  No WhatsApp vem do `OriginalRepliedMessageSid`; na interface web, do balão escolhido.
- `timestamp_envio` / `erro_envio`: entrega efetiva ao cliente pelo canal de saída.

Revision ID: 2026091601
Revises: 2026072301
Create Date: 2026-09-16 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026091601"
down_revision: Union[str, None] = "2026072301"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mensagens", sa.Column("resposta_a_mensagem_id", sa.Integer(), nullable=True))
    op.add_column("mensagens", sa.Column("resposta_a_message_sid", sa.String(length=50), nullable=True))
    op.add_column("mensagens", sa.Column("timestamp_envio", sa.DateTime(timezone=True), nullable=True))
    op.add_column("mensagens", sa.Column("erro_envio", sa.Text(), nullable=True))

    op.create_index(
        "ix_mensagens_resposta_a_mensagem_id",
        "mensagens",
        ["resposta_a_mensagem_id"],
    )
    op.create_foreign_key(
        "fk_mensagens_resposta_a_mensagem_id",
        "mensagens",
        "mensagens",
        ["resposta_a_mensagem_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_mensagens_resposta_a_mensagem_id", "mensagens", type_="foreignkey")
    op.drop_index("ix_mensagens_resposta_a_mensagem_id", table_name="mensagens")
    op.drop_column("mensagens", "erro_envio")
    op.drop_column("mensagens", "timestamp_envio")
    op.drop_column("mensagens", "resposta_a_message_sid")
    op.drop_column("mensagens", "resposta_a_mensagem_id")
