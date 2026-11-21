"""cria tabela cumprimentos (expressões de início de conversa e a resposta a cada uma)

Antes, o que contava como cumprimento era uma regex fixa no classificador e a resposta era
sempre "Olá!". A tabela passa a ser a fonte das duas coisas e é editada no painel
(`services/cumprimentos.py`). O seed traz as expressões da regex antiga, cada uma com a
resposta no mesmo tom; "tudo bem" e afins entram sem resposta (contam como cumprimento,
mas não escolhem a primeira frase).

Revision ID: 2026110101
Revises: 2026101201
Create Date: 2026-11-01 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026110101"
down_revision: Union[str, None] = "2026101201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (expressão como digitada, normalizada, resposta)
_SEED = [
    ("oi", "oi", "Oi!"),
    ("olá", "ola", "Olá!"),
    ("bom dia", "bom dia", "Bom dia!"),
    ("boa tarde", "boa tarde", "Boa tarde!"),
    ("boa noite", "boa noite", "Boa noite!"),
    ("e aí", "e ai", "E aí!"),
    ("eai", "eai", "E aí!"),
    ("e aí bro", "e ai bro", "E aí?"),
    ("salve", "salve", "Salve!"),
    ("hey", "hey", "Olá!"),
    ("hi", "hi", "Olá!"),
    ("hello", "hello", "Olá!"),
    ("tudo bem", "tudo bem", ""),
    ("tudo bom", "tudo bom", ""),
    ("tudo certo", "tudo certo", ""),
    ("tudo joia", "tudo joia", ""),
    ("como vai", "como vai", ""),
]


def upgrade() -> None:
    tabela = op.create_table(
        "cumprimentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expressao", sa.String(length=100), nullable=False),
        sa.Column("expressao_normalizada", sa.String(length=100), nullable=False),
        sa.Column("resposta", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("atualizado_por", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expressao_normalizada"),
    )
    op.bulk_insert(
        tabela,
        [
            {"expressao": e, "expressao_normalizada": n, "resposta": r, "ativo": True, "atualizado_por": "migração"}
            for e, n, r in _SEED
        ],
    )


def downgrade() -> None:
    # Descer volta a não ter de onde ler: `services/cumprimentos.py` cai nos padrões do
    # código, que são este mesmo seed. Perde só o que foi cadastrado no painel.
    op.drop_table("cumprimentos")
