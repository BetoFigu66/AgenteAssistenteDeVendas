# Backlog de Tarefas — REQ-016 (Atendimentos) + Renomeação Negociação→Atendimento

<!-- CLASSIFICACAO: HISTORICO -->

**Versão:** 0.1 (rascunho para revisão da Kika)
**Data:** 2026-06-09
**Autor:** Beto (`[gerente]`)
**Base:** `artefatos/requisitos_formais/REQ-016-identificacao-numeracao-atendimentos.md` v2.0 + `artefatos/analista_de_requisitos/analise_renomeacao_negociacao_para_atendimento.md` v0.2

---

## Contexto

- REQ-016 v2.0 redefine o conceito: **Atendimento** substitui **Negociação**, com ciclo de vida simplificado (`ativo`/`encerrado`) e continuidade controlada pelo cliente (pergunta de continuação após janela configurável).
- Esta é uma mudança **transversal**: toca em modelo de dados, classificador, processador, gerador de respostas, painel admin e migrations.
- Estratégia: **uma migration Alembic de rename atômico** (T-A1) seguida das adaptações de domínio (T-A2 a T-A8). Sem fase de coexistência — o termo "negociação" sai do código em uma única passada.
- Validação: cada tarefa tem critério de aceite verificável no **painel administrativo (REQ-010)**, sem depender de WhatsApp.

## Legenda de status

| Símbolo | Significado |
|---------|-------------|
| 🟢 | Pronto — base equivalente existe, falta só renomear/ajustar |
| 🟡 | Parcial — código atual cobre parte, falta evoluir |
| 🔴 | Pendente — feature nova sem precedente no código |

## Convenções

- **Subitens REQ**: critérios do REQ-016 v2.0 cobertos pela tarefa.
- **Validação no painel**: como verificar usando o painel admin.
- **Labels sugeridas**: `tipo:*`, `prio:*`, `area:*`, `REQ-016`.
- **Branch**: nome descritivo sem ID (política v1.1). ID do REQ vai na mensagem de commit.

---

## Mapa de tarefas

| # | Tarefa | Status | Prioridade |
|---|--------|--------|------------|
| T-A1 | Migration Alembic: rename de tabelas, colunas e FKs `negociacoes`→`atendimentos` | 🟢 | Alta |
| T-A1b | Migration Alembic: drop dos estados antigos com remapeamento (`aberta`/`abandonada`→`ativo`; `ganha`/`perdida`→`encerrado`) | 🟡 | Alta |
| T-A2 | Refactor de models, schemas e serviços (Python) com o novo vocabulário | 🟢 | Alta |
| T-A3 | Coluna `ultima_mensagem_at` + atualização em cada mensagem | 🟡 | Alta |
| T-A4 | Lógica de criação automática de atendimento integrada ao classificador | 🟡 | Alta |
| T-A5 | Janela de continuação + pergunta de continuação (REQ-016.7 / REQ-016.9) | 🔴 | Alta |
| T-A6 | Encerramento explícito + pergunta de fechamento (REQ-016.4 / REQ-016.10) | 🔴 | Alta |
| T-A7 | Reabertura de atendimento encerrado (REQ-016.8) | 🔴 | Média |
| T-A8 | Parâmetro `janela_continuacao_atendimento_horas` em `parametros` (REQ-014.2C) | 🔴 | Alta |
| T-A9 | Painel: exibição "Atendimento #N" + ações encerrar/reabrir (REQ-010 v1.3) | 🔴 | Alta |
| T-A10 | Eventos de auditoria de atendimento em REQ-005.4 | 🔴 | Média |
| T-A11 | Renomeações de UI no frontend (labels, badges, breadcrumbs) | 🟡 | Média |
| T-A12 | Cenários de teste manual no QA Runner para o novo ciclo de vida | 🔴 | Média |

---

## T-A1 — Migration Alembic: rename de tabelas, colunas e FKs

- **Status atual:** 🟢 Pronto (rename mecânico)
- **Subitens REQ:** REQ-016.1 a REQ-016.5 (modelo de dados implícito), §7 do REQ-016.
- **Escopo:**
  - Tabelas: `negociacoes` → `atendimentos`; `negociacao_infos` → `atendimento_infos`.
  - Colunas FK em `orcamentos`, `conversas`, `mensagens`, `atendimento_infos`: `negociacao_id` → `atendimento_id`.
  - Coluna interna em `atendimentos`: `numero_negociacao_cliente` → `numero_atendimento_cliente`.
  - Índices renomeados (`ix_negociacoes_*` → `ix_atendimentos_*`).
  - Index único composto `(contato_id, numero_atendimento_cliente)` preservado.
  - **Downgrade**: rename reverso completo (sem perda de dados).
  - **Não cobre** a alteração do domínio de `status` nem a coluna `motivo_encerramento` — isso fica isolado em T-A1b para reduzir risco e permitir revisão de uma migration por vez.
