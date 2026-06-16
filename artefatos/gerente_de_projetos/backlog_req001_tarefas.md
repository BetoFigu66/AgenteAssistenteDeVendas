# Backlog de Tarefas — REQ-001 (Integração Receita Federal / CNPJ)

**Versão:** 0.1
**Data:** 2026-06-10
**Autor:** Beto (`[gerente]`)
**Base:** `artefatos/requisitos_formais/REQ-001-integracao-receita-federal.md` v1.2

---

## Contexto

- Cada item desta lista vira **uma issue** no GitHub Projects.
- Cobertura atual do REQ-001: **~45%** (validação e consulta básica implementadas; faltam eco/confirmação, política de tentativas com escalonamento e NFRs instrumentadas).
- O que já existe no código: extração de CNPJ via regex + validação algorítmica (`validar_cnpj`), consulta a BrasilAPI, persistência em `Empresa`, fluxo PJ em `_processar_cnpj_fornecido`.

## Legenda de status

| Símbolo | Significado |
|---------|-------------|
| 🟢 | Pronto |
| 🟡 | Parcial |
| 🔴 | Pendente |

## Convenções

- **Subitens REQ**: lista os critérios do REQ-001 cobertos pela tarefa.
- **Validação no painel**: como verificar usando o painel admin (sem WhatsApp).
- **Labels sugeridas**: para aplicar quando virar issue (`tipo:*`, `prio:*`, `area:*`, `REQ-001`).

---

## Mapa de tarefas

| # | Tarefa | Status | Prioridade |
|---|--------|--------|------------|
| T-01 | Eco/confirmação dos dados retornados pela Receita (REQ-001.4) | 🔴 | Alta |
| T-02 | Política de 3 tentativas + escalonamento para humano (REQ-001.6) | 🔴 | Alta |
| T-03 | Tratamento de falhas da API externa com retry interno (REQ-001.10) | 🟡 | Alta |
| T-04 | Distinção entre falha de cliente vs. falha de infraestrutura na contagem de tentativas | 🔴 | Alta |
| T-05 | Instrumentação de NFRs: tempo de resposta, disponibilidade, falhas (REQ-001.8/.9) | 🔴 | Média |
| T-06 | Auditoria de cada tentativa de CNPJ via REQ-005.4 | 🔴 | Média |

---

## T-01 — Eco/confirmação dos dados retornados pela Receita

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-001.4, REQ-001.5
- **Contexto:** Hoje o sistema valida CNPJ e persiste empresa, mas não ecoa os dados para o cliente confirmar antes de prosseguir. O fluxo esperado é: bot mostra razão social + endereço + situação cadastral, cliente responde S/N, sistema avança ou pede correção.
- **Escopo:**
  - Após `_processar_cnpj_fornecido` validar, gerar template `CONFIRMA_DADOS_EMPRESA` com razão social, nome fantasia, endereço, situação, abertura, CNAE principal.
  - Estado de conversa: `aguardando_confirmacao_empresa`.
  - Detectar resposta afirmativa/negativa via classificador (intenções `CONFIRMAR` / `NEGAR`).
  - Em caso de "N", reabrir captura de CNPJ.
  - Em caso de "S", marcar `empresa.confirmada=true` e avançar para qualificação.
- **Validação no painel:**
  - Enviar CNPJ válido → painel mostra a mensagem de confirmação enviada.
  - Cliente responde "Sim" → estado avança; "Não" → loop volta para captura.
- **Dependências:** modelo `Empresa` precisa de flag `confirmada` (ou tabela de auditoria).
- **Branch sugerida:** `feature/REQ-001-eco-confirmacao-empresa`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-001`

## T-02 — Política de 3 tentativas + escalonamento para humano

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-001.6
- **Contexto:** Hoje, CNPJ inválido apenas retorna mensagem genérica sem contador. A política formal é: máximo 3 tentativas por conversa (1 inicial + 2 retentativas). Após esgotar, escalar via REQ-004.9.
- **Escopo:**
  - Contador `tentativas_cnpj` em `NegociacaoInfo` ou na própria `Negociacao`.
  - Mensagem de erro indica motivo específico (formato inválido / não encontrado / situação inativa).
  - 3ª falha → invocar `RECLAMACAO_ESCALADA` / template `ESCALADO_BAIXA_CONFIANCA` com resumo dos CNPJs tentados.
  - Reset do contador ao iniciar nova negociação (telefone novo ou janela de continuação).
- **Validação no painel:**
  - Painel exibe contador atual na conversa.
  - 3 CNPJs inválidos seguidos → mensagem de escalonamento + status `aguardando_humano`.
- **Dependências:** REQ-004 (escalonamento) precisa estar pronto ao menos como template.
- **Branch sugerida:** `feature/REQ-001-politica-tentativas-cnpj`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-001`, `REQ-004`

