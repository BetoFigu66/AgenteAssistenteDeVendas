# CLAUDE.md

<!-- CLASSIFICACAO: IA -->
<!-- CLASSIFICACAO: SISTEMA-DEV -->

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

WhatsApp sales-assistant AI system for Inforrel (sells access-control turnstiles/time clocks). Currently POC/single-tenant stage for one client (Rita/Ivan). Backend in Python (FastAPI + SQLAlchemy + PostgreSQL/pgvector), frontend in React. Documentation and commit messages are in **Portuguese** — keep new docs/comments in Portuguese too.

## Commands

### Backend (from `backend/`)

```bash
# venv setup (WSL/Linux)
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# run dev server (reload) — dev uses 8001, docker/QA uses 8000
uvicorn main:app --host 0.0.0.0 --port 8001 --reload   # or ./run.sh
python main.py                                          # simpler alternative

# migrations (Alembic) — also auto-applied on app startup (lifespan in main.py)
alembic upgrade head
alembic revision --autogenerate -m "descricao"

# tests (pytest, from backend/ with venv active)
pytest
pytest tests/test_cpf.py
pytest tests/test_cpf.py::test_validar_cpf -v
```

### Frontend (from `frontend/`)

```bash
npm install
npm run dev       # http://localhost:5173 (or 3001 in the two-env dev setup), proxies /api to backend
npm run build
npm run lint
```

### Full stack (Docker)

```bash
docker-compose up --build     # postgres (pgvector/pgvector:pg16) + backend:8000 + frontend:3000
docker-compose up -d postgres # only the DB, e.g. to run backend/frontend natively against it
```
Postgres exposed on host port **5433** (container `inforrel_postgres`, db `assistente_vendas`, user/pass `inforrel`/`inforrel_dev`).

### QA / lint (run from repo root)

```bash
ruff check .                 # lint (config in pyproject.toml)
ruff check --fix .
python scripts/qa_check.py --listar          # list registered QA checks
python scripts/qa_check.py                   # run all
python scripts/qa_check.py --escopo pre-commit
pre-commit run --all-files
```
QA checks are registered via `@registrar_check` in `agentes/qa_engineer.py`. The pre-commit hook (`scripts/run_qa_check_precommit.sh`) locates the Python interpreter in `backend/venv` for both Windows and WSL — `pre-commit install` must be run from the **same environment** (WSL or PowerShell) used for `git commit`.

Full command reference (env setup gotchas, Cloudflare tunnel, DBeaver connection, RAG ingestion scripts, etc.) lives in `docs/comandos_uteis.md` — check it before proposing an environment/tooling fix, and add new recurring tips there.

## Architecture

### The "cérebro" (message processing pipeline)

The core of the system is `backend/services/processador.py::ProcessadorMensagem.processar()`, invoked from both `POST /webhook` (Twilio) and `POST /api/mensagem` (web UI) in `backend/main.py`. Pipeline per inbound message:

1. Persist inbound `Mensagem` (origem=USER).
2. **Identify** sender by phone (`services/identificador.py`) → contact/company/person, or `NOVO`/`SEM_EMPRESA`/`MULTIPLO` status.
3. **Classify** intent + extract entities (`services/classificador.py`) — CNPJ/CPF, product types, quantities, names, dates — via rules first, LLM as fallback/enrichment.
4. If the active `Atendimento` (deal/case) is in `ModoOperacao.HUMANO`, skip response generation entirely — a human operator replies through the UI (`POST /api/atendimentos/{id}/mensagens-manuais`).
5. Otherwise route by identification status + intent in `_decidir_resposta`/`_gerar_resposta_por_intencao`: escalate to human, handle CNPJ/CPF flows (`services/cnpj/`, `services/cpf/`), or generate a reply.
6. Reply generation layers, in priority order: curated **Q&A pairs** (`services/rag/qa_service.py`) → vector **RAG** over product docs (`services/rag/retrieval.py`, pgvector) → static **templates** (`services/respostas/`) optionally personalized via LLM.
7. Every decision is persisted to `ProcessamentoMensagem` for audit (intent, confidence, entities, RAG/QA trace, tokens, latency) — this is the source of truth for debugging "why did the bot answer X".
8. Outbound `Mensagem` (origem=SYSTEM) is created. Whether it starts pre-approved or requires human approval before being considered "sent" depends on the **modo de execução** — see below (`ModoExecucao.EXECUCAO_NORMAL` self-approves; `SIMULACAO`/`CONVERSA_CONTROLADA` leave `aprovador_id`/`timestamp_aprovacao` NULL until a human calls `/api/mensagens/{id}/aprovar|reprovar`, a `reprovar` creating a `ReportProblema`).