- **Validação:**
  - `alembic upgrade head` e `alembic downgrade -1` rodam limpos em base local.
  - `SELECT COUNT(*)` antes e depois bate (sem perda de linhas).
  - Foreign keys validadas com `\d+ atendimentos` no psql.
- **Dependências:** nenhuma — é a primeira tarefa.
- **Risco:** baixo — apenas rename. POC ainda não tem dados em produção.
- **Labels:** `tipo:task`, `prio:alta`, `area:backend`, `area:db`, `REQ-016`

## T-A1b — Migration Alembic: drop dos estados antigos com remapeamento

- **Status atual:** 🟡 Parcial (estados antigos existem; novos não)
- **Subitens REQ:** REQ-016.4 (ciclo de vida `ativo`/`encerrado`), REQ-006 v1.8 (ganha/perdida ficam exclusivamente no orçamento).
- **Contexto:** O modelo antigo mantinha estados `aberta`/`abandonada`/`ganha`/`perdida` na própria nego (agora atendimento). REQ-016 v2.0 colapsa para `ativo`/`encerrado`; desfecho comercial migra para o orçamento (REQ-006 v1.8).
- **Escopo:**
  - Migration Alembic separada (depois de T-A1) que:
    - Restringe a coluna `status` em `atendimentos` ao conjunto `{ativo, encerrado}`.
    - Adiciona coluna `motivo_encerramento` (string nullable) em `atendimentos`.
    - Remapeia os valores existentes em uma **única transação**:
      - `aberta` → `ativo`, `motivo_encerramento = NULL`
      - `abandonada` → `encerrado`, `motivo_encerramento = inatividade`
      - `ganha` → `encerrado`, `motivo_encerramento = ganha_legado` (com auditoria de que existe pelo menos um orçamento `convertido` no atendimento; se não houver, registrar warning estruturado mas não falhar)
      - `perdida` → `encerrado`, `motivo_encerramento = perdida_legado` (análogo, esperando `perdido` em algum orçamento)
    - Aplica `CHECK constraint` em `status` (apenas `ativo`/`encerrado`) e em `motivo_encerramento` (apenas os valores definidos em REQ-016.4 + os dois `_legado`).
  - **Downgrade**: restaurar domínio antigo (`aberta`, `abandonada`, `ganha`, `perdida`) e reverter o remapeamento usando `motivo_encerramento` como pista; valores legados (`ganha_legado`/`perdida_legado`) viram `ganha`/`perdida` respectivamente; `inatividade` vira `abandonada`.
  - Auditoria: registrar no log da migration o **contador** de linhas por transição (`N atendimentos aberta→ativo`, etc.) para facilitar diagnóstico pós-deploy.
- **Validação:**
  - `alembic upgrade head` em base com dados sintéticos representando cada estado antigo → distribuição final contém apenas `ativo`/`encerrado` e `motivo_encerramento` esperados.
  - `alembic downgrade -1` restaura o conjunto original sem perda.
  - Query de sanity: nenhum atendimento em `encerrado` sem `motivo_encerramento` preenchido (exceto durante a janela transitória da própria migration).
- **Dependências:** T-A1.
- **Risco:** médio — é a migration que **muda semântica**. Mesmo no POC, queremos preservar o que está hoje na base local de dev para não perder cenários manuais. Por isso é issue separada de T-A1 (cada uma com seu PR).
- **Coordenação com REQ-006:** O orçamento mantém seu `status` (`rascunho`/`enviado`/`convertido`/`perdido`) inalterado — esta migration **não** mexe em `orcamentos`. A conferência de consistência (orcamentos.status vs atendimentos.motivo_encerramento) é apenas auditoria, não regra de negócio impositiva.
- **Labels:** `tipo:task`, `prio:alta`, `area:backend`, `area:db`, `REQ-016`, `REQ-006`

## T-A2 — Refactor de models, schemas e serviços (Python)

