"""limpeza de drift de DDL manual: tabelas fantasma + constraints com typo

Corrige um drift de DDL aplicado manualmente fora do Alembic, encontrado ao
implementar o passo A0 do MVP Continuidade (2026-07-10):

1. Tabelas fantasmas vazias `negociacoes` e `negociacao_infos` — remanescentes
   de `Base.metadata.create_all()` (ver `backend/database.py`) rodando antes
   da migration 2026061501 (rename negociacoes -> atendimentos) ter sido
   aplicada em algum momento. Ambas com 0 linhas, verificado antes de remover.
2. Sequences que a migration 2026061501 esqueceu de renomear: `atendimentos.id`
   ainda usava `negociacoes_id_seq`; `atendimento_infos.id` ainda usava
   `negociacao_infos_id_seq`.
3. Constraints de FK com nomes com typo (`atendimentao` no lugar de
   `atendimento`, `atendimentoes` no lugar de `atendimentos`), fruto de ALTER
   TABLE RENAME CONSTRAINT manual feito fora do Alembic — a migration 2026061501
   por si só nunca teria produzido esses nomes (seu transform de string dá o
   nome correto), então isso foi um ajuste manual posterior.

Todas as renomeações de constraint/sequence só executam se o nome antigo
(com o problema) realmente existir — em uma base nova, criada do zero a partir
do historico de migrations, os nomes ja nascem corretos e esta migration não
faz nada além de checar e seguir em frente.

Revision ID: 2026071002
Revises: 2026071001
Create Date: 2026-07-10 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "2026071002"
down_revision: Union[str, None] = "2026071001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dropar_fantasma_vazia(table: str) -> None:
    """Remove uma tabela fantasma (0 linhas) criada por `create_all()` fora do Alembic.

    Nunca apaga dados: se a tabela nao existir, nao faz nada; se existir com
    linhas, levanta erro em vez de remover silenciosamente.
    """
    conn = op.get_bind()
    existe = conn.execute(text("SELECT to_regclass(:table) IS NOT NULL"), {"table": table}).scalar()
    if not existe:
        return
    total = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
    if total:
        raise RuntimeError(
            f"Tabela fantasma '{table}' tem {total} linha(s) — não removendo automaticamente. "
            "Investigar manualmente antes de rodar esta migration."
        )
    op.execute(f'DROP TABLE "{table}"')


def _rename_constraint(table: str, old: str, new: str) -> None:
    """Renomeia a constraint `old` -> `new` em `table`, só se `old` existir com esse nome."""
    conn = op.get_bind()
    existe = conn.execute(
        text("SELECT 1 FROM pg_constraint WHERE conrelid = CAST(:table AS regclass) AND conname = :old"),
        {"table": table, "old": old},
    ).scalar()
    if existe:
        op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old}" TO "{new}"')


def _rename_sequence(old: str, new: str) -> None:
    op.execute(f'ALTER SEQUENCE IF EXISTS "{old}" RENAME TO "{new}"')


def upgrade() -> None:
    # 1. Tabelas fantasmas vazias (ordem: filha antes da pai, por causa da FK entre elas)
    _dropar_fantasma_vazia("negociacao_infos")
    _dropar_fantasma_vazia("negociacoes")

    # 2. Sequences esquecidas pela migration 2026061501
    _rename_sequence("negociacoes_id_seq", "atendimentos_id_seq")
    _rename_sequence("negociacao_infos_id_seq", "atendimento_infos_id_seq")

    # 3. Constraints com typo (drift de ALTER manual fora do Alembic)
    _rename_constraint("atendimentos", "atendimentoes_contato_id_fkey", "atendimentos_contato_id_fkey")
    _rename_constraint("atendimentos", "atendimentoes_empresa_id_fkey", "atendimentos_empresa_id_fkey")
    _rename_constraint(
        "atendimentos", "fk_atendimentoes_pessoa_id_pessoas", "fk_atendimentos_pessoa_id_pessoas"
    )
    _rename_constraint(
        "atendimento_infos",
        "atendimentao_infos_atendimentao_id_fkey",
        "atendimento_infos_atendimento_id_fkey",
    )
    _rename_constraint("mensagens", "mensagens_atendimentao_id_fkey", "mensagens_atendimento_id_fkey")
    _rename_constraint("orcamentos", "orcamentos_atendimentao_id_fkey", "orcamentos_atendimento_id_fkey")
    _rename_constraint(
        "processamentos_mensagem",
        "processamentos_mensagem_atendimentao_id_ativa_fkey",
        "processamentos_mensagem_atendimento_id_ativa_fkey",
    )


def downgrade() -> None:
    # Reverte só os nomes (não recria as tabelas fantasmas — eram vazias e não deveriam existir).
    _rename_constraint(
        "processamentos_mensagem",
        "processamentos_mensagem_atendimento_id_ativa_fkey",
        "processamentos_mensagem_atendimentao_id_ativa_fkey",
    )
    _rename_constraint("orcamentos", "orcamentos_atendimento_id_fkey", "orcamentos_atendimentao_id_fkey")
    _rename_constraint("mensagens", "mensagens_atendimento_id_fkey", "mensagens_atendimentao_id_fkey")
    _rename_constraint(
        "atendimento_infos",
        "atendimento_infos_atendimento_id_fkey",
        "atendimentao_infos_atendimentao_id_fkey",
    )
    _rename_constraint(
        "atendimentos", "fk_atendimentos_pessoa_id_pessoas", "fk_atendimentoes_pessoa_id_pessoas"
    )
    _rename_constraint("atendimentos", "atendimentos_empresa_id_fkey", "atendimentoes_empresa_id_fkey")
    _rename_constraint("atendimentos", "atendimentos_contato_id_fkey", "atendimentoes_contato_id_fkey")

    _rename_sequence("atendimento_infos_id_seq", "negociacao_infos_id_seq")
    _rename_sequence("atendimentos_id_seq", "negociacoes_id_seq")
