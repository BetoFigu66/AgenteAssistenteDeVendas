"""cria tabela perguntas_produto (texto de uma pergunta do roteiro por produto)

Antes, cada pergunta do roteiro de qualificação tinha um texto só, fixo no código, e a do
modelo falava de relógio para qualquer produto ("O relógio seria cartográfico ou
eletrônico? Se eletrônico: ...?", duas perguntas numa mensagem). A tabela permite um texto
por produto, editado no painel (`services/perguntas_produto.py`); sem linha, vale o do
código.

Carga inicial (proposta de 02/11, a revisar pelo Beto): a pergunta do modelo, numa
pergunta só, para os produtos cujo catálogo tem tecnologias de leitura. Produto que não
existe no banco é pulado.

Revision ID: 2026110201
Revises: 2026110101
Create Date: 2026-11-02 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026110201"
down_revision: Union[str, None] = "2026110101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (descrição do produto, campo, texto)
_SEED = [
    (
        "Relógio de Ponto",
        "modelo_produto",
        "Qual tecnologia de marcação você prefere: cartográfico, cartão de proximidade, cartão de barras, "
        "biometria ou reconhecimento facial?",
    ),
    (
        "Catraca",
        "modelo_produto",
        "Qual forma de identificação você quer na catraca: cartão de proximidade, biometria, "
        "reconhecimento facial ou QR Code?",
    ),
    (
        "Leitor Facial",
        "modelo_produto",
        "Você prefere um leitor só de reconhecimento facial ou que também leia biometria (digital)?",
    ),
]


def upgrade() -> None:
    op.create_table(
        "perguntas_produto",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("campo", sa.String(length=60), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("atualizado_por", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("produto_id", "campo"),
    )
    op.create_index("ix_perguntas_produto_produto_id", "perguntas_produto", ["produto_id"])
    for descricao, campo, texto in _SEED:
        op.execute(
            sa.text(
                "INSERT INTO perguntas_produto (produto_id, campo, texto, ativo, atualizado_por) "
                "SELECT id, :campo, :texto, true, 'migração' FROM produtos WHERE descricao = :descricao"
            ).bindparams(descricao=descricao, campo=campo, texto=texto)
        )


def downgrade() -> None:
    # Sem a tabela, `services/perguntas_produto.py` usa os textos do código.
    op.drop_index("ix_perguntas_produto_produto_id", table_name="perguntas_produto")
    op.drop_table("perguntas_produto")