- **Status atual:** 🟢 Pronto (rename mecânico em código)
- **Subitens REQ:** transversal — sustenta T-A3 em diante.
- **Escopo:**
  - `backend/models.py`: `Negociacao` → `Atendimento`, `NegociacaoInfo` → `AtendimentoInfo`, atributos `negociacao_id` → `atendimento_id`, relacionamentos `negociacao` → `atendimento`.
  - `backend/services/processador.py`: variáveis locais e funções (`identificar_negociacao` → `identificar_atendimento`, `negociacao_atual` → `atendimento_atual`, etc.).
  - `backend/services/classificador.py`: payloads de retorno, comentários, docstrings.
  - `backend/services/respostas/gerador.py` e `templates.py`: tokens `{numero_negociacao}` → `{numero_atendimento}` quando existirem, ajustes de texto.
  - Schemas Pydantic (`schemas/`): renomear classes `NegociacaoOut` → `AtendimentoOut` etc., e rotas onde forem expostas.
  - Endpoints: `/api/negociacoes/*` → `/api/atendimentos/*` (sem manter rota antiga — POC).
  - Testes unitários e fixtures atualizados.
- **Validação:**
  - `pytest backend/tests` passa.
  - `grep -ri negocia backend/` retorna **zero** matches relevantes (exceto comentários históricos explícitos, se houver).
- **Dependências:** T-A1 e T-A1b (o model precisa refletir o domínio final, com `motivo_encerramento`).
- **Labels:** `tipo:task`, `prio:alta`, `area:backend`, `REQ-016`

## T-A3 — Coluna `ultima_mensagem_at` + atualização em cada mensagem

- **Status atual:** 🟡 Parcial (timestamp de mensagem existe; coluna no atendimento não)
- **Subitens REQ:** REQ-016.7 (precisa do timestamp para calcular janela).
- **Escopo:**
  - Adicionar coluna `ultima_mensagem_at` em `atendimentos` (migration própria ou incluída em T-A1).
  - No `processador.py`, ao receber cada mensagem do cliente, atualizar `atendimento.ultima_mensagem_at = now()`.
  - Ao reabrir um atendimento (T-A7), atualizar também.
- **Validação no painel:**
  - Painel mostra timestamp da última mensagem na lista de atendimentos do cliente.
  - Enviar nova mensagem pelo simulador → timestamp atualiza imediatamente.
- **Dependências:** T-A1, T-A2.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-016`

## T-A4 — Lógica de criação automática de atendimento

- **Status atual:** 🟡 Parcial (cria negociação implicitamente hoje, com lógica difusa)
- **Subitens REQ:** REQ-016.6.
- **Escopo:**
  - Centralizar criação em `services/atendimentos.py` (novo): função `obter_ou_criar_atendimento_para_mensagem(contato, mensagem)`.
  - Regras de criação:
    - Se contato é novo → criar atendimento ativo.
    - Se contato tem atendimento `ativo` → reutilizar.
    - Se contato tem apenas atendimentos `encerrado` → ver T-A5 (continuação automática vs. pergunta).
  - Numeração: `numero_atendimento_cliente = MAX(numero_atendimento_cliente) + 1` para o contato (com lock para evitar race).
- **Validação no painel:**
  - Telefone novo envia mensagem → aparece `Atendimento #1` no painel.
  - Segundo atendimento do mesmo telefone → `#2`, e por diante.
- **Dependências:** T-A1, T-A2.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-016`

## T-A5 — Janela de continuação + pergunta de continuação

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-016.7, REQ-016.9, REQ-016.18.
- **Escopo:**
  - Ler `janela_continuacao_atendimento_horas` (T-A8) no momento da chegada da mensagem.
  - Se `now() - ultima_mensagem_at(atendimento_encerrado_mais_recente) <= janela`: reabrir automaticamente (mesmo número), registrar evento.
  - Se `> janela`: gerar **pergunta de continuação** ("Você quer continuar o Atendimento #N que tivemos em <data>, ou abrir um novo?").
  - Classificar a resposta do cliente:
    - Afirmativa → reabrir o atendimento anterior (T-A7).
    - Negativa → criar atendimento novo (T-A4).
    - Ambígua → assumir default configurável (default: novo) e registrar para auditoria.
  - O processador deve segurar o tratamento da mensagem original do cliente até essa decisão ser tomada (uma mensagem da pergunta + uma da resposta do cliente).
- **Validação no painel:**
  - Simulador permite "envelhecer" um atendimento encerrado (mover `ultima_mensagem_at` para o passado) e disparar nova mensagem para validar os dois caminhos (dentro/fora da janela).
- **Dependências:** T-A1, T-A2, T-A4, T-A7, T-A8.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-016`

