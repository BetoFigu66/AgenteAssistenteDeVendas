"""adiciona_pergunta_tsv_em_pares_qa

Revision ID: 2026060201
Revises: 3699280dbfe7
Create Date: 2026-06-02 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026060201'
down_revision: Union[str, None] = '3699280dbfe7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona coluna TSVECTOR
    op.add_column(
        'pares_qa',
        sa.Column('pergunta_tsv', postgresql.TSVECTOR(), nullable=True)
    )

    # Cria índice GIN para busca full-text eficiente
    op.create_index(
        'idx_pares_qa_pergunta_tsv',
        'pares_qa',
        ['pergunta_tsv'],
        postgresql_using='gin',
    )

    # Popula dados existentes: converte perguntas atuais para tsvector
    op.execute("""
        UPDATE pares_qa
        SET pergunta_tsv = to_tsvector('portuguese', pergunta)
        WHERE pergunta_tsv IS NULL
    """)

    # Cria função de trigger para manter pergunta_tsv sincronizado
    op.execute("""
        CREATE OR REPLACE FUNCTION atualiza_pergunta_tsv()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.pergunta_tsv := to_tsvector('portuguese', NEW.pergunta);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Cria o trigger na tabela pares_qa
    op.execute("""
        CREATE TRIGGER trg_atualiza_pergunta_tsv
        BEFORE INSERT OR UPDATE OF pergunta ON pares_qa
        FOR EACH ROW
        EXECUTE FUNCTION atualiza_pergunta_tsv();
    """)


def downgrade() -> None:
    # Remove trigger e função
    op.execute("DROP TRIGGER IF EXISTS trg_atualiza_pergunta_tsv ON pares_qa;")
    op.execute("DROP FUNCTION IF EXISTS atualiza_pergunta_tsv();")

    # Remove índice e coluna
    op.drop_index('idx_pares_qa_pergunta_tsv', table_name='pares_qa')
    op.drop_column('pares_qa', 'pergunta_tsv')
