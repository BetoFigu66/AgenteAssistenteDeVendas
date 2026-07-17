"""adiciona_campos_escalonamento_atendimento

Revision ID: 2026071702
Revises: 2026071701
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026071702"
down_revision: Union[str, None] = "2026071701"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-004 (Fase 5): auditoria mínima de escalonamento, mesmo padrão de
    # encerrado_em/encerrado_por (Fase 1) — sem CHECK constraint (diferente de
    # motivo_encerramento) porque a tabela de eventos genérica só vem na Fase 6/REQ-005;
    # aqui é a "solução simples" que o plano pede.
    op.add_column("atendimentos", sa.Column("escalado_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("atendimentos", sa.Column("escalado_por", sa.String(length=50), nullable=True))
    op.add_column("atendimentos", sa.Column("motivo_escalonamento", sa.String(length=30), nullable=True))
    op.add_column("atendimentos", sa.Column("resumo_escalonamento", sa.Text(), nullable=True))

    # REQ-004.8: limiar de funcionários pra considerar "cliente grande/projeto complexo"
    # — o próprio requisito deixa em aberto ("a definir com o vendedor"), então fica
    # configurável em runtime (mesmo padrão de janela_continuacao_atendimento_horas).
    op.execute(
        """
        INSERT INTO parametros (nome, valor, descricao, created_at, updated_at)
        VALUES (
            'escalonamento_limiar_funcionarios',
            '50',
            'Quantidade de funcionarios a partir da qual o atendimento e considerado '
            'projeto complexo e escala para humano (REQ-004.8)',
            NOW(),
            NOW()
        )
        ON CONFLICT (nome) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametros WHERE nome = 'escalonamento_limiar_funcionarios';")
    op.drop_column("atendimentos", "resumo_escalonamento")
    op.drop_column("atendimentos", "motivo_escalonamento")
    op.drop_column("atendimentos", "escalado_por")
    op.drop_column("atendimentos", "escalado_em")
