# SQL manuais legados

Os arquivos nesta pasta foram **workarounds temporários** criados quando o Alembic estava inoperante por um problema de ambiente (conflito do Miniconda com `libffi`/`libp11-kit`). Eles foram aplicados manualmente no banco via DBeaver/`psql`.

⚠️ **Estes arquivos estão congelados — não executar novamente.**

## Substituídos por

Cada arquivo foi convertido em uma migration Alembic oficial:

| SQL manual                           | Migration Alembic equivalente                                      |
|--------------------------------------|---------------------------------------------------------------------|
| `001_processamentos_e_reports.sql`   | `alembic/versions/db98912c2a80_adiciona_processamentos_e_reports.py` |
| `002_reports_triagem.sql`            | `alembic/versions/a7f3e8c1d2b4_adiciona_triagem_em_reports.py`      |

## Divergência com as migrations

Os SQLs manuais criaram as colunas de classificação/triagem como `VARCHAR`. As migrations Alembic correspondentes criam **tipos ENUM nativos do Postgres**, alinhando com o modelo SQLAlchemy e com o padrão da migration inicial (`80c013aa867b_schema_inicial_completo.py`).

Bancos que foram inicializados pelos SQLs manuais precisam de um passo extra de normalização (converter as colunas `VARCHAR` em ENUM). Ver `docs/comandos_uteis.md`.

## Diretriz relacionada

Este episódio originou a **D01** do harness do Implementador:
`artefatos/implementador/diretrizes.md`.