## T-A6 — Encerramento explícito + pergunta de fechamento

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-016.4, REQ-016.10.
- **Escopo:**
  - Detectar sinais de fim de atendimento (cliente diz "obrigado", "era só isso", "ok", e/ou orçamento enviado + N minutos de silêncio configurável).
  - Sistema envia **pergunta de fechamento** ("Posso encerrar este atendimento?").
  - Conforme resposta:
    - Sim → `status = encerrado`, `motivo_encerramento = cliente_confirmou`, registrar evento.
    - Não/ambígua → mantém `ativo`.
  - Encerramento também pode ser disparado pelo painel (T-A9): `motivo_encerramento = encerrado_pelo_vendedor`.
  - Encerramento por inatividade prolongada (REQ-002.22): `motivo_encerramento = inatividade`.
- **Validação no painel:**
  - Cenário scriptado de "obrigado, era isso" deve gerar pergunta de fechamento; resposta afirmativa encerra o atendimento e o painel reflete imediatamente.
- **Dependências:** T-A1, T-A2, T-A4.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-016`

## T-A7 — Reabertura de atendimento encerrado

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-016.8.
- **Escopo:**
  - Função `reabrir_atendimento(atendimento_id, ator)` em `services/atendimentos.py`.
  - Reabertura automática quando T-A5 detectar continuação dentro da janela.
  - Reabertura manual via painel (T-A9), com registro de quem reabriu.
  - Evento `atendimento_reaberto` em REQ-005.4 com autoria e timestamp.
  - Limpar `motivo_encerramento` ao reabrir.
- **Validação no painel:**
  - Encerrar um atendimento, depois reabrir manualmente: status volta para `ativo`, evento aparece no histórico.
- **Dependências:** T-A1, T-A2, T-A6.
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-016`

## T-A8 — Parâmetro `janela_continuacao_atendimento_horas`

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-016.18, REQ-014.2C.
- **Escopo:**
  - Seed na tabela `parametros` com `nome=janela_continuacao_atendimento_horas`, `valor=24`, descrição.
  - Validação: inteiro ≥ 1.
  - Expor no `GET /api/config/rag` (ou endpoint dedicado conforme REQ-014.5).
  - `ParametroService` já existente: garantir leitura imediata (sem cache de longo prazo).
- **Validação no painel:**
  - Alterar valor para 1h via painel de configuração, esperar 1h+5min e validar que sistema pergunta continuação.
- **Dependências:** independente; pode ser feita em paralelo a T-A5.
- **Labels:** `tipo:task`, `prio:alta`, `area:backend`, `REQ-016`, `REQ-014`

## T-A9 — Painel: exibição "Atendimento #N" + ações encerrar/reabrir

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-016.14, REQ-016.15, REQ-016.8 (parte manual), REQ-010 v1.3.
- **Escopo:**
  - Cabeçalho da tela de chat exibe `Atendimento #N` (REQ-010.7A).
  - Lista de atendimentos do cliente (com status e datas) na ficha do contato.
  - Botões **Encerrar atendimento** (com seletor de motivo) e **Reabrir atendimento**.
  - Lista de orçamentos do atendimento (link cruzado REQ-006).
  - Filtro por atendimento na busca de mensagens (REQ-011.17A).
- **Validação no painel:**
  - Acionar encerramento/reabertura pelo painel reflete no banco e gera evento auditável.
- **Dependências:** T-A2, T-A6, T-A7.
- **Labels:** `tipo:feature`, `prio:alta`, `area:frontend`, `REQ-016`, `REQ-010`

## T-A10 — Eventos de auditoria de atendimento (REQ-005.4)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-005.4 (v1.10) + REQ-016.4/.6/.8/.9/.10.
- **Escopo:**
  - Adicionar tipos de evento: `atendimento_criado`, `atendimento_encerrado` (payload com `motivo_encerramento`), `atendimento_reaberto` (payload com `ator` e timestamp).
  - Registrar também as perguntas de continuação (T-A5) e fechamento (T-A6), com resposta classificada.
  - Evento aparece no timeline de auditoria do painel.
- **Validação no painel:**
  - Cada transição de atendimento gera evento visível no histórico da conversa.
