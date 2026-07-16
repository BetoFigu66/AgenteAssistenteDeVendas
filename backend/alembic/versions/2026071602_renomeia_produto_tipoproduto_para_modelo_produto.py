"""renomeia Produto/TipoProduto para Modelo/Produto (decisão 2026-07-09)

As duas entidades de catálogo trocam de sentido entre si (documentado em
`docs/dicionario_termos.md`, decisão de 2026-07-09, implementação pendente até agora):

- `tipos_produto` (categoria genérica: "catraca", "relógio de ponto") -> `produtos`
- `produtos` (SKU específico e precificável) -> `modelos`

Não é find-replace direto: os dois nomes trocam de sentido, e `itens_atendimento` tem
DUAS colunas com prefixo "produto" apontando pra tabelas diferentes
(`tipo_produto_id`/`produto_id`), que também trocam de papel. Ordem "vacate-first" em
todo nível (tabela -> sequence -> PK -> unique -> FK -> índice -> coluna): sempre libera
o nome-alvo antes de reivindicá-lo, pra nunca colidir com um nome que ainda está em uso.

Segue o mesmo padrão (rename_table + rename de sequence/constraint/índice, localizando
constraints dinamicamente pela coluna em vez de nome fixo) já usado e testado em
`2026071001_rename_itens_negociacao_para_itens_atendimento.py`. Tabelas confirmadas vazias
neste ambiente (risco de perda de dado é baixo), mas o schema precisa ficar correto porque
`itens_atendimento`/`itens_orcamento` dependem via FK.

Revision ID: 2026071602
Revises: 2026071601
Create Date: 2026-07-16 09:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "2026071602"
down_revision: Union[str, None] = "2026071601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_index(old: str, new: str) -> None:
    op.execute(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"')


def _rename_constraint_by_column(table: str, column: str, contype: str, new_name: str) -> None:
    """Renomeia a constraint (pk='p'/fk='f'/unique='u') que envolve `column` em `table`,
    seja qual for o nome atual — protege contra drift de nome (mesmo padrão já usado em
    2026071001), e funciona mesmo quando `column` acabou de ser renomeada nesta MESMA
    migration (pg_attribute já reflete o rename dentro da mesma transação)."""
    conn = op.get_bind()
    row = conn.execute(
        text(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.conrelid = CAST(:table AS regclass)
              AND c.contype = :contype
              AND a.attname = :column
            """
        ),
        {"table": table, "contype": contype, "column": column},
    ).fetchone()
    if row and row[0] != new_name:
        conn.execute(text(f'ALTER TABLE {table} RENAME CONSTRAINT "{row[0]}" TO "{new_name}"'))


def upgrade() -> None:
    # ---- Fase 1: libera "produtos" migrando o SKU atual (Produto) para "modelos" ----
    op.rename_table("produtos", "modelos")
    op.execute('ALTER SEQUENCE IF EXISTS "produtos_id_seq" RENAME TO "modelos_id_seq"')
    _rename_constraint_by_column("modelos", "id", "p", "modelos_pkey")
    _rename_constraint_by_column("modelos", "codigo", "u", "modelos_codigo_key")
    # FK ainda referencia a coluna com o nome antigo (tipo_produto_id) — a constraint
    # continua válida mesmo a tabela-alvo ainda não ter sido renomeada (FK aponta por OID).
    _rename_constraint_by_column("modelos", "tipo_produto_id", "f", "modelos_tipo_produto_id_fkey")
    _rename_index("ix_produtos_tipo_produto_id", "ix_modelos_tipo_produto_id")

    # ---- Fase 2: libera "tipos_produto" (nome já vago) -> vira "produtos" (categoria) ----
    op.rename_table("tipos_produto", "produtos")
    op.execute('ALTER SEQUENCE IF EXISTS "tipos_produto_id_seq" RENAME TO "produtos_id_seq"')
    _rename_constraint_by_column("produtos", "id", "p", "produtos_pkey")
    _rename_constraint_by_column("produtos", "descricao", "u", "produtos_descricao_key")

    # ---- Fase 3: renomeia a coluna de FK dentro de "modelos" (agora que a tabela-alvo
    # "produtos" já existe com o novo sentido) ----
    op.execute('ALTER TABLE modelos RENAME COLUMN tipo_produto_id TO produto_id')
    _rename_constraint_by_column("modelos", "produto_id", "f", "modelos_produto_id_fkey")
    _rename_index("ix_modelos_tipo_produto_id", "ix_modelos_produto_id")

    # ---- Fase 4: itens_atendimento tem DUAS colunas com prefixo "produto" que trocam de
    # papel entre si — ordem vacate-first também nas colunas, FKs e índices (o nome-alvo
    # de cada rename é o nome ATUAL do outro par, então a ordem abaixo não pode inverter):
    #   produto_id -> modelo_id  (sempre PRIMEIRO, libera "produto_id" pro próximo passo)
    #   tipo_produto_id -> produto_id  (só depois, quando "produto_id" já está livre)
    op.execute('ALTER TABLE itens_atendimento RENAME COLUMN produto_id TO modelo_id')
    op.execute('ALTER TABLE itens_atendimento RENAME COLUMN tipo_produto_id TO produto_id')
    # Mesma ordem vacate-first nas FKs: a constraint que ficou em "modelo_id" tem o nome
    # antigo "itens_atendimento_produto_id_fkey" — precisa ser renomeada ANTES da outra
    # constraint reivindicar esse mesmo nome-alvo.
    _rename_constraint_by_column("itens_atendimento", "modelo_id", "f", "itens_atendimento_modelo_id_fkey")
    _rename_constraint_by_column("itens_atendimento", "produto_id", "f", "itens_atendimento_produto_id_fkey")
    # E nos índices: mesmo motivo, mesma ordem.
    _rename_index("ix_itens_atendimento_produto_id", "ix_itens_atendimento_modelo_id")
    _rename_index("ix_itens_atendimento_tipo_produto_id", "ix_itens_atendimento_produto_id")

    # ---- Fase 5: itens_orcamento (troca simples, sem par cruzado) ----
    op.execute('ALTER TABLE itens_orcamento RENAME COLUMN produto_id TO modelo_id')
    _rename_constraint_by_column("itens_orcamento", "modelo_id", "f", "itens_orcamento_modelo_id_fkey")
    _rename_index("ix_itens_orcamento_produto_id", "ix_itens_orcamento_modelo_id")


