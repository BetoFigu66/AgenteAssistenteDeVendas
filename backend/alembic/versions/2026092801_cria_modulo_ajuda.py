"""cria_modulo_ajuda

Cria as tabelas do FAQ de ajuda contextual do painel: `ajuda_contextos`,
`ajuda_conteudos` e `ajuda_consultas`.

Independentes de `pares_qa`/`documentos_conhecimento` de proposito — publicos
diferentes (operador interno x cliente do WhatsApp). Ver `backend/models/ajuda.py`.

A configuracao full-text `portuguese_unaccent` ja foi criada pela migration
2026060401 (pares_qa) e e reaproveitada aqui; a funcao de trigger, nao — cada
tabela tem a sua, porque o nome da coluna de origem faz parte do corpo da funcao.

Revision ID: 2026092801
Revises: 2026092701
Create Date: 2026-09-28 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026092801'
down_revision: Union[str, None] = '2026092701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Contextos iniciais: as 5 telas do painel + o global. As chaves casam com os
# arquivos `frontend/src/ajuda/<chave>.md` e com o `contexto` passado pelo
# `<BotaoAjuda contexto="...">`.
CONTEXTOS_INICIAIS = [
    ("chat", "Chat (simulador de atendimento)", "Simulacao de conversa como se fosse o cliente."),
    ("acompanhamento", "Acompanhamento de Atendimentos", "Fila de atendimentos, aprovacao de mensagens e modo de operacao."),
    ("reports", "Triagem de Reports", "Fila de problemas reportados sobre respostas do assistente."),
    ("qa-base", "Base Q&A", "Perguntas e respostas curadas que o assistente usa com clientes."),
    ("parametros", "Parametros", "Ajustes de funcionamento alteraveis sem reiniciar o sistema."),
    ("ajuda-base", "Base de Ajuda", "Administracao do conteudo de ajuda do proprio painel."),
]


def upgrade() -> None:
    op.create_table(
        "ajuda_contextos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chave", sa.String(length=100), nullable=False),
        sa.Column("rotulo", sa.String(length=150), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave"),
    )

    op.create_table(
        "ajuda_conteudos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contexto_id", sa.Integer(), nullable=True),
        sa.Column("pergunta", sa.Text(), nullable=False),
        sa.Column("resposta", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pergunta_tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("criado_por", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["contexto_id"], ["ajuda_contextos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # `vector` nao tem tipo SQLAlchemy nativo aqui (Vector e UserDefinedType),
    # entao a coluna entra por DDL direto — mesmo caminho das demais tabelas pgvector.
    op.execute("ALTER TABLE ajuda_conteudos ADD COLUMN embedding vector(1536);")

    op.create_index("idx_ajuda_conteudos_contexto_id", "ajuda_conteudos", ["contexto_id"])
    op.create_index("idx_ajuda_conteudos_contexto_ativo", "ajuda_conteudos", ["contexto_id", "ativo"])
    op.create_index(
        "idx_ajuda_conteudos_pergunta_tsv",
        "ajuda_conteudos",
        ["pergunta_tsv"],
        postgresql_using="gin",
    )

    op.create_table(
        "ajuda_consultas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pergunta", sa.Text(), nullable=False),
        sa.Column("contexto", sa.String(length=100), nullable=True),
        sa.Column("encontrou", sa.Boolean(), nullable=False),
        sa.Column("conteudo_id", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("origem_busca", sa.String(length=20), nullable=True),
        sa.Column("usuario", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conteudo_id"], ["ajuda_conteudos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ajuda_consultas_contexto", "ajuda_consultas", ["contexto"])
    op.create_index("idx_ajuda_consultas_encontrou", "ajuda_consultas", ["encontrou"])
    op.create_index("idx_ajuda_consultas_encontrou_data", "ajuda_consultas", ["encontrou", "created_at"])

    # Mantem `pergunta_tsv` sincronizado com `pergunta`, usando o mesmo dicionario
    # com unaccent criado na 2026060401 (acento deixa de atrapalhar a busca).
    op.execute("""
        CREATE OR REPLACE FUNCTION atualiza_ajuda_conteudos_tsv()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.pergunta_tsv := to_tsvector('portuguese_unaccent', NEW.pergunta);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_atualiza_ajuda_conteudos_tsv
        BEFORE INSERT OR UPDATE OF pergunta ON ajuda_conteudos
        FOR EACH ROW
        EXECUTE FUNCTION atualiza_ajuda_conteudos_tsv();
    """)

    # Seed dos contextos. Idempotente para nao quebrar em bases que ja tenham
    # a chave (ex.: reaplicacao manual durante desenvolvimento).
    tabela = sa.table(
        "ajuda_contextos",
        sa.column("chave", sa.String),
        sa.column("rotulo", sa.String),
        sa.column("descricao", sa.Text),
    )
    op.bulk_insert(
        tabela,
        [{"chave": c, "rotulo": r, "descricao": d} for c, r, d in CONTEXTOS_INICIAIS],
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_atualiza_ajuda_conteudos_tsv ON ajuda_conteudos;")
    op.execute("DROP FUNCTION IF EXISTS atualiza_ajuda_conteudos_tsv();")

    op.drop_index("idx_ajuda_consultas_encontrou_data", table_name="ajuda_consultas")
    op.drop_index("idx_ajuda_consultas_encontrou", table_name="ajuda_consultas")
    op.drop_index("idx_ajuda_consultas_contexto", table_name="ajuda_consultas")
    op.drop_table("ajuda_consultas")

    op.drop_index("idx_ajuda_conteudos_pergunta_tsv", table_name="ajuda_conteudos")
    op.drop_index("idx_ajuda_conteudos_contexto_ativo", table_name="ajuda_conteudos")
    op.drop_index("idx_ajuda_conteudos_contexto_id", table_name="ajuda_conteudos")
    op.drop_table("ajuda_conteudos")

    op.drop_table("ajuda_contextos")