- **Dependências:** T-A4, T-A5, T-A6, T-A7.
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-016`, `REQ-005`

## T-A11 — Renomeações de UI no frontend

- **Status atual:** 🟡 Parcial (alguns componentes ainda dizem "Negociação")
- **Subitens REQ:** REQ-010 v1.3 (decorrente do rename).
- **Escopo:**
  - Substituir labels visíveis: "Negociação" → "Atendimento", "Nova negociação" → "Novo atendimento", "Nº negociação" → "Nº atendimento", etc.
  - Atualizar chaves de tradução (se houver), ícones e tooltips.
  - Atualizar rotas do frontend: `/negociacoes/*` → `/atendimentos/*`.
  - Atualizar testes e snapshots.
- **Validação:**
  - Busca por "Negocia" no frontend retorna apenas comentários históricos.
  - Lighthouse/acessibilidade sem regressão.
- **Dependências:** T-A2 (endpoints renomeados).
- **Labels:** `tipo:task`, `prio:media`, `area:frontend`, `REQ-016`

## T-A12 — Cenários de teste manual no QA Runner

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** transversal — valida T-A4 a T-A7 e T-A9.
- **Escopo:**
  - Criar cenários em `artefatos/qa/cenarios_manuais/`:
    - **CTF-016-01** — Primeiro atendimento do telefone (criação automática, número 1).
    - **CTF-016-02** — Segundo atendimento (incremento sequencial).
    - **CTF-016-03** — Continuação automática dentro da janela.
    - **CTF-016-04** — Pergunta de continuação fora da janela (resposta afirmativa).
    - **CTF-016-05** — Pergunta de continuação fora da janela (resposta negativa).
    - **CTF-016-06** — Encerramento explícito após "obrigado, era só isso".
    - **CTF-016-07** — Reabertura manual pelo painel.
    - **CTF-016-08** — Alteração do parâmetro `janela_continuacao_atendimento_horas` em runtime.
  - Cada cenário com passos, dados de entrada, resultado esperado e ponto de captura de evidência.
- **Validação:**
  - QA Runner executa os 8 cenários e gera relatório.
- **Dependências:** T-A4 em diante (pelo menos os cenários correspondentes).
- **Labels:** `tipo:task`, `prio:media`, `area:qa`, `REQ-016`

---

## Sequenciamento sugerido

```
T-A1 ──► T-A1b ──► T-A2 ──┬──► T-A3 ──► T-A4 ──► T-A6 ──► T-A7 ──► T-A5 ──► T-A10
                          │                                  ▲
                          │                                  │
                          └──► T-A8 ──────────────────────────┘
                          │
                          └──► T-A11 (frontend) ───────────► T-A9 ───────► T-A12
```

- **Sprint 03 mínimo viável:** T-A1, T-A1b, T-A2, T-A3, T-A4, T-A8, T-A11 (rename + remapeamento de estados + numeração + parâmetro + UI). Pergunta de continuação fica para um segundo PR para reduzir risco.
- **Sprint 04:** T-A5, T-A6, T-A7, T-A9, T-A10, T-A12.

## Itens não-funcionais cobertos transversalmente

- **Auditoria** (REQ-005.4 v1.10): T-A10.
- **Configurabilidade** (REQ-014.2C v1.2): T-A8.
- **Compatibilidade com REQ-006** (ganha/perdida ficam no orçamento, não no atendimento): coberto por T-A1b (drop dos estados antigos) e validado em T-A12.

## Fora do escopo desta lista

- **REQ-002** (fluxo conversacional) — tem backlog próprio (`backlog_req002_tarefas.md`), atualizado para usar "atendimento".
- **REQ-008 (WhatsApp)** — fora; validação real no canal vem depois.
- **Lógica de detecção de "obrigado/era isso"** (T-A6): a heurística inicial é simples (palavras-chave); refinamento via LLM fica para sprint futura.

---

## Próximos passos

1. **Kika revisa** este documento e marca o que ajustar (granularidade, prioridade, ordem).
2. Após aprovação, gerar **`scripts/criar_issues_req016.ps1`** com `gh issue create` para cada tarefa.
3. Vincular issues ao Project "Assistente de Vendas — Board" e ao milestone Sprint 03.

## Histórico

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-09 | 0.1 | Criação inicial — 12 tarefas para a Fase 3 da renomeação Negociação→Atendimento (migration + refactor + novo ciclo de vida + parâmetro + UI + QA). Sequenciamento sugerido para 2 sprints. | Beto |
| 2026-06-09 | 0.2 | Split de T-A1 em T-A1 (rename mecânico, baixo risco) e T-A1b (drop/remapeamento de estados antigos, risco médio) para permitir PRs e revisões independentes. Sequenciamento e Sprint 03 atualizados. | Beto |
