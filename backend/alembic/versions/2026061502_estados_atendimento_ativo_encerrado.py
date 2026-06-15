"""estados atendimento ativo encerrado com motivo_encerramento

Colapsa statusnegociacao para statusatendimento {ativo, encerrado}.
Remapeia valores legados do POC (novo, em_contato, fechado_venda, etc.).

Revision ID: 2026061502
Revises: 2026061501
Create Date: 2026-06-15 18:00:00.000000

"""
from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

logger = logging.getLogger("alembic.runtime.migration")

revision: str = "2026061502"
down_revision: Union[str, None] = "2026061501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_ATIVO_LEGADO = (
    "novo",
    "em_contato",
    "aguardando_orcamento",
    "orcamento_enviado",
    "em_negociacao",
)

MOTIVOS_ENCERRAMENTO = (
    "concluido_pelo_cliente",
    "abandono",
    "manual_vendedor",
    "inatividade",
    "ganha_legado",
    "perdida_legado",
)


def _log_contagens(conn, coluna: str) -> None:
    rows = conn.execute(
        text(f"SELECT {coluna}::text AS val, COUNT(*) AS n FROM atendimentos GROUP BY 1 ORDER BY 1")
    )
    for row in rows:
        logger.info("[T-A1b] atendimentos.%s = %s → %s linha(s)", coluna, row.val, row.n)


def _auditar_fechado_venda_sem_orcamento_aprovado(conn) -> None:
    rows = conn.execute(
        text(
            """
            SELECT a.id
            FROM atendimentos a
            WHERE a.status::text = 'fechado_venda'
              AND NOT EXISTS (
                SELECT 1 FROM orcamentos o
                WHERE o.atendimento_id = a.id
                  AND o.status::text = 'aprovado'
              )
            """
        )
    ).fetchall()
    for row in rows:
        logger.warning(
            "[T-A1b] atendimento id=%s fechado_venda sem orcamento aprovado — motivo ganha_legado mesmo assim",
            row.id,
        )


def upgrade() -> None:
    conn = op.get_bind()
    logger.info("[T-A1b] upgrade — snapshot status legado")
    _log_contagens(conn, "status")

    status_atendimento = postgresql.ENUM("ativo", "encerrado", name="statusatendimento")
    status_atendimento.create(conn, checkfirst=True)

    op.add_column("atendimentos", sa.Column("motivo_encerramento", sa.String(length=50), nullable=True))
    op.add_column(
        "atendimentos",
        sa.Column(
            "status_novo",
            postgresql.ENUM("ativo", "encerrado", name="statusatendimento", create_type=False),
            nullable=True,
        ),
    )

    _auditar_fechado_venda_sem_orcamento_aprovado(conn)

    ativos = ", ".join(f"'{s}'" for s in STATUS_ATIVO_LEGADO)
    conn.execute(
        text(
            f"""
            UPDATE atendimentos
            SET status_novo = 'ativo', motivo_encerramento = NULL
            WHERE status::text IN ({ativos})
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_novo = 'encerrado', motivo_encerramento = 'ganha_legado'
            WHERE status::text = 'fechado_venda'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_novo = 'encerrado', motivo_encerramento = 'perdida_legado'
            WHERE status::text = 'fechado_perda'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_novo = 'encerrado', motivo_encerramento = 'abandono'
            WHERE status::text = 'arquivado'
            """
        )
    )

    orphan = conn.execute(
        text("SELECT COUNT(*) FROM atendimentos WHERE status_novo IS NULL")
    ).scalar()
    if orphan:
        raise RuntimeError(
            f"[T-A1b] {orphan} atendimento(s) com status legado não mapeado — abortando migration"
        )

    logger.info("[T-A1b] pós-remapeamento")
    _log_contagens(conn, "status_novo")

    op.drop_column("atendimentos", "status")
    op.alter_column("atendimentos", "status_novo", new_column_name="status", nullable=False)

    # Tabelas vazias recriadas pelo app enquanto models.py ainda aponta para negociacoes.
    op.execute("DROP TABLE IF EXISTS negociacao_infos CASCADE")
    op.execute("DROP TABLE IF EXISTS negociacoes CASCADE")

    op.execute("DROP TYPE statusnegociacao")

    motivos_sql = ", ".join(f"'{m}'" for m in MOTIVOS_ENCERRAMENTO)
    op.create_check_constraint(
        "ck_atendimentos_status",
        "atendimentos",
        "status IN ('ativo', 'encerrado')",
    )
    op.create_check_constraint(
        "ck_atendimentos_motivo_encerramento",
        "atendimentos",
        f"""(
            (status = 'ativo' AND motivo_encerramento IS NULL)
            OR (
                status = 'encerrado'
                AND motivo_encerramento IS NOT NULL
                AND motivo_encerramento IN ({motivos_sql})
            )
        )""",
    )


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_constraint("ck_atendimentos_motivo_encerramento", "atendimentos", type_="check")
    op.drop_constraint("ck_atendimentos_status", "atendimentos", type_="check")

    status_negociacao = postgresql.ENUM(
        "novo",
        "em_contato",
        "aguardando_orcamento",
        "orcamento_enviado",
        "em_negociacao",
        "fechado_venda",
        "fechado_perda",
        "arquivado",
        name="statusnegociacao",
    )
    status_negociacao.create(conn, checkfirst=True)

    op.add_column(
        "atendimentos",
        sa.Column(
            "status_legado",
            postgresql.ENUM(
                "novo",
                "em_contato",
                "aguardando_orcamento",
                "orcamento_enviado",
                "em_negociacao",
                "fechado_venda",
                "fechado_perda",
                "arquivado",
                name="statusnegociacao",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_legado = 'novo'
            WHERE status = 'ativo'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_legado = 'fechado_venda'
            WHERE status = 'encerrado' AND motivo_encerramento = 'ganha_legado'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_legado = 'fechado_perda'
            WHERE status = 'encerrado' AND motivo_encerramento = 'perdida_legado'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE atendimentos
            SET status_legado = 'arquivado'
            WHERE status = 'encerrado'
              AND motivo_encerramento IN (
                  'abandono', 'inatividade', 'concluido_pelo_cliente', 'manual_vendedor'
              )
            """
        )
    )

    orphan = conn.execute(
        text("SELECT COUNT(*) FROM atendimentos WHERE status_legado IS NULL")
    ).scalar()
    if orphan:
        raise RuntimeError(
            f"[T-A1b] downgrade: {orphan} atendimento(s) sem status_legado — abortando"
        )

    op.drop_column("atendimentos", "status")
    op.alter_column("atendimentos", "status_legado", new_column_name="status", nullable=False)
    op.drop_column("atendimentos", "motivo_encerramento")

    op.execute("DROP TYPE statusatendimento")
