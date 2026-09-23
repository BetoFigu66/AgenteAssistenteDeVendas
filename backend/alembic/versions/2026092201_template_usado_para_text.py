"""template_usado passa de String(100) para Text

O valor desta coluna é composto em runtime, não escolhido de uma lista fechada: o motor
junta com "+" os templates de todas as ações que dispararam, o gerador compõe códigos, e a
fase Finalizando compõe dúvida + retomada (cada lado podendo já vir composto).

Quatro templates reais estouram 100 caracteres. Quando isso acontece, o INSERT de auditoria
falha e derruba `processar()` inteiro: o cliente recebe a resposta de erro genérica e a
transação do turno volta atrás. É o mesmo mecanismo da divergência B (commit `a94e996`),
que era um rótulo de 34 caracteres numa coluna String(30), agora num campo que não tem teto
natural.

Ampliar em vez de truncar porque um campo de auditoria truncado passa a mentir sobre o que o
sistema fez.

Revision ID: 2026092201
Revises: 2026091901
Create Date: 2026-09-22 17:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026092201"
down_revision: Union[str, None] = "2026091901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "processamentos_mensagem",
        "template_usado",
        existing_type=sa.String(length=100),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Valor mais longo que 100 não cabe de volta. Truncar é a única forma de descer sem
    # falhar, e é aceitável aqui: o downgrade só existe para reverter o schema, e a
    # alternativa seria o downgrade quebrar em qualquer banco que já tenha registrado uma
    # composição longa.
    op.execute(
        "UPDATE processamentos_mensagem SET template_usado = LEFT(template_usado, 100) "
        "WHERE template_usado IS NOT NULL AND LENGTH(template_usado) > 100"
    )
    op.alter_column(
        "processamentos_mensagem",
        "template_usado",
        existing_type=sa.Text(),
        type_=sa.String(length=100),
        existing_nullable=True,
    )
