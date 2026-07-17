# Backlog de Tarefas — REQ-013 (Pares Q&A Curados)

<!-- CLASSIFICACAO: ANDAMENTO -->

**Versão:** 0.1
**Data:** 2026-06-10
**Autor:** Beto (`[gerente]`)
**Base:** `artefatos/requisitos_formais/REQ-013-pares-qa-curados.md` v1.0

---

## Contexto

- Cada item desta lista vira **uma issue** no GitHub Projects.
- Cobertura atual do REQ-013: **~75%** (modelo `ParQA`, endpoints `/api/pares-qa/*`, `QABasePage`, modal de criação por reprovação, lazy embedding e precedência sobre RAG já implementados).
- O que falta: criação a partir de report, filtro por contexto, auditoria do uso, detecção de duplicatas, estatísticas no cabeçalho e persistência da configuração entre reinícios.

## Legenda de status

| Símbolo | Significado |
|---------|-------------|
| 🟢 | Pronto |
| 🟡 | Parcial |
| 🔴 | Pendente |

## Convenções

- **Subitens REQ**: lista os critérios do REQ-013 cobertos pela tarefa.
- **Validação no painel**: como verificar usando o painel admin.
- **Labels sugeridas**: `tipo:*`, `prio:*`, `area:*`, `REQ-013`.

---

## Mapa de tarefas

| # | Tarefa | Status | Prioridade |
|---|--------|--------|------------|
| T-01 | Criação de par Q&A a partir de report (REQ-013.7) | 🔴 | Alta |
| T-02 | Filtro por contexto na busca em produção (REQ-013.12) | 🔴 | Média |
| T-03 | Auditoria de uso de Q&A em ProcessamentoMensagem (REQ-013.14) | 🔴 | Alta |
| T-04 | Detecção de duplicatas na criação (REQ-013.17) | 🔴 | Média |
| T-05 | Estatísticas no cabeçalho da QABasePage (REQ-013.18) | 🔴 | Média |
| T-06 | Persistência de configuração runtime entre reinícios (REQ-013.13) | 🟡 | Média |
| T-07 | Workflow de aprovação com notificação + histórico de revisões (REQ-013.16) | 🟡 | Alta |
| T-08 | Ingestão em lote a partir de pastas/CSV (REQ-013.8) | 🔴 | Baixa |

---

## T-01 — Criação de par Q&A a partir de report (REQ-013.7)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-013.7
- **Contexto:** Hoje só é possível criar par Q&A a partir de mensagem reprovada (REQ-013.6). Falta a integração análoga com a tela de detalhe de report (REQ-012.13), oferecendo a ação quando categoria for `resposta_inadequada` ou `template`.
- **Escopo:**
  - Botão "Criar par Q&A" no detalhe de report nas categorias suportadas.
  - Pré-preenche `pergunta` ← mensagem do cliente do contexto do report.
  - `id_externo` ← `report:<report_id>` para rastrear origem.
  - Após criação, vincular `report_id` ao novo `ParQA` (FK opcional ou referência por `id_externo`).
- **Validação no painel:**
  - Abrir report categoria `resposta_inadequada` → botão visível.
  - Clicar → modal de criação aberto com campos pré-preenchidos.
  - Par criado aparece em `QABasePage` como rascunho com origem do report.
- **Dependências:** REQ-012 (reports) precisa estar acessível.
- **Branch sugerida:** `feature/REQ-013-criar-par-qa-from-report`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-013`, `REQ-012`

## T-02 — Filtro por contexto na busca em produção (REQ-013.12)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-013.12
- **Contexto:** A busca atual em `/api/pares-qa/buscar` não aceita filtro por `contexto`. O REQ pede que o filtro exista como parâmetro opcional, desabilitado por default no POC.
- **Escopo:**
  - Adicionar parâmetro `contexto: str | None` ao endpoint de busca.
  - Filtrar query SQLAlchemy por `ParQA.contexto == contexto` quando informado.
  - Index parcial no Postgres em `pares_qa.contexto` para performance.
  - Documentar uso no swagger.
- **Validação no painel:**
  - Tela admin de debug do RAG aceita filtrar resultado da busca por contexto.
- **Dependências:** independente.
- **Branch sugerida:** `feature/REQ-013-filtro-contexto-busca`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-013`

## T-03 — Auditoria de uso de Q&A em ProcessamentoMensagem (REQ-013.14)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-013.14, REQ-005.6
- **Contexto:** Quando uma resposta é entregue via Q&A curada, `ProcessamentoMensagem` deve registrar o caminho usado, o id do par e o score. Hoje o registro só diz se RAG foi usado.
- **Escopo:**
  - Campos novos em `ProcessamentoMensagem`: `caminho_resposta` (enum `qa_curada` / `rag_documental` / `llm_generico` / `template`), `par_qa_id` (FK opcional), `qa_score`.
  - Atualizar `_decidir_resposta` no processador para gravar esses campos quando aplicável.
  - Migration Alembic para os campos novos.
- **Validação no painel:**
  - Detalhe da mensagem no painel mostra o caminho usado + id do par + score.
