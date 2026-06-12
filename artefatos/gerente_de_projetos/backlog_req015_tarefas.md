# Backlog de Tarefas — REQ-015 (Validação de CPF e Consulta de Débitos)

**Versão:** 0.1
**Data:** 2026-06-10
**Autor:** Beto (`[gerente]`)
**Base:** `artefatos/requisitos_formais/REQ-015-validacao-cpf-consulta-debitos.md` v1.0

---

## Contexto

- Cada item desta lista vira **uma issue** no GitHub Projects.
- Cobertura atual do REQ-015: **~50%** (validação algorítmica de CPF, captura no fluxo PF, persistência em `Pessoa` com `tipo_documento=CPF`, integração básica com REQ-002 já implementadas).
- O que falta: consulta a provedor externo de débitos, eco/confirmação do CPF, tratamento de restrição com escalonamento, tratamento LGPD (mascaramento, finalidade, retenção), auditoria das consultas.

## Legenda de status

| Símbolo | Significado |
|---------|-------------|
| 🟢 | Pronto |
| 🟡 | Parcial |
| 🔴 | Pendente |

## Convenções

- **Subitens REQ**: lista os critérios do REQ-015 cobertos pela tarefa.
- **Validação no painel**: como verificar usando o painel admin.
- **Labels sugeridas**: `tipo:*`, `prio:*`, `area:*`, `REQ-015`.

---

## Mapa de tarefas

| # | Tarefa | Status | Prioridade |
|---|--------|--------|------------|
| T-01 | Eco/confirmação do CPF capturado (REQ-015.4) | 🔴 | Alta |
| T-02 | Política de 3 tentativas + escalonamento para CPF inválido (REQ-015.6) | 🔴 | Alta |
| T-03 | Tratamento de PF que recusa fornecer CPF (REQ-015.8) | 🔴 | Alta |
| T-04 | Decisão e integração do provedor de consulta de débitos (REQ-015.3) | 🔴 | Alta |
| T-05 | Tratamento de restrição financeira com escalonamento humano (REQ-015.7) | 🔴 | Alta |
| T-06 | Tratamento LGPD do CPF: mascaramento, finalidade, retenção (REQ-015.13) | 🔴 | Alta |
| T-07 | Auditoria das consultas de débito (REQ-015.14) | 🔴 | Média |
| T-08 | Sinalização visual de restrição no painel (REQ-010 + REQ-015.5) | 🔴 | Média |
| T-09 | Reuso de CPF já validado em conversas futuras (REQ-015.10) | 🟡 | Média |

---

## T-01 — Eco/confirmação do CPF capturado

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.4
- **Contexto:** Sistema valida CPF e persiste, mas não ecoa para confirmação (S/N). Igual à T-01 do REQ-001 mas para CPF.
- **Escopo:**
  - Após `_processar_cpf_fornecido` validar, gerar template `CONFIRMA_CPF` exibindo CPF formatado.
  - Estado `aguardando_confirmacao_cpf`.
  - Em "N", reabrir captura; em "S", marcar `pessoa.confirmado=true` e avançar.
- **Validação no painel:**
  - CPF válido → mensagem de confirmação enviada.
  - Cliente "Sim" → avança; "Não" → loop.
- **Dependências:** modelo `Pessoa` precisa de flag `confirmado`.
- **Branch sugerida:** `feature/REQ-015-eco-confirmacao-cpf`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-015`

## T-02 — Política de 3 tentativas + escalonamento para CPF inválido

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.6
- **Contexto:** Mesma política do REQ-001.6 aplicada a CPF. Máximo 3 tentativas; após esgotar, escalar para humano com resumo dos CPFs tentados.
- **Escopo:**
  - Contador `tentativas_cpf` em `NegociacaoInfo` ou `Negociacao`.
  - Mensagem de erro indicando motivo (formato / dígitos verificadores / sequência trivial).
  - 3ª falha → escalonamento via REQ-004.9 com resumo (CPFs **mascarados** no log).
  - Reset do contador ao iniciar nova negociação.
- **Validação no painel:**
  - 3 CPFs inválidos → mensagem de escalonamento + status `aguardando_humano`.
- **Dependências:** REQ-004 (escalonamento), T-06 (mascaramento).
- **Branch sugerida:** `feature/REQ-015-politica-tentativas-cpf`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-015`, `REQ-004`

