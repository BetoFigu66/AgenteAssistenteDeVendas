"""adiciona processamentos e reports

Revision ID: db98912c2a80
Revises: 80c013aa867b
Create Date: 2026-04-21 08:35:37.907995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'db98912c2a80'
down_revision: Union[str, None] = '80c013aa867b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria infraestrutura de auditoria de processamentos e reports de problema."""

    # Enum de origem de classificação (tipo nativo PG).
    # Criamos o TYPE explicitamente e, ao usá-lo nas colunas abaixo, marcamos
    # create_type=False para o create_table NÃO tentar recriá-lo.
    origem_classificacao = postgresql.ENUM(
        'regra', 'llm', 'hibrido',
        name='origemclassificacao',
        create_type=False,
    )
    postgresql.ENUM(
        'regra', 'llm', 'hibrido',
        name='origemclassificacao',
    ).create(op.get_bind(), checkfirst=True)

    # ---------------------------------------------------------------
    # 1) Tabela processamentos_mensagem
    # ---------------------------------------------------------------
    op.create_table(
        'processamentos_mensagem',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),

        # Classificação
        sa.Column('intencao', sa.String(length=50), nullable=True),
        sa.Column('confianca', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('origem_classificacao', origem_classificacao, nullable=True),
        sa.Column('entidades', sa.JSON(), nullable=True),

        # Identificação do remetente
        sa.Column('status_identificacao', sa.String(length=30), nullable=True),
        sa.Column('contato_id_identificado', sa.Integer(), nullable=True),
        sa.Column('empresa_id_identificada', sa.Integer(), nullable=True),
        sa.Column('negociacao_id_ativa', sa.Integer(), nullable=True),

        # Decisão de resposta
        sa.Column('template_usado', sa.String(length=100), nullable=True),
        sa.Column('personalizado_via_llm', sa.Boolean(), nullable=False, server_default=sa.false()),

        # Metadados da LLM
        sa.Column('llm_provider', sa.String(length=30), nullable=True),
        sa.Column('llm_modelo', sa.String(length=100), nullable=True),
        sa.Column('llm_tokens_input', sa.Integer(), nullable=True),
        sa.Column('llm_tokens_output', sa.Integer(), nullable=True),
        sa.Column('llm_latencia_ms', sa.Integer(), nullable=True),
        sa.Column('llm_raw_resposta', sa.JSON(), nullable=True),

        # Controle
        sa.Column('duracao_ms', sa.Integer(), nullable=True),
        sa.Column('erro', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),

        sa.ForeignKeyConstraint(['contato_id_identificado'], ['contatos.id']),
        sa.ForeignKeyConstraint(['empresa_id_identificada'], ['empresas.id']),
        sa.ForeignKeyConstraint(['negociacao_id_ativa'], ['negociacoes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_processamentos_mensagem_intencao'),
        'processamentos_mensagem',
        ['intencao'],
        unique=False,
    )

    # ---------------------------------------------------------------
    # 2) Tabela reports_problema (schema inicial, sem triagem)
    # ---------------------------------------------------------------
    op.create_table(
        'reports_problema',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('processamento_id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('autor', sa.String(length=100), nullable=True),
        sa.Column('resolvido', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('resolucao', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.ForeignKeyConstraint(
            ['processamento_id'],
            ['processamentos_mensagem.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_reports_problema_processamento_id'),
        'reports_problema',
        ['processamento_id'],
        unique=False,
    )

    # ---------------------------------------------------------------
    # 3) FK mensagens.processamento_id
    # ---------------------------------------------------------------
    op.add_column('mensagens', sa.Column('processamento_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_mensagens_processamento_id'),
        'mensagens',
        ['processamento_id'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_mensagens_processamento_id',
        'mensagens',
        'processamentos_mensagem',
        ['processamento_id'],
        ['id'],
    )


def downgrade() -> None:
    """Reverte em ordem inversa de dependência."""
    op.drop_constraint('fk_mensagens_processamento_id', 'mensagens', type_='foreignkey')
    op.drop_index(op.f('ix_mensagens_processamento_id'), table_name='mensagens')
    op.drop_column('mensagens', 'processamento_id')

    op.drop_index(op.f('ix_reports_problema_processamento_id'), table_name='reports_problema')
    op.drop_table('reports_problema')

    op.drop_index(op.f('ix_processamentos_mensagem_intencao'), table_name='processamentos_mensagem')
    op.drop_table('processamentos_mensagem')

    postgresql.ENUM(name='origemclassificacao').drop(op.get_bind(), checkfirst=True)
