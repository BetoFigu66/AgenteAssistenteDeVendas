"""rename negociacoes para atendimentos (schema mecanico)

Renomeia tabelas negociacoes/negociacao_infos e colunas FK relacionadas.
NAO altera dominio de status — isso fica em T-A1b.

Revision ID: 2026061501
Revises: 2026060901
Create Date: 2026-06-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '2026061501'
down_revision: Union[str, None] = '2026060901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_index(old: str, new: str) -> None:
    op.execute(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"')


def _to_atendimento_name(name: str) -> str:
    return name.replace("negociacoes", "atendimentos").replace("negociacao", "atendimento")


def _to_negociacao_name(name: str) -> str:
    return name.replace("atendimentos", "negociacoes").replace("atendimento", "negociacao")


def _rename_fk_constraints(*, to_atendimento: bool) -> None:
    conn = op.get_bind()
    transform = _to_atendimento_name if to_atendimento else _to_negociacao_name
    needle = "negociac" if to_atendimento else "atendiment"

    incoming = conn.execute(
        text(
            """
            SELECT c.conrelid::regclass::text AS tbl, c.conname AS cname
            FROM pg_constraint c
            JOIN pg_class ref ON c.confrelid = ref.oid
            WHERE ref.relname = 'atendimentos'
              AND c.contype = 'f'
              AND c.conname LIKE :pattern
            """
        ),
        {"pattern": f"%{needle}%"},
    )
    for row in incoming:
        new_name = transform(row.cname)
        if new_name != row.cname:
            conn.execute(
                text(f'ALTER TABLE {row.tbl} RENAME CONSTRAINT "{row.cname}" TO "{new_name}"')
            )

    outgoing = conn.execute(
        text(
            """
            SELECT c.conname AS cname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'atendimentos'
              AND c.contype = 'f'
              AND c.conname LIKE :pattern
            """
        ),
        {"pattern": f"%{needle}%"},
    )
    for row in outgoing:
        new_name = transform(row.cname)
        if new_name != row.cname:
            conn.execute(
                text(f'ALTER TABLE atendimentos RENAME CONSTRAINT "{row.cname}" TO "{new_name}"')
            )


def upgrade() -> None:
    # --- 1. Tabelas principais ---
    op.rename_table('negociacoes', 'atendimentos')
    op.rename_table('negociacao_infos', 'atendimento_infos')

    # --- 2. Colunas FK (negociacao_id -> atendimento_id) ---
    op.alter_column('mensagens', 'negociacao_id', new_column_name='atendimento_id')
    op.alter_column('orcamentos', 'negociacao_id', new_column_name='atendimento_id')
    op.alter_column('atendimento_infos', 'negociacao_id', new_column_name='atendimento_id')
    op.alter_column('itens_negociacao', 'negociacao_id', new_column_name='atendimento_id')
    op.alter_column(
        'processamentos_mensagem',
        'negociacao_id_ativa',
        new_column_name='atendimento_id_ativa',
    )

    # --- 3. Indices em atendimentos ---
    _rename_index('ix_negociacoes_contato_id', 'ix_atendimentos_contato_id')
    _rename_index('ix_negociacoes_empresa_id', 'ix_atendimentos_empresa_id')
    _rename_index('ix_negociacoes_modo_operacao', 'ix_atendimentos_modo_operacao')
    _rename_index('ix_negociacoes_pessoa_id', 'ix_atendimentos_pessoa_id')
    _rename_index('ix_negociacoes_tipo_documento', 'ix_atendimentos_tipo_documento')

    # --- 4. Indices em tabelas filhas ---
    _rename_index('idx_mensagens_negociacao', 'idx_mensagens_atendimento')
    _rename_index('ix_mensagens_negociacao_id', 'ix_mensagens_atendimento_id')
    _rename_index('ix_orcamentos_negociacao_id', 'ix_orcamentos_atendimento_id')
    _rename_index('idx_negociacao_info_chave', 'idx_atendimento_info_chave')
    _rename_index('ix_negociacao_infos_negociacao_id', 'ix_atendimento_infos_atendimento_id')
    _rename_index('ix_itens_negociacao_negociacao_id', 'ix_itens_negociacao_atendimento_id')

    # --- 5. FK constraints nomeadas (incoming + outgoing) ---
    _rename_fk_constraints(to_atendimento=True)


def downgrade() -> None:
    _rename_fk_constraints(to_atendimento=False)

    _rename_index('ix_itens_negociacao_atendimento_id', 'ix_itens_negociacao_negociacao_id')
    _rename_index('ix_atendimento_infos_atendimento_id', 'ix_negociacao_infos_negociacao_id')
    _rename_index('idx_atendimento_info_chave', 'idx_negociacao_info_chave')
    _rename_index('ix_orcamentos_atendimento_id', 'ix_orcamentos_negociacao_id')
    _rename_index('ix_mensagens_atendimento_id', 'ix_mensagens_negociacao_id')
    _rename_index('idx_mensagens_atendimento', 'idx_mensagens_negociacao')

    _rename_index('ix_atendimentos_tipo_documento', 'ix_negociacoes_tipo_documento')
    _rename_index('ix_atendimentos_pessoa_id', 'ix_negociacoes_pessoa_id')
    _rename_index('ix_atendimentos_modo_operacao', 'ix_negociacoes_modo_operacao')
    _rename_index('ix_atendimentos_empresa_id', 'ix_negociacoes_empresa_id')
    _rename_index('ix_atendimentos_contato_id', 'ix_negociacoes_contato_id')

    op.alter_column(
        'processamentos_mensagem',
        'atendimento_id_ativa',
        new_column_name='negociacao_id_ativa',
    )
    op.alter_column('itens_negociacao', 'atendimento_id', new_column_name='negociacao_id')
    op.alter_column('atendimento_infos', 'atendimento_id', new_column_name='negociacao_id')
    op.alter_column('orcamentos', 'atendimento_id', new_column_name='negociacao_id')
    op.alter_column('mensagens', 'atendimento_id', new_column_name='negociacao_id')

    op.rename_table('atendimento_infos', 'negociacao_infos')
    op.rename_table('atendimentos', 'negociacoes')
