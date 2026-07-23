"""adiciona categorias marca aplicacao modelos

Revision ID: 2026072114
Revises: 2026072004
Create Date: 2026-07-21 14:58:24.124332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026072114"
down_revision: Union[str, None] = "2026072004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('categorias',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('descricao', sa.String(length=100), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('descricao')
    )
    op.execute(
        """
        INSERT INTO categorias (descricao, ativo, created_at)
        VALUES
            ('Controle de Acesso', TRUE, NOW()),
            ('Controle de Ponto', TRUE, NOW()),
            ('Softwares', TRUE, NOW()),
            ('Vigilância', TRUE, NOW()),
            ('Roteadores', TRUE, NOW())
        """
    )
    op.create_table('modelos_categorias',
    sa.Column('modelo_id', sa.Integer(), nullable=False),
    sa.Column('categoria_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['modelo_id'], ['modelos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('modelo_id', 'categoria_id')
    )
    op.add_column('modelos', sa.Column('marca', sa.String(length=100), nullable=True))
    op.add_column('modelos', sa.Column('aplicacao', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("modelos", "aplicacao")
    op.drop_column("modelos", "marca")
    op.drop_table("modelos_categorias")
    op.drop_table("categorias")
