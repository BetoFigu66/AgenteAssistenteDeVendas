"""adiciona modo de operacao em negociacoes

Cria ENUM `modooperacao` (agente, humano) e adiciona a coluna
`modo_operacao` em `negociacoes` com default `agente`. Usado para definir
se o sistema deve gerar respostas automaticamente (AGENTE) ou apenas
registrar mensagens recebidas (HUMANO), deixando a resposta para o operador.

Revision ID: e8a2b6c4f9d1
Revises: c5d9f1a8e3b7
Create Date: 2026-04-23 06:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e8a2b6c4f9d1'
down_revision: Union[str, None] = 'c5d9f1a8e3b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MODO_OPERACAO_VALUES = ('agente', 'humano')


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Cria o TYPE ENUM no Postgres
    postgresql.ENUM(*MODO_OPERACAO_VALUES, name='modooperacao').create(
        bind, checkfirst=True
    )

    modo_enum = postgresql.ENUM(
        *MODO_OPERACAO_VALUES, name='modooperacao', create_type=False
    )

    # 2) Adiciona a coluna com default 'agente' (respeita negociações existentes)
    op.add_column(
        'negociacoes',
        sa.Column(
            'modo_operacao',
            modo_enum,
            nullable=False,
            server_default='agente',
        ),
    )

    # 3) Índice para consulta rápida por modo
    op.create_index(
        'ix_negociacoes_modo_operacao',
        'negociacoes',
        ['modo_operacao'],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index('ix_negociacoes_modo_operacao', table_name='negociacoes')
    op.drop_column('negociacoes', 'modo_operacao')

    postgresql.ENUM(name='modooperacao').drop(bind, checkfirst=True)
