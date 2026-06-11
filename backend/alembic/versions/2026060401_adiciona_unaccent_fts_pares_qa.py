"""adiciona_unaccent_fts_pares_qa

Revision ID: 2026060401
Revises: 2026060201
Create Date: 2026-06-04 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2026060401'
down_revision: Union[str, None] = '2026060201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cria extensão unaccent (idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # 2. Cria configuração full-text portuguese_unaccent baseada no padrão
    # (DROP + CREATE pois PostgreSQL não suporta IF NOT EXISTS nesse comando)
    op.execute("""
        DROP TEXT SEARCH CONFIGURATION IF EXISTS portuguese_unaccent CASCADE;
    """)
    op.execute("""
        CREATE TEXT SEARCH CONFIGURATION portuguese_unaccent
            (COPY = pg_catalog.portuguese);
    """)

    # 3. Substitui o mapeamento padrão para usar unaccent + stemming português
    op.execute("""
        ALTER TEXT SEARCH CONFIGURATION portuguese_unaccent
            ALTER MAPPING FOR hword, hword_part, word
            WITH unaccent, portuguese_stem;
    """)

    # 4. Atualiza função de trigger para usar portuguese_unaccent
    op.execute("""
        CREATE OR REPLACE FUNCTION atualiza_pergunta_tsv()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.pergunta_tsv := to_tsvector('portuguese_unaccent', NEW.pergunta);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 5. Reconstrói tsvector de todos os registros existentes com novo dicionário
    op.execute("""
        UPDATE pares_qa
        SET pergunta_tsv = to_tsvector('portuguese_unaccent', pergunta)
        WHERE pergunta IS NOT NULL;
    """)


def downgrade() -> None:
    # Reverte trigger para dicionário padrão
    op.execute("""
        CREATE OR REPLACE FUNCTION atualiza_pergunta_tsv()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.pergunta_tsv := to_tsvector('portuguese', NEW.pergunta);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Reconstrói tsvector com dicionário padrão
    op.execute("""
        UPDATE pares_qa
        SET pergunta_tsv = to_tsvector('portuguese', pergunta)
        WHERE pergunta IS NOT NULL;
    """)

    # Remove configuração customizada (não remove a extensão unaccent pois pode ser usada em outro lugar)
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS portuguese_unaccent CASCADE;")
