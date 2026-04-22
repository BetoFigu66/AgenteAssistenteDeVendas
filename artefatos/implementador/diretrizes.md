# Harness do Agente Implementador

Este documento é o **contrato de conduta** que toda implementação neste repositório deve seguir. Cada diretriz foi acumulada a partir de um episódio real do projeto e permanece ativa até ser revisada explicitamente.

> 🧭 **Regra de ouro:** leia este arquivo antes de implementar algo não-trivial. Se uma situação nova não estiver coberta, **pergunte ao usuário** e registre a decisão como nova diretriz.

---

## Diretrizes ativas

### D01 — Não mudar a forma de implementar em função de problemas temporários de ambiente
- **Categoria:** arquitetura
- **Registrada em:** 2026-04-21
- **Regra:** Quando surgir um problema de ambiente (erro de import, lib faltando, container quebrado, conda conflitando, etc.), a resposta correta é **resolver o problema de ambiente**, NÃO contornar a arquitetura do projeto usando uma abordagem alternativa "mais fácil".
- **Motivação:** Atalhos feitos sob pressão de ambiente tendem a virar dívida técnica permanente. A arquitetura foi decidida deliberadamente (ex.: Alembic para migrations, SQLAlchemy para ORM, Docker Compose para dev) e deve ser preservada. Ambiente é circunstancial; arquitetura é contratual.
- **Contexto originário:** Durante a implementação do sistema de triagem de reports, o Alembic falhou com `ImportError: libp11-kit.so.0: undefined symbol: ffi_type_pointer` por conflito com o Miniconda. Em vez de resolver o ambiente (usar venv limpa ou `python -m alembic`), geramos migrations como scripts SQL manuais em `backend/sql/*.sql`. Resultado: duas migrations fora do controle do Alembic, sem versionamento automático e sem rollback. A regra do projeto (memória do usuário) já dizia: *"Alembic para migrations"*.
- **Aplicação prática:**
  - ❌ "Alembic está quebrado, vou gerar SQL manual."
  - ✅ "Alembic está quebrado. Vou primeiro diagnosticar/resolver o ambiente. Se levar mais que alguns minutos, reporto ao usuário e peço orientação — não troco a abordagem sem aprovação explícita."
  - Se for **absolutamente inevitável** fazer um workaround, ele deve vir com: (a) aviso explícito ao usuário, (b) TODO de regularização, (c) prazo para reverter.

### D02 — Toda modificação de banco deve ser feita por migration Alembic
- **Categoria:** migrations
- **Registrada em:** 2026-04-21
- **Regra:** **Nenhuma** alteração de schema (CREATE/ALTER/DROP TABLE, ADD/DROP COLUMN, índices, tipos ENUM, etc.) pode ser aplicada no banco sem estar acompanhada de uma migration Alembic em `backend/alembic/versions/`. Scripts SQL soltos estão proibidos, exceto para consultas pontuais (SELECT) ou operações de dados explicitamente fora do DDL.
- **Motivação:** Migrations garantem versionamento, rollback, reproducibilidade em múltiplos ambientes (dev/staging/prod) e detecção automática de divergência entre modelo e banco via autogenerate. SQL manual gera schema "invisível" ao Alembic e cria divergências silenciosas (ex.: VARCHAR no banco vs Enum nativo no modelo).
- **Contexto originário:** Após a D01, identificamos que as duas migrations manuais (`001_processamentos_e_reports.sql`, `002_reports_triagem.sql`) haviam introduzido colunas como `VARCHAR` enquanto o modelo SQLAlchemy declarava `Enum`. Isso foi só revelado ao regularizar para Alembic.
- **Aplicação prática:**
  - ✅ Para nova feature: alterar o modelo → `alembic revision --autogenerate -m "..."` → revisar → `alembic upgrade head`.
  - ✅ Para data migrations (ex.: backfill), usar `op.execute("UPDATE ...")` dentro do `upgrade()` da migration.
  - ❌ Proibido: aplicar DDL direto em DBeaver/psql e só depois alinhar com modelo.
  - Antes de qualquer mudança de schema, **verificar** se o modelo e o banco estão alinhados (`alembic current` + `alembic check`).

### D03 — Relatórios de Sprint são responsabilidade do Gerente de Projetos
- **Categoria:** processo
- **Registrada em:** 2026-04-22
- **Regra:** Relatórios de evolução do projeto (a cada 2 semanas) devem ser gerados via `agentes.diretor_geral.GerenteDeProjetos.gerar_relatorio_sprint()`. Não criar relatórios manuais soltos; usar o template padrão em `artefatos/gerente_projetos/template_relatorio_sprint.md`. A estrutura padrão inclui: ✅ Feito, 🎯 Próximo Sprint, 📋 Backlog Pendente, 🚨 Bloqueios, 📈 Métricas.
- **Motivação:** Padronização da comunicação de progresso, rastreabilidade de entregas, e visibilidade clara do que falta vs. o que foi feito. O agente Gerente de Projetos centraliza a gestão ágil e mantém histórico automático.
- **Contexto originário:** Usuário solicitou preparação de apresentação de Sprint e questionou qual agente deveria ser responsável. DiretorGeral foi renomeado para GerenteDeProjetos para refletir melhor seu papel de PO/Scrum Master.
- **Aplicação prática:**
  - ✅ Usar `GerenteDeProjetos().gerar_relatorio_sprint()` preenchendo: `feito`, `proximo_sprint`, `backlog_pendente`, `bloqueios`.
  - ✅ Relatórios ficam em `artefatos/gerente_projetos/` com padrão `relatorio_sprint_NN_YYYYMMDD.md`.
  - ✅ Apresentações a cada 2 semanas devem usar este artefato como base.
  - ❌ Não criar documentos de status soltos em outras pastas sem registro no agente.

---

## Como registrar novas diretrizes

Use o agente `Implementador` em `agentes/implementador.py`:

```python
from agentes.implementador import implementador

implementador.registrar_diretriz(
    titulo="Título curto e imperativo",
    regra="A regra em si, em forma imperativa",
    motivacao="Por que essa regra existe",
    contexto="Episódio real que originou a diretriz",
    categoria="arquitetura | migrations | git | qualidade | ...",
)
```

Ou edite este arquivo manualmente seguindo o padrão `### DNN — Título`.
