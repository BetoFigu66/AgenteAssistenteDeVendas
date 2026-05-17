# Harness do Agente Implementador

Este documento é o **contrato de conduta** que toda implementação neste repositório deve seguir. Cada diretriz foi acumulada a partir de um episódio real do projeto e permanece ativa até ser revisada explicitamente.

> 🧭 **Regra de ouro:** leia este arquivo antes de implementar qualquer coisa. Se uma situação nova não estiver coberta, **pergunte ao usuário** e registre a decisão como nova diretriz.

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

### D03 — Sprint Review: YAML como fonte única, PPTX derivado
- **Categoria:** processo
- **Registrada em:** 2026-04-22
- **Revisada em:** 2026-04-29
- **Regra:** O Sprint Review (a cada 2 semanas) é composto por dois artefatos gerados pelo `GerenteDeProjetos`:
  1. **`sprint_NN_YYYYMMDD.yaml`** — **fonte única da verdade**, versionado. Gerado por `gerar_dados_sprint_yaml()`. Contém: `feito`, `proximo_sprint`, `backlog_pendente`, `bloqueios`, `metricas`, `insights`.
  2. **`sprint_review_NN_YYYYMMDD.pptx`** — derivado do YAML via `python gera_sprint_report.py`, preenchendo o template `sprint_review_template_v01.pptx` por substituição de tokens `{{...}}`. **Não é versionado** (ver `.gitignore`) e não deve ser editado diretamente exceto para ajustes puramente visuais.
- **Motivação:** Um único formato estruturado elimina retrabalho de copiar dados do `.md` para o `.pptx`. YAML é legível/editável por humano, fácil de revisar em PR. O `.pptx` passa a ser artefato descartável de apresentação, regerado sempre que o YAML mudar.
- **Contexto originário:** A versão anterior gerava um `.md` que depois era copiado manualmente para o `.pptx`. O usuário pediu para automatizar. Decidimos unificar no YAML e eliminar o `.md` para evitar ter duas fontes de verdade.
- **Aplicação prática:**
  - ✅ Fluxo padrão:
    ```python
    gp = GerenteDeProjetos()
    yaml_path = gp.gerar_dados_sprint_yaml(sprint_numero=1, data_inicio=..., data_fim=..., feito=[...], proximo_sprint=[...], backlog_pendente=[...], bloqueios=[...])
    python gera_sprint_report.py
    ```
  - ✅ Editar conteúdo só no YAML; regerar o PPTX.
  - ✅ Tokens aceitos pelo template documentados em `artefatos/gerente_de_projetos/README.md`.
  - ❌ Proibido criar novo `.md` de Sprint Review solto ou editar conteúdo textual direto no PPTX.
  - ❌ Proibido commitar `sprint_review_*.pptx` (exceto templates, que têm `template` no nome).

### D04 — SEMPRE logar stack-trace completa em erros de backend
- **Categoria:** logging / diagnóstico
- **Registrada em:** 2026-04-23
- **Regra:** Toda exceção não tratada ou erro de API (422, 500, etc.) no backend DEVE ter sua stack-trace completa logada no servidor. Não basta logar apenas a mensagem de erro; o traceback completo é obrigatório para diagnóstico efetivo.
- **Motivação:** Erros HTTP (especialmente 422 ValidationError e 500 Internal Server Error) sem stack-trace são impossíveis de diagnosticar em produção. O desenvolvedor precisa saber exatamente qual linha de código gerou a exceção e o caminho de execução completo.
- **Contexto originário:** Endpoint GET /api/negociacoes/ativas retornava 422 sem nenhuma informação de log no servidor, tornando impossível identificar qual campo ou validação estava falhando. Usuário teve que investigar manualmente sem pistas.
- **Aplicação prática:**
  - ✅ Usar exception handlers globais no FastAPI capturando RequestValidationError (422) e Exception (500)
  - ✅ Logar via logging.error() com traceback.format_exc() - linha, arquivo, call stack completa
  - ✅ Incluir informações de contexto: método HTTP, URL, tipo da exceção, mensagem
  - ✅ Verificar implementação de referência em main.py: handlers validation_exception_handler e global_exception_handler
  - ❌ Nunca deixar uma exceção propagar sem logging detalhado, mesmo que retorne resposta amigável ao cliente
  - ❌ Não depender apenas do log do uvicorn (que pode ser superficial); logar explicitamente no handler

