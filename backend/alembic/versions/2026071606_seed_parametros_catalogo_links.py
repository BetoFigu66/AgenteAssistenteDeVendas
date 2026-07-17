"""seed_parametros_catalogo_links

Revision ID: 2026071606
Revises: 2026071605
Create Date: 2026-07-16 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026071606"
down_revision: Union[str, None] = "2026071605"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # REQ-003.11: links dos catálogos por tipo de produto, configuráveis via
    # PATCH /api/parametros/{nome} sem deploy. Valor vazio até alguém configurar o link
    # público real — o processador trata "vazio" como "catálogo indisponível no momento".
    op.execute(
        """
        INSERT INTO parametros (nome, valor, descricao, created_at, updated_at)
        VALUES
            (
                'catalogo_link_catraca',
                '',
                'Link publico do catalogo de catracas enviado ao cliente (REQ-003.11)',
                NOW(),
                NOW()
            ),
            (
                'catalogo_link_relogio_ponto',
                '',
                'Link publico do catalogo de relogios de ponto enviado ao cliente (REQ-003.11)',
                NOW(),
                NOW()
            )
        ON CONFLICT (nome) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM parametros
        WHERE nome IN ('catalogo_link_catraca', 'catalogo_link_relogio_ponto');
        """
    )