## T-03 — Tratamento de PF que recusa fornecer CPF

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.8
- **Contexto:** Se cliente PF não quiser ou não souber informar CPF, sistema deve prosseguir coletando os campos não dependentes (nome, telefone, endereço de instalação). Antes de finalizar orçamento, escalar para humano com o registro.
- **Escopo:**
  - Detectar recusa ou silêncio na coleta de CPF (intenção `RECUSAR_CPF` ou ausência após 2 perguntas).
  - Marcar negociação com `cpf_pendente=true`, `motivo='cliente_nao_forneceu'`.
  - Prosseguir qualificação sem CPF.
  - Antes de gerar orçamento, status muda para `aguardando_revisao_humana` com motivo registrado.
  - Limite de 2 insistências para coletar (depois respeita recusa).
- **Validação no painel:**
  - Conversa simulada onde cliente diz "não vou passar CPF agora" → sistema segue, gera negociação com flag `cpf_pendente`.
- **Dependências:** REQ-004 (escalonamento).
- **Branch sugerida:** `feature/REQ-015-recusa-cpf`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-015`, `REQ-004`

## T-04 — Decisão e integração do provedor de consulta de débitos

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.3
- **Contexto:** Marcado como `[PENDENTE: definir provedor]` no REQ. Provedores candidatos: Serasa Experian, SPC Brasil, Boa Vista (Equifax), Quod. Decisão depende de custo, cobertura, contrato. Sem essa decisão, nada do fluxo "consulta de débitos" avança.
- **Escopo:**
  - Levantar com `[planejador]` custo por consulta e cobertura dos 4 provedores.
  - Validar com Rita (Inforrel) qual é viável.
  - Implementar `services/debitos.py` com interface `ConsultorDebitos` e factory.
  - Mock local para desenvolvimento (sem chamar provedor real).
  - Documentar credenciais em `.env.example`.
- **Validação no painel:**
  - Em ambiente dev, mock retorna restrição configurável.
  - Em prod (futuro), provedor real é chamado via factory.
- **Dependências:** ADR do `[planejador]` + `[arquiteto]`.
- **Branch sugerida:** `feature/REQ-015-provedor-debitos-decisao`
- **Labels:** `tipo:task`, `prio:alta`, `area:backend`, `area:negocio`, `REQ-015`

## T-05 — Tratamento de restrição financeira com escalonamento humano

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.7
- **Contexto:** Quando consulta retorna restrição, sistema **não** nega automaticamente (LGPD art. 20); registra, sinaliza no painel e escala para revisão humana antes de finalizar orçamento.
- **Escopo:**
  - Após `consultar_debitos`, registrar `restricao_financeira` em `NegociacaoInfo` com `valor` agregado (sim/não + ocorrências + score).
  - **Nunca** mencionar a restrição ao cliente.
  - Continuar qualificação normalmente.
  - No momento de gerar orçamento (final do fluxo), se `restricao_financeira=sim`, mudar status para `aguardando_revisao_humana` com motivo `restricao_financeira`.
  - Vendedor decide pelo painel se procede, pede pagamento antecipado, recusa, etc.
- **Validação no painel:**
  - Mock retorna restrição → conversa continua sem revelar; painel mostra badge.
  - Ao gerar orçamento → status muda para revisão humana com motivo claro.
- **Dependências:** T-04, T-08 (sinalização visual), REQ-004.
- **Branch sugerida:** `feature/REQ-015-tratamento-restricao`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-015`, `REQ-004`

## T-06 — Tratamento LGPD do CPF (mascaramento, finalidade, retenção)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.13
- **Contexto:** REQ explícito sobre LGPD. Hoje CPF aparece em texto pleno em logs, modal de raciocínio e auditoria — risco real.
- **Escopo:**
  - Função utilitária `mascarar_cpf(cpf)` → `***.456.789-**`.
  - Logs, `ProcessamentoMensagem`, eventos de auditoria (REQ-005) e reports (REQ-012) usam CPF mascarado.
  - CPF completo só em telas de cadastro de cliente e detalhe de orçamento (acesso restrito).
  - Texto de finalidade exibido ao cliente na primeira solicitação de CPF da conversa: "Usamos seu CPF apenas para elaborar o orçamento e verificar pendências financeiras com nossos parceiros de crédito."
  - Job de anonimização periódica para CPFs sem relação comercial ativa há mais de N meses (configurável; default 24 meses).
  - Endpoint `DELETE /api/clientes/{telefone}/dados-pessoais` para atendimento manual de pedido de exclusão.
  - Bloquear indexação de CPF pelo RAG (REQ-003).
