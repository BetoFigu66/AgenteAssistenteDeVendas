"""adiciona triagem em reports

Acrescenta campos de triagem (categoria, severidade, status, resolvido_por,
resolvido_em) à tabela reports_problema. Sincroniza o campo legado
`resolvido` com o novo `status`.

Revision ID: a7f3e8c1d2b4
Revises: db98912c2a80
Create Date: 2026-04-21 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7f3e8c1d2b4'
down_revision: Union[str, None] = 'db98912c2a80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Definições de enums (compartilhadas entre upgrade e downgrade)
CATEGORIA_VALUES = ('classificacao', 'fluxo', 'template', 'dados', 'llm', 'outro')
SEVERIDADE_VALUES = ('baixa', 'media', 'alta', 'critica')
STATUS_VALUES = ('aberto', 'em_analise', 'aguardando_fix', 'resolvido', 'descartado')


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Criar os TYPEs ENUM no Postgres explicitamente.
    postgresql.ENUM(*CATEGORIA_VALUES, name='categoriareport').create(bind, checkfirst=True)
    postgresql.ENUM(*SEVERIDADE_VALUES, name='severidadereport').create(bind, checkfirst=True)
    postgresql.ENUM(*STATUS_VALUES, name='statusreport').create(bind, checkfirst=True)

    # Referências de tipo com create_type=False para reutilizar os tipos já
    # criados acima sem tentar recriá-los via add_column.
    categoria_enum = postgresql.ENUM(
        *CATEGORIA_VALUES, name='categoriareport', create_type=False
    )
    severidade_enum = postgresql.ENUM(
        *SEVERIDADE_VALUES, name='severidadereport', create_type=False
    )
    status_enum = postgresql.ENUM(
        *STATUS_VALUES, name='statusreport', create_type=False
    )

    # 2) Adicionar colunas em reports_problema
    op.add_column(
        'reports_problema',
        sa.Column(
            'categoria',
            categoria_enum,
            nullable=False,
            server_default='outro',
        ),
    )
    op.add_column(
        'reports_problema',
        sa.Column(
            'severidade',
            severidade_enum,
            nullable=False,
            server_default='media',
        ),
    )
    op.add_column(
        'reports_problema',
        sa.Column(
            'status',
            status_enum,
            nullable=False,
            server_default='aberto',
        ),
    )
    op.add_column(
        'reports_problema',
        sa.Column('resolvido_por', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'reports_problema',
        sa.Column('resolvido_em', sa.DateTime(), nullable=True),
    )

    # 3) Índices de triagem
    op.create_index(
        op.f('ix_reports_problema_status'),
        'reports_problema',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_reports_problema_categoria',
        'reports_problema',
        ['categoria'],
        unique=False,
    )

    # 4) Sincronizar reports legados que tinham resolvido=TRUE
    op.execute(
        "UPDATE reports_problema "
        "SET status = 'resolvido' "
        "WHERE resolvido = TRUE AND status = 'aberto'"
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index('ix_reports_problema_categoria', table_name='reports_problema')
    op.drop_index(op.f('ix_reports_problema_status'), table_name='reports_problema')

    op.drop_column('reports_problema', 'resolvido_em')
    op.drop_column('reports_problema', 'resolvido_por')
    op.drop_column('reports_problema', 'status')
    op.drop_column('reports_problema', 'severidade')
    op.drop_column('reports_problema', 'categoria')

    postgresql.ENUM(name='statusreport').drop(bind, checkfirst=True)
    postgresql.ENUM(name='severidadereport').drop(bind, checkfirst=True)
    postgresql.ENUM(name='categoriareport').drop(bind, checkfirst=True)