- **Dependências:** independente.
- **Branch sugerida:** `feature/REQ-013-auditoria-uso-qa`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-013`, `REQ-005`

## T-04 — Detecção de duplicatas na criação (REQ-013.17)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-013.17
- **Contexto:** Ao criar par novo, sistema não alerta sobre perguntas similares já existentes. Risco de duplicação.
- **Escopo:**
  - No endpoint `POST /api/pares-qa`, antes de gravar, gerar embedding temporário da pergunta e buscar top-3 pares com score ≥ 0.85.
  - Retornar 200 com `duplicatas_candidatas: [...]` quando houver, sem bloquear (alerta apenas).
  - UI exibe modal de confirmação com a lista de candidatos antes de salvar.
- **Validação no painel:**
  - Tentar criar par com pergunta muito similar a um existente → modal de alerta.
- **Dependências:** independente.
- **Branch sugerida:** `feature/REQ-013-deteccao-duplicatas`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-013`

## T-05 — Estatísticas no cabeçalho da QABasePage (REQ-013.18)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-013.18
- **Contexto:** Painel não tem contadores rápidos. Curador precisa rolar a lista para entender o estado da base.
- **Escopo:**
  - Endpoint `GET /api/pares-qa/estatisticas` retorna: total ativos+aprovados, rascunhos pendentes, top N pares mais usados em 7d e 30d (depende de T-03 para popular `par_qa_id` em `ProcessamentoMensagem`).
  - Cabeçalho de `QABasePage` exibe 4 cards com esses números.
- **Validação no painel:**
  - Cabeçalho mostra contadores que atualizam ao aprovar/desativar pares.
- **Dependências:** T-03 (uso histórico).
- **Branch sugerida:** `feature/REQ-013-estatisticas-qabase`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-013`

## T-06 — Persistência de configuração runtime entre reinícios (REQ-013.13)

- **Status atual:** 🟡 Parcial (`/api/config/rag` existe; volátil em memória)
- **Subitens REQ:** REQ-013.13
- **Contexto:** Configuração de `QA_ENABLED` e `QA_SCORE_MINIMO` é volátil; reinício do servidor restaura defaults. Para POC era aceitável, mas começa a incomodar conforme aumenta o volume de ajustes.
- **Escopo:**
  - Tabela `configuracoes_runtime` (chave/valor/tipo/atualizado_em/atualizado_por).
  - Endpoint PATCH `/api/config/rag` persiste no banco.
  - No boot, carregar configurações do banco antes de aceitar requisições.
  - Histórico de alterações em tabela separada (`historico_config`).
- **Validação no painel:**
  - Mudar `QA_SCORE_MINIMO` no painel, reiniciar servidor, valor persiste.
- **Dependências:** REQ-014 (configuração runtime das camadas).
- **Branch sugerida:** `feature/REQ-013-persistir-config-runtime`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-013`, `REQ-014`

## T-07 — Workflow de aprovação com notificação + histórico de revisões

- **Status atual:** 🟡 Parcial (aprovação como toggle simples; sem histórico)
- **Subitens REQ:** REQ-013.16, REQ-013.2
- **Contexto:** Hoje aprovação é um clique no `QABasePage` sem histórico. Para projeto crescer, precisamos saber quem aprovou, quando, e ver revisões/edições.
- **Escopo:**
  - Tabela `revisoes_par_qa` (par_qa_id, ator, acao [criou/editou/aprovou/desativou], snapshot_antes_json, timestamp).
  - Hook nos endpoints PATCH/POST para popular revisões.
  - UI: timeline de revisões no detalhe do par.
  - Notificação (in-app por enquanto) quando rascunho está pendente há mais de 7 dias.
- **Validação no painel:**
  - Editar pergunta de um par → timeline mostra snapshot antes + ator + timestamp.
- **Dependências:** independente, mas idealmente após T-03 (auditoria).
- **Branch sugerida:** `feature/REQ-013-workflow-aprovacao-historico`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-013`, `REQ-005`

## T-08 — Ingestão em lote a partir de pastas/CSV (REQ-013.8)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-013.8
- **Contexto:** Cadastro hoje é só manual por par. Para popular a base rapidamente (catálogo de produtos, FAQs antigas), falta um caminho de ingestão estruturada.
- **Escopo:**
  - Script CLI `scripts/ingerir_pares_qa.py` aceitando markdown / CSV / JSON.
  - Endpoint admin `POST /api/pares-qa/ingestao` para upload via UI.
  - `id_externo` derivado do arquivo (ex: `produto_xyz.md:p3`).
  - Pares ingeridos entram como `aprovado=false`, sem embedding.
  - Tela de revisão em massa com seleção múltipla + ação "aprovar selecionados".
- **Validação no painel:**
  - Subir CSV de 20 perguntas → tabela de revisão com checkboxes; aprovar 5 → embedding gerado, pares entram em produção.
- **Dependências:** T-07 (workflow de aprovação para revisar massa).
- **Branch sugerida:** `feature/REQ-013-ingestao-lote-qa`
- **Labels:** `tipo:feature`, `prio:baixa`, `area:backend`, `area:frontend`, `REQ-013`

---

## Próximos passos

1. Revisar este backlog; ajustar prioridades.
2. Rodar `scripts/criar_issues_req013.ps1` para criar as 8 issues no GitHub Projects.
3. Priorizar para Sprint 03: T-03 (auditoria), T-07 (workflow) e T-01 (criação a partir de report).

## Histórico

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-10 | 0.1 | Criação inicial — 8 tarefas para completar REQ-013 (gaps de criação a partir de report, filtro contexto, auditoria, duplicatas, estatísticas, persistência de config, workflow de aprovação, ingestão em lote). Base: REQ-013 v1.0 + análise do código atual (modelo `ParQA`, endpoints existentes). | Beto |