## T-03 — Tratamento de falhas da API externa com retry interno

- **Status atual:** 🟡 Parcial (consulta básica existe; sem retry estruturado)
- **Subitens REQ:** REQ-001.10
- **Contexto:** `consultar_cnpj` em `services/receita.py` chama BrasilAPI mas não tem retry exponencial nem fallback. Timeouts retornam erro genérico ao cliente.
- **Escopo:**
  - Retry com backoff exponencial (3 tentativas, 1s/2s/4s).
  - Distinguir tipos de erro: timeout, 5xx, 404 (CNPJ não existe), 429 (rate limit).
  - 404 → consumir tentativa do cliente (REQ-001.6).
  - Timeout/5xx/429 → **não** consumir tentativa; após esgotar retry, escalar via REQ-004 com mensagem "consulta indisponível, será revisado manualmente".
  - Considerar API alternativa configurável (receitaws como fallback).
- **Validação no painel:**
  - Simular timeout (mock) → painel mostra retry interno + escalonamento sem consumir tentativa.
  - CNPJ inexistente → consome tentativa normalmente.
- **Dependências:** independente; melhor fazer antes de T-04.
- **Branch sugerida:** `feature/REQ-001-retry-api-receita`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-001`

## T-04 — Distinção falha de cliente vs. falha de infraestrutura na contagem

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-001.6 (regra crítica)
- **Contexto:** Subtarefa de T-02 isolada por ser regra de negócio sensível: falha de infra **não** consome tentativa do cliente.
- **Escopo:**
  - Camada de erro tipado no resultado de `consultar_cnpj`: `{tipo: cliente|infra, motivo: ...}`.
  - `_processar_cnpj_fornecido` só incrementa contador quando `tipo=cliente`.
  - Mensagem de erro distinta: cliente vê "CNPJ não encontrado, confira os números" vs "consulta indisponível no momento, tentando novamente".
- **Validação no painel:**
  - 3 timeouts de API → painel mostra contador ainda em 0 + escalonamento por indisponibilidade.
  - 3 CNPJs com formato inválido → contador chega a 3 + escalonamento por baixa confiança.
- **Dependências:** T-02, T-03.
- **Branch sugerida:** `feature/REQ-001-tipagem-erros-receita`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-001`

## T-05 — Instrumentação de NFRs

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-001.8 (tempo < 3s), REQ-001.9 (disponibilidade > 99%)
- **Contexto:** Não há métricas observáveis para tempo de resposta da Receita nem para taxa de falha.
- **Escopo:**
  - Logar latência de cada consulta CNPJ com timestamp.
  - Endpoint `/api/metrics/req001` ou tabela `MetricasReceita` agregando: total, sucesso, falha (por tipo), p50/p95 de latência.
  - Painel admin: gráfico simples de uso + alertas quando p95 > 3s ou taxa de erro > 1%.
- **Validação no painel:**
  - Nova aba "Métricas REQ-001" no painel mostra contadores agregados das últimas 24h/7d/30d.
- **Dependências:** T-03 (precisamos do tipo de erro padronizado).
- **Branch sugerida:** `feature/REQ-001-metricas-nfr`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-001`, `REQ-005`

## T-06 — Auditoria de cada tentativa de CNPJ (REQ-005.4)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-001.6 (último bullet), REQ-005.4
- **Contexto:** Cada tentativa (CNPJ digitado, resultado, motivo) deve ser registrada como evento na auditoria conforme REQ-005.4. Hoje só fica em `ProcessamentoMensagem`.
- **Escopo:**
  - Criar evento `tentativa_cnpj` em `EventoAuditoria` (ou similar) com: `cnpj`, `resultado` (sucesso/inválido/inativo/erro_infra), `motivo`, `numero_tentativa`, `timestamp`.
  - Persistir antes de responder ao cliente.
  - Endpoint `/api/auditoria/cnpj?telefone=...` retorna histórico.
- **Validação no painel:**
  - Detalhe da conversa mostra timeline de tentativas com resultado.
- **Dependências:** T-02 (contador) + REQ-005 estrutura de eventos.
- **Branch sugerida:** `feature/REQ-001-auditoria-tentativas-cnpj`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-001`, `REQ-005`

---

## Próximos passos

1. Revisar este backlog; ajustar prioridades.
2. Após aprovação, rodar `scripts/criar_issues_req001.ps1` para criar as 6 issues no GitHub Projects (milestone Sprint 03 ou Sprint 04).
3. Vincular ao Project v2 "Assistente de Vendas — Board" e definir Sprint/Estimativa.

## Histórico

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-10 | 0.1 | Criação inicial — 6 tarefas para completar REQ-001 (eco/confirmação, política de tentativas, retry, tipagem de erros, NFRs, auditoria). Base: REQ-001 v1.2 + análise do código atual. | Beto |