- **Validação no painel:**
  - Painel admin nunca mostra CPF completo fora da tela de detalhe do cliente.
  - Modal de raciocínio (REQ-005.6) mostra CPF mascarado.
- **Dependências:** REQ-005 (auditoria), REQ-003 (RAG indexação).
- **Branch sugerida:** `feature/REQ-015-lgpd-cpf`
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-015`, `REQ-005`

## T-07 — Auditoria das consultas de débito

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.14
- **Contexto:** Cada consulta de débitos deve gerar evento de auditoria com CPF mascarado, provedor, resultado agregado, data/hora. Não persistir resultado completo em texto pleno.
- **Escopo:**
  - Tabela `auditoria_consulta_debitos` (cpf_mascarado, provedor, resultado_agregado_json, identificador_transacao, criado_em, criado_por).
  - Hook em `services/debitos.py` para popular após cada consulta.
  - Endpoint `/api/auditoria/debitos?cnpj_consultor=...` (acesso restrito).
- **Validação no painel:**
  - Tela admin "Auditoria de Consultas" lista as consultas com CPF mascarado.
- **Dependências:** T-04 (provedor), T-06 (mascaramento), REQ-005.
- **Branch sugerida:** `feature/REQ-015-auditoria-debitos`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-015`, `REQ-005`

## T-08 — Sinalização visual de restrição no painel

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-015.5, REQ-015.7, REQ-010
- **Contexto:** Painel precisa destacar conversas/negociações onde o CPF tem restrição, sem expor o CPF completo.
- **Escopo:**
  - Badge `⚠️ Restrição Financeira` no card de conversa e no detalhe da negociação.
  - Tooltip explicando o que significa.
  - Filtro na listagem por "com restrição / sem restrição / pendente / indisponível".
- **Validação no painel:**
  - Negociações com `restricao_financeira=sim` mostram badge em vermelho.
- **Dependências:** T-04, T-05.
- **Branch sugerida:** `feature/REQ-015-sinalizacao-restricao-painel`
- **Labels:** `tipo:feature`, `prio:media`, `area:frontend`, `REQ-015`, `REQ-010`

## T-09 — Reuso de CPF já validado em conversas futuras

- **Status atual:** 🟡 Parcial (`Pessoa` é persistida; falta a lógica de reuso explícita)
- **Subitens REQ:** REQ-015.10
- **Contexto:** Se cliente já validou CPF em conversa anterior (mesmo telefone), não pedir de novo. Análogo a REQ-002.10 para CNPJ.
- **Escopo:**
  - Ao iniciar nova negociação para telefone com `Pessoa` já validada, herdar CPF automaticamente.
  - Se cliente mencionar CPF diferente, perguntar antes de trocar (template `CONFIRMA_TROCA_CPF`).
  - Se cliente pedir explicitamente troca, executar.
- **Validação no painel:**
  - 2ª conversa do mesmo telefone PF → não pede CPF de novo.
  - Cliente envia CPF diferente → sistema confirma antes de gravar.
- **Dependências:** modelo `Pessoa` (já existe).
- **Branch sugerida:** `feature/REQ-015-reuso-cpf-validado`
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-015`

---

## Próximos passos

1. Revisar este backlog; ajustar prioridades.
2. **Crítico antes de avançar:** T-04 depende de decisão de provedor (envolvendo `[planejador]` + Rita).
3. Rodar `scripts/criar_issues_req015.ps1` para criar as 9 issues no GitHub Projects.
4. Priorizar para Sprint 03: T-01 (eco), T-02 (tentativas), T-06 (LGPD) — independentes da decisão do provedor.

## Histórico

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-10 | 0.1 | Criação inicial — 9 tarefas para completar REQ-015 (eco, política de tentativas, recusa de CPF, decisão de provedor de débitos, tratamento de restrição, LGPD, auditoria, sinalização no painel, reuso). Base: REQ-015 v1.0 + análise do código (validação algorítmica + fluxo PF já implementados). | Beto |