def downgrade() -> None:
    # Espelho exato em ordem inversa — a reversão de uma sequência vacate-first válida é
    # garantidamente vacate-first válida também.

    # ---- Reverte Fase 5 ----
    _rename_index("ix_itens_orcamento_modelo_id", "ix_itens_orcamento_produto_id")
    _rename_constraint_by_column("itens_orcamento", "modelo_id", "f", "itens_orcamento_produto_id_fkey")
    op.execute('ALTER TABLE itens_orcamento RENAME COLUMN modelo_id TO produto_id')

    # ---- Reverte Fase 4 (mesma ordem vacate-first, espelhada) ----
    _rename_index("ix_itens_atendimento_produto_id", "ix_itens_atendimento_tipo_produto_id")
    _rename_index("ix_itens_atendimento_modelo_id", "ix_itens_atendimento_produto_id")
    _rename_constraint_by_column("itens_atendimento", "produto_id", "f", "itens_atendimento_tipo_produto_id_fkey")
    _rename_constraint_by_column("itens_atendimento", "modelo_id", "f", "itens_atendimento_produto_id_fkey")
    op.execute('ALTER TABLE itens_atendimento RENAME COLUMN produto_id TO tipo_produto_id')
    op.execute('ALTER TABLE itens_atendimento RENAME COLUMN modelo_id TO produto_id')

    # ---- Reverte Fase 3 ----
    _rename_index("ix_modelos_produto_id", "ix_modelos_tipo_produto_id")
    _rename_constraint_by_column("modelos", "produto_id", "f", "modelos_tipo_produto_id_fkey")
    op.execute('ALTER TABLE modelos RENAME COLUMN produto_id TO tipo_produto_id')

    # ---- Reverte Fase 2 ----
    _rename_constraint_by_column("produtos", "descricao", "u", "tipos_produto_descricao_key")
    _rename_constraint_by_column("produtos", "id", "p", "tipos_produto_pkey")
    op.execute('ALTER SEQUENCE IF EXISTS "produtos_id_seq" RENAME TO "tipos_produto_id_seq"')
    op.rename_table("produtos", "tipos_produto")

    # ---- Reverte Fase 1 ----
    _rename_index("ix_modelos_tipo_produto_id", "ix_produtos_tipo_produto_id")
    _rename_constraint_by_column("modelos", "tipo_produto_id", "f", "produtos_tipo_produto_id_fkey")
    _rename_constraint_by_column("modelos", "codigo", "u", "produtos_codigo_key")
    _rename_constraint_by_column("modelos", "id", "p", "produtos_pkey")
    op.execute('ALTER SEQUENCE IF EXISTS "modelos_id_seq" RENAME TO "produtos_id_seq"')
    op.rename_table("modelos", "produtos")
