"""adiciona_pessoas_parametros_e_tipo_doc

Cria tabelas pessoas (PF) e parametros (config dinamica), adiciona
pessoa_id e tipo_documento em negociacoes, e faz seed dos limiares
conservadores para a zona cinza do RAG/QA.

Revision ID: 2026060601
Revises: 2026060402
Create Date: 2026-06-06 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2026060601'
down_revision: Union[str, None] = '2026060402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela pessoas (PF)
    op.create_table(
        'pessoas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cpf', sa.String(length=14), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=True),
        sa.Column('data_nascimento', sa.Date(), nullable=True),
        sa.Column('situacao', sa.String(length=30), nullable=True),
        sa.Column('ultima_atualizacao_api', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cpf'),
    )
    op.create_index(op.f('ix_pessoas_cpf'), 'pessoas', ['cpf'], unique=False)

    # 2. Tabela parametros (config dinamica)
    op.create_table(
        'parametros',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.Text(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome'),
    )
    op.create_index(op.f('ix_parametros_nome'), 'parametros', ['nome'], unique=False)

    # 3. Novos campos em negociacoes
    tipodocumento_enum = sa.Enum('cpf', 'cnpj', 'indefinido', name='tipodocumento')
    tipodocumento_enum.create(op.get_bind())

    op.add_column('negociacoes', sa.Column('pessoa_id', sa.Integer(), nullable=True))
    op.add_column(
        'negociacoes',
        sa.Column('tipo_documento', tipodocumento_enum, nullable=False, server_default='indefinido')
    )
    op.create_foreign_key(
        op.f('fk_negociacoes_pessoa_id_pessoas'), 'negociacoes', 'pessoas', ['pessoa_id'], ['id']
    )
    op.create_index(op.f('ix_negociacoes_pessoa_id'), 'negociacoes', ['pessoa_id'], unique=False)
    op.create_index(op.f('ix_negociacoes_tipo_documento'), 'negociacoes', ['tipo_documento'], unique=False)

    # 5. Auditoria: nível de confiança do classificador
    op.add_column(
        'processamentos_mensagem',
        sa.Column('confianca_nivel', sa.String(length=10), nullable=True)
    )

    # 6. Seed dos limiares conservadores (zona cinza)
    op.execute("""
        INSERT INTO parametros (nome, valor, descricao, created_at, updated_at)
        VALUES
            ('qa_fulltext_responde_min', '0.30', 'ts_rank minimo para responder direto via full-text (zona cinza: < isso = desambigua)', NOW(), NOW()),
            ('qa_fulltext_desambigua_min', '0.12', 'ts_rank minimo para entrar em zona cinza (desambigua); abaixo = descarta', NOW(), NOW()),
            ('qa_embedding_responde_min', '0.80', 'score embedding minimo para responder direto (zona cinza: < isso = desambigua)', NOW(), NOW()),
            ('qa_embedding_desambigua_min', '0.65', 'score embedding minimo para zona cinza (desambigua); abaixo = descarta', NOW(), NOW()),
            ('classificador_conf_alta_min', '0.70', 'limiar de confianca ALTA do classificador (>= responde direto)', NOW(), NOW()),
            ('classificador_conf_baixa_max', '0.40', 'limiar maximo de confianca BAIXA do classificador (< aciona fallback QA)', NOW(), NOW()),
            ('desambiguador_max_opcoes', '3', 'maximo de opcoes a apresentar na pergunta de desambiguacao', NOW(), NOW()),
            ('desambiguador_timeout_min', '5', 'minutos ate expirar um estado de desambiguacao pendente', NOW(), NOW())
        ON CONFLICT (nome) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_column('processamentos_mensagem', 'confianca_nivel')

    op.drop_index(op.f('ix_negociacoes_tipo_documento'), table_name='negociacoes')
    op.drop_index(op.f('ix_negociacoes_pessoa_id'), table_name='negociacoes')
    op.drop_constraint(op.f('fk_negociacoes_pessoa_id_pessoas'), 'negociacoes', type_='foreignkey')
    op.drop_column('negociacoes', 'tipo_documento')
    op.drop_column('negociacoes', 'pessoa_id')

    tipodocumento_enum = sa.Enum('cpf', 'cnpj', 'indefinido', name='tipodocumento')
    tipodocumento_enum.drop(op.get_bind())

    op.drop_index(op.f('ix_parametros_nome'), table_name='parametros')
    op.drop_table('parametros')

    op.drop_index(op.f('ix_pessoas_cpf'), table_name='pessoas')
    op.drop_table('pessoas')
