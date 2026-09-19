"""Cria o schema `teste_conversas` (se não existir) e as tabelas do testador.

Idempotente — pode rodar de novo sem apagar dados já existentes.
"""

from config import SCHEMA
from db import engine
from models import Base
from sqlalchemy import text


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
    Base.metadata.create_all(engine)
    print(f"Schema '{SCHEMA}' e tabelas criados/atualizados.")


if __name__ == "__main__":
    main()