### Modos de execução e aprovação (REQ-011)

Two **orthogonal** axes control whether/how an AI-generated reply reaches the customer — don't conflate them:

- **`ModoExecucao`** (global system setting, `models/parametro.py`, read via `ParametroService.modo_execucao()`, changed via `PATCH /api/config/execucao`): `SIMULACAO` / `CONVERSA_CONTROLADA` (both require human approval before send — `services/processador.py` leaves `aprovador_id` NULL) vs. `EXECUCAO_NORMAL` (system self-approves as soon as the reply is generated — `processador.py` sets `aprovador_id` to a system user — and the reply goes out **synchronously** inside the Twilio webhook's TwiML response, `main.py::webhook_twilio`). See `artefatos/requisitos_formais/REQ-011-modos-execucao-aprovacao-mensagens.md`.
- **`ModoOperacao`** (per-`Atendimento`, step 4 above): `AGENTE` vs `HUMANO`. `HUMANO` suppresses AI generation entirely, in **any** `ModoExecucao` (REQ-011.14/REQ-004.10) — this is the "no message is generated at all" case, not to be confused with `SIMULACAO`/`CONVERSA_CONTROLADA` (which do generate, just hold for approval).

### Canal de saída (REQ-008, Fase 10)

A **third, orthogonal axis**, and the one that decides whether anything actually reaches a customer: `CANAL_SAIDA` in `.env` (`services/canal/`, factory like `llm`/`embeddings`).

- `simulado` (default): nothing is delivered. Messages are persisted and shown in the UI, which is exactly what the system always did — now declared instead of implicit.
- `twilio`: real delivery. `TWILIO_MODO_ENVIO` picks how the webhook's *synchronous* reply goes out — `twiml` (the only one a trial/Sandbox account accepts; the outbound SID arrives later via `statusCallback` on `POST /webhook/status`) or `rest` (SID immediately, paid account required).

It lives in `.env` and not in the `parametros` table on purpose: flipping `ModoExecucao` in the panel must never, by itself, start messaging real customers. All three delivery points (approval `POST /api/mensagens/{id}/aprovar`, manual reply `POST /api/atendimentos/{id}/mensagens-manuais`, and the webhook's `rest` path) go through `services/envio.py::entregar_mensagem`, which records the outcome on the `Mensagem` (`timestamp_envio`, `erro_envio`, `message_sid`). **A delivery failure never fails the approval** — the human decision is persisted and the reason it didn't go out is recorded (the concrete case is WhatsApp's 24h window, Twilio error 63016).

`/webhook` distinguishes a real Twilio call from a local one by the presence of `AccountSid` (the `testador_conversas` and the web simulator only send `From`/`Body`): local calls always get the text back in the TwiML, which is how those tools read replies, and with `CANAL_SAIDA=simulado` a real Twilio call gets an empty TwiML.

### Reply-to: "this message answers that one"

`Mensagem.resposta_a_mensagem_id` (self-FK) is fed by two paths that converge on one column: WhatsApp's `OriginalRepliedMessageSid` (resolved through `Mensagem.message_sid`, which only exists once the `statusCallback` landed) and the web UI's own "Responder" button (`resposta_a_mensagem_id` in `POST /api/mensagem`). Both are filtered by the conversation's phone number in `ProcessadorMensagem._resolver_resposta_a`. `resposta_a_message_sid` keeps the raw SID even when it doesn't resolve, which is what distinguishes "quoted nothing" from "quoted something we don't know". This is tiebreaker (0) of the planned pilha de perguntas pendentes.

Providers are pluggable via factories: `services/llm/factory.py` (`LLM_PROVIDER`, currently Groq) and `services/embeddings/factory.py` (`EMBEDDING_PROVIDER`, currently OpenAI). All feature toggles (`RAG_ENABLED`, `QA_ENABLED`, thresholds like `RAG_SCORE_MINIMO`) are in `backend/config.py` (`Settings`, pydantic-settings from `.env`) and some are additionally tunable at runtime without restart via `PATCH /api/config/rag` and the `parametros` table (`services/parametro_service.py`, `PATCH /api/parametros/{nome}`).

### Domain model (`backend/models/`)

Package with one module per domain area (`atendimento.py`, `mensagem.py`, `empresa.py`, `catalogo.py`, `report.py`, etc.); `models/__init__.py` re-exports every entity so `from models import X` keeps working everywhere — import that way, not from the submodule, unless you're inside the package itself. Portuguese table/entity names. Key entities: `Contato` (WhatsApp contact) → `Empresa` (CNPJ, for PJ) or `Pessoa` (CPF, for PF) → `Atendimento` (a case/deal, has `status` ATIVO/ENCERRADO and `modo_operacao` AGENTE/HUMANO) → `Mensagem` (chat messages, linked to `ProcessamentoMensagem`) → `ReportProblema` (QA triage report, created when a message is rejected or manually flagged) → `Orcamento`/`ItemNegociacao`/`AtendimentoInfo` (quote/collected-info state). `documentos_conhecimento` (pgvector) backs the RAG; `pares_qa` backs the curated Q&A layer (see `backend/routers/pares_qa.py`).

Timestamps are stored UTC (`timestamptz`, `utils/datetime_utils.py::utc_now`/`serialize_utc_datetime`) and displayed in America/Sao_Paulo in the frontend.

### Frontend

React (Vite, TailwindCSS) SPA in `frontend/src/`. `services/api.js` talks to the backend; Vite dev server proxies `/api/*` (see `vite.config.js` / `VITE_DEV_API_PROXY`). Main screens: `AcompanhamentoPage` (active-case triage, ordered by pending approvals), `ChatArea`/`Message`/`PhonePanel` (conversation view + manual reply + approve/reject), `ReportsPage`/`ReportDetalhe` (problem-report queue), `ParametrosPage`, `QABasePage`. Inforrel brand colors are defined in `tailwind.config.js` (primary `#1B4F72`, secondary `#2E86AB`, accent `#F39C12`) — reuse them, don't hardcode new colors.

### Dev-team "agents" system (`agentes/`, `artefatos/`, `AGENTS.md`)

Separate from the product: this repo also hosts a set of role-play prompts used to structure work with Claude/Cursor/Windsurf. A message prefixed `[nome]` (e.g. `[implementador]`, `[qa]`, `[arquiteto]`) tells the assistant to adopt that persona's tone/scope and save artifacts under `artefatos/<agente>/`. Full routing table and conventions are in `AGENTS.md` — read it before acting on a bracket-prefixed request or when unsure which artifact directory to use. Most agents are pure prompt files (`agentes/<nome>.md`); a few also have executable Python (`agentes/*.py`, all built on `agentes/base_agente.py::BaseAgente`).

`AnotacoesPessoais/` is a per-collaborator scratch area, gitignored except its `README.md` — never put real client data or secrets there, and never treat its contents as authoritative project documentation.

### Testador de conversas (`testador_conversas/`)

Separate system (own venv, own CLI) that exercises the real backend end-to-end like an actual WhatsApp user would — sends messages via `POST /webhook` (same form-encoded shape Twilio uses) and reads the synchronous TwiML reply. It sends no `AccountSid`, which is precisely how `/webhook` knows the call is local and always returns the text in the TwiML, whatever `CANAL_SAIDA` says (see "Canal de saída" above). Its own Postgres schema (`teste_conversas`, same DB server as `assistente_vendas`) is the source of truth for scenarios/turns and for the accumulated catalog of accepted responses (`respostas_aceitas` — a turn can have several, since accepted phrasing evolves); a response not matching any accepted one pauses the run for a human accept/reject decision (`cli.py rodar <cenario>`), not a fully automated pass/fail gate. `cli.py exportar` snapshots scenarios+accepted responses to YAML under `cenarios_exportados/`, committed to git as versioned history/backup — not the source of truth. See `testador_conversas/README.md` for setup/usage.

## Business rules (enforced in generated responses)

- Never promise a delivery deadline (`Intencao.PERGUNTAR_PRAZO` always routes to a non-committal template).
- Always defer system-compatibility questions to technical validation rather than answering definitively.
- Escalate to a human whenever the customer asks for one, or on a complaint (`Intencao.ESCALAR_HUMANO`/`RECLAMAR`).

## Working conventions

- Backend: SQLAlchemy for all DB access (no raw psycopg outside `services/`), Alembic for schema changes — never hand-edit the schema.
- Route ordering in `main.py` matters: static routes (e.g. `/api/atendimentos/ativas`) must be declared before dynamic ones (`/api/atendimentos/{atendimento_id}`).
- `LOG_LEVEL` defaults to WARNING; SQL statements only log with `SQL_ECHO=true`.