### D05 — Rotas estáticas ANTES de rotas dinâmicas no FastAPI
- **Categoria:** fastapi / routing
- **Registrada em:** 2026-04-23
- **Regra:** No FastAPI (Starlette), rotas são matchadas na ordem de declaração. Portanto, rotas com path parameters dinâmicos (`/{id}`) devem sempre ser declaradas DEPOIS de rotas estáticas específicas (`/ativas`, `/stats`, etc.).
- **Motivação:** Se `/api/items/{item_id}` for declarado antes de `/api/items/stats`, uma requisição para `/api/items/stats` vai tentar fazer match com `item_id="stats"`, falhando na validação (ex: int_parsing error 422) ou pior, buscando um ID inexistente.
- **Contexto originário:** Endpoint `/api/negociacoes/ativas` retornava 422 "Input should be a valid integer" porque `/api/negociacoes/{negociacao_id}` (com parâmetro int) estava declarado primeiro, capturando "ativas" como valor do path parameter.
- **Aplicação prática:**
  - ✅ Declarar `/api/negociacoes/ativas` ANTES de `/api/negociacoes/{negociacao_id}`
  - ✅ Usar comentário de seção para indicar ordenação importante (ex: `# Rotas estáticas ANTES de dinâmicas`)
  - ❌ Nunca declarar rotas dinâmicas antes de estáticas no mesmo prefixo
  - ⚠️ Aplicar mesmo padrão para sub-rotas: `/api/users/me` antes de `/api/users/{user_id}`

### D06 — Checks de QA são executáveis e rodam no pre-commit
- **Categoria:** qualidade / processo
- **Registrada em:** 2026-04-29
- **Regra:** Toda regra de qualidade reutilizável e verificável automaticamente deve ser implementada como um `@registrar_check` no `@c:\Beto\Pessoal\Python\git\AgenteAssistenteDeVendas\agentes\qa_engineer.py` e executada via `scripts/qa_check.py`. Severidade `error` **bloqueia** o commit via `pre-commit`; `warning` e `info` apenas alertam.
- **Motivação:** Concentrar as regras verificáveis num único registry torna fácil (1) adicionar novas regras — basta decorar uma função — e (2) rodar as mesmas regras em diferentes momentos do processo (local pre-commit, CI, release). Evita lógica de QA espalhada por scripts ad-hoc.
- **Contexto originário:** Ao longo do projeto surgiram verificações úteis (gitkeep redundantes, imports relativos apontando para arquivos inexistentes, citações `@path` órfãs em `.md`). Sem um ponto único, cada uma virava código solto ou documentação esquecida.
- **Aplicação prática:**
  - ✅ Nova regra verificável → criar função decorada com `@registrar_check(id=..., titulo=..., severidade=..., escopos=[...])` retornando `CheckResult`.
  - ✅ Escopos aceitos: `sempre`, `pre-commit`, `pre-push`, `release`. Escolher com base no custo: pre-commit só checks rápidos (segundos).
  - ✅ Usar `severidade="error"` apenas para problemas que **devem** bloquear commit (ex: import quebrado). Quando em dúvida, usar `warning`.
  - ✅ Setup local obrigatório: `pip install pre-commit && pre-commit install`.
  - ✅ Rodar manualmente: `python scripts/qa_check.py [--escopo X] [--check Y] [--listar]`.
  - ❌ Não criar scripts de verificação fora do registry (fica invisível ao QA Engineer e ao pre-commit).

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
