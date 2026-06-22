# Proposta de Reorganização das Issues do Board

**Data:** 2026-06-16
**Autor:** `[gerente]` (Cascade)
**Motivação:** Reagrupar tarefas técnicas em funcionalidades entregáveis e testáveis, de forma que cada issue possa ser validada funcionalmente de ponta a ponta quando concluída.

**Critério de agrupamento:** uma issue = uma funcionalidade que o desenvolvedor pode demonstrar funcionando no painel ou via teste automatizado, sem depender de outra issue aberta no mesmo grupo.

---

## REQ-016 — Renomeação Negociação → Atendimento

### Issue REQ-016-F01 — Migração completa do modelo negociação para atendimento

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-016`
**Sprint:** Sprint 03

**Descrição:**
Renomear o conceito de "negociação" para "atendimento" em toda a stack: banco de dados, código Python e interface do usuário. Inclui a migration de rename de tabelas/colunas, a restrição do ciclo de vida do atendimento aos estados `ativo`/`encerrado`, o refactor completo do código Python e as atualizações visuais no frontend.

**Critério de aceite:**
A funcionalidade está pronta quando o painel exibir "Atendimento #N" no lugar de "Negociação", sem regressão visível nas telas principais, e `pytest backend/tests` passar.

**Subtarefas:**
- [ ] **T-A1** — Migration Alembic: rename `negociacoes` → `atendimentos`, colunas e FKs
- [ ] **T-A1b** — Migration Alembic: drop dos estados antigos (`aberta`/`abandonada`/`ganha`/`perdida`) com remapeamento para `ativo`/`encerrado` e coluna `motivo_encerramento`
- [ ] **T-A2** — Refactor Python: models, schemas, services e rotas (`/api/negociacoes/*` → `/api/atendimentos/*`)
- [ ] **T-A11** — Frontend: renomear labels, badges, breadcrumbs e rotas de `/negociacoes/*` → `/atendimentos/*`

**Validação funcional:**
- `alembic upgrade head` e `alembic downgrade -1` rodam limpos
- `grep -ri negocia backend/` retorna zero matches relevantes
- Navegar pelo painel não exibe mais "Negociação" em nenhum label visível

**Branch sugerida:** `feature/migration-rename-atendimentos`

---

### Issue REQ-016-F02 — Criação automática de atendimento com numeração sequencial

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-016`, `REQ-014`
**Sprint:** Sprint 03

**Descrição:**
Centralizar a criação de atendimentos em um serviço dedicado (`services/atendimentos.py`), adicionar rastreamento de timestamp da última mensagem e expor o parâmetro de janela de continuação via configuração de runtime.

**Critério de aceite:**
Telefone novo envia mensagem → painel mostra "Atendimento #1". Segundo atendimento do mesmo telefone → "Atendimento #2". Timestamp da última mensagem atualiza em tempo real.

**Subtarefas:**
- [ ] **T-A3** — Coluna `ultima_mensagem_at` no atendimento + atualização a cada mensagem recebida
- [ ] **T-A4** — Serviço `obter_ou_criar_atendimento_para_mensagem` com numeração sequencial e lock anti-race
- [ ] **T-A8** — Parâmetro `janela_continuacao_atendimento_horas` na tabela de parâmetros (REQ-014.2C)

**Validação funcional:**
- Simulador: telefone novo → Atendimento #1; mesmo telefone → reutiliza
- Alterar `janela_continuacao_atendimento_horas` via endpoint → efeito imediato sem reiniciar

**Branch sugerida:** `feature/criacao-automatica-atendimento`

---

## REQ-016 — Sprint 04

### Issue REQ-016-F03 — Ciclo de vida do atendimento: janela de continuação, encerramento e reabertura

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-016`
**Sprint:** Sprint 04

**Descrição:**
Implementar o ciclo de vida completo do atendimento: detecção automática de continuação por janela de tempo, encerramento explícito com pergunta de fechamento e reabertura de atendimentos encerrados.

**Critério de aceite:**
Um atendimento encerrado pode ser reaberto quando o cliente retorna dentro da janela configurada. Fora da janela, um novo atendimento é criado automaticamente.

**Subtarefas:**
- [ ] **T-A5** — Janela de continuação: verificar `ultima_mensagem_at` vs. `janela_continuacao_atendimento_horas` ao receber nova mensagem de contato com atendimento encerrado
- [ ] **T-A6** — Encerramento explícito: pergunta de fechamento ao operador + motivo de encerramento
- [ ] **T-A7** — Reabertura de atendimento encerrado dentro da janela + atualização de `ultima_mensagem_at`

**Validação funcional:**
- Atendimento encerrado há 2h + janela de 24h + nova mensagem → reabre o mesmo atendimento
- Atendimento encerrado há 48h + janela de 24h + nova mensagem → cria novo atendimento

**Branch sugerida:** `feature/ciclo-vida-atendimento`

---

### Issue REQ-016-F04 — Painel e auditoria de atendimentos

**Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-016`, `REQ-005`
**Sprint:** Sprint 04

**Descrição:**
Exibir o atendimento com identificação "Atendimento #N" no painel, expor ações de encerrar/reabrir e registrar eventos de auditoria do ciclo de vida.

**Critério de aceite:**
Painel exibe "Atendimento #N" no cabeçalho da conversa. Operador pode encerrar ou reabrir via botão. Cada transição gera evento de auditoria visível na timeline.

**Subtarefas:**
- [ ] **T-A9** — Painel: exibição "Atendimento #N" + botões encerrar/reabrir na tela da conversa
- [ ] **T-A10** — Eventos de auditoria de atendimento em REQ-005.4 (ativo→encerrado, encerrado→ativo)
- [ ] **T-A12** — Cenários de teste manual no QA Runner para o ciclo de vida de atendimento

**Validação funcional:**
- Encerrar atendimento via painel → evento de auditoria aparece na timeline
- QA Runner carrega os cenários de T-A12 e todos passam

**Branch sugerida:** `feature/painel-auditoria-atendimentos`

---

## REQ-001 — Integração Receita Federal (CNPJ)

### Issue REQ-001-F01 — Captura e confirmação de CNPJ com política de tentativas

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-001`, `REQ-004`
**Sprint:** Sprint 03

**Descrição:**
Completar o fluxo de identificação via CNPJ: ecoar os dados retornados pela Receita para confirmação do cliente, aplicar política de 3 tentativas com distinção de falha do cliente vs. falha de infraestrutura, e escalar automaticamente ao esgotar as tentativas.

**Critério de aceite:**
CNPJ válido → bot exibe razão social e pergunta confirmação. 3 CNPJs inválidos consecutivos → escalonamento para humano. Timeout da API não consome tentativa do cliente.

**Subtarefas:**
- [ ] **T-01** — Eco e confirmação dos dados retornados pela Receita (template `CONFIRMA_DADOS_EMPRESA`, estado `aguardando_confirmacao_empresa`)
- [ ] **T-02** — Política de 3 tentativas + escalonamento via REQ-004.9 ao esgotar
- [ ] **T-03** — Retry com backoff exponencial na chamada à API da Receita (3 tentativas: 1s/2s/4s), com fallback para API alternativa
- [ ] **T-04** — Tipagem de erros: `tipo: cliente | infra` para garantir que falha de infra não consome tentativa do cliente

**Validação funcional:**
- CNPJ válido → tela de confirmação; cliente confirma → avança para qualificação
- Simular timeout (mock) → contador de tentativas do cliente permanece em 0
- 3 CNPJs inválidos → status `aguardando_humano` no painel

**Branch sugerida:** `feature/REQ-001-captura-cnpj-completo`

---

### Issue REQ-001-F02 — Auditoria e métricas da consulta CNPJ

**Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-001`, `REQ-005`
**Sprint:** Sprint 03

**Descrição:**
Registrar evento de auditoria para cada tentativa de CNPJ e instrumentar métricas de latência e disponibilidade da consulta à Receita Federal.

**Critério de aceite:**
Detalhe da conversa no painel exibe timeline de tentativas de CNPJ com resultado. Aba de métricas mostra contadores agregados das últimas 24h/7d/30d.

**Subtarefas:**
- [ ] **T-05** — Instrumentação de NFRs: log de latência, endpoint `/api/metrics/req001`, alertas quando p95 > 3s ou taxa de erro > 1%
- [ ] **T-06** — Evento `tentativa_cnpj` em `EventoAuditoria` com CNPJ, resultado, motivo, número da tentativa e timestamp

**Validação funcional:**
- Aba `Métricas REQ-001` exibe contadores reais
- Timeline da conversa mostra cada tentativa de CNPJ com resultado

**Branch sugerida:** `feature/REQ-001-auditoria-metricas`

---

## REQ-002 — Fluxo Conversacional Guiado

### Issue REQ-002-F01 — Classificador com categorias e fallback para RAG

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`, `REQ-003`
**Sprint:** Sprint 03

**Descrição:**
Adicionar o campo `categoria` (1–4) ao classificador, consumir limiares de REQ-014 em vez de valores fixos, e implementar fallback condicional para Q&A/RAG quando a confiança for baixa, além de tratamento de mensagens compostas.

**Critério de aceite:**
Painel exibe categoria e nível de confiança no detalhe da mensagem. Mensagem com confiança baixa consulta a base RAG antes de devolver fallback genérico. Mensagem composta (resposta + pergunta embutida) registra ambas corretamente.

**Subtarefas:**
- [ ] **T-01** — Adicionar `categoria` (1–4) e `justificativa_curta` ao `ResultadoClassificacao`; adaptar `_decidir_resposta` para rotear por categoria; consumir limiares de REQ-014
- [ ] **T-02** — Fallback condicional ao REQ-003 quando `confianca_nivel = baixa` (Caso 2) + tratamento de mensagem composta com pergunta embutida (Caso 3)

**Validação funcional:**
- `Quais produtos a Inforrel vende?` com classificador hesitante → resposta da base RAG (não fallback genérico)
- `5, mas vocês têm modelo com biometria facial?` → registra `quantidade=5` E responde sobre facial

**Branch sugerida:** `feature/classificador-categorias-fallback`

---

### Issue REQ-002-F02 — Identificação PF/PJ e roteamento antes da qualificação

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`
**Sprint:** Sprint 03

**Descrição:**
Permitir que o cliente faça perguntas sobre produto/empresa antes de fornecer documento fiscal (criando contato anônimo), inferir automaticamente se é PF ou PJ, e rotear para o fluxo correto de captura de documento.

**Critério de aceite:**
Telefone novo pergunta sobre produto sem fornecer CNPJ/CPF → painel mostra contato anônimo + resposta da base. Quando fornece CNPJ posteriormente → contato é promovido com histórico preservado.

**Subtarefas:**
- [ ] **T-03** — Roteamento pré-identificação: criar contato anônimo quando categoria 3 com confiança alta e sem documento fiscal
- [ ] **T-04** — Inferência PF/PJ a partir da mensagem inicial; pergunta dirigida quando ambíguo; troca de tipo no meio da conversa

**Validação funcional:**
- `Quais relógios de ponto vocês vendem?` de número novo → contato anônimo no painel + resposta
- Em mensagem seguinte, fornece CNPJ → contato promovido, conversa anterior preservada
- `Quero orçamento para minha casa` → pergunta PF ou PJ

**Branch sugerida:** `feature/identificacao-pf-pj-roteamento`

---

### Issue REQ-002-F03 — Qualificação adaptativa completa do atendimento

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-002`
**Sprint:** Sprint 04

**Descrição:**
Implementar o motor de qualificação completo: catálogo de campos por tipo de cliente, perguntas dinâmicas baseadas no estado atual, captura de tipo/modelo/dados adicionais/endereço, validações, eco consolidado e tratamento de ambiguidade com retry e RAG durante a qualificação.

**Critério de aceite:**
Mensagem rica inicial (`orçamento de catraca biometrica para 10 pessoas em SP`) preenche múltiplos campos de uma vez. Painel mostra lista de campos com status. Ao final, sumarização completa é apresentada antes de encaminhar para orçamento.

**Subtarefas:**
- [ ] **T-05** — Catálogo canônico de campos por tipo de cliente (PF/PJ) + serviço `proxima_pergunta(atendimento)` + integração no processador
- [ ] **T-06** — Captura adaptativa: tipo de produto (T-06.1), modelo (T-06.2), dados adicionais (T-06.3), endereço (T-06.4)
- [ ] **T-07** — Validações de respostas capturadas: CPF, e-mail, telefone, modelo, endereço, quantidade
- [ ] **T-08** — Eco consolidado de dados extraídos (REQ-002.16) + sumarização final da qualificação (REQ-002.5)
- [ ] **T-09** — Tratamento de ambiguidade: contador de tentativas por campo, reformulação dirigida, escalonamento após esgotar, retomada do RAG sem consumir tentativa

**Validação funcional:**
- Painel mostra status de cada campo (capturado / pendente / não-aplicável)
- `Qual a diferença entre biométrico e facial?` no meio do fluxo → resposta + retomada da pergunta anterior
- Resposta inválida (CPF errado) → mensagem de esclarecimento; 3 falhas → escalonamento

**Branch sugerida:** `feature/qualificacao-adaptativa-completa`

---

### Issue REQ-002-F04 — Abandono de conversa, reengajamento e integração WhatsApp

**Labels:** `tipo:feature`, `prio:baixa`, `area:backend`, `area:infra`, `area:integracao`, `REQ-002`, `REQ-008`
**Sprint:** Sprint 04

**Descrição:**
Detectar abandono por inatividade, enviar mensagem de reengajamento e, após maturidade do painel, validar todos os comportamentos do REQ-002 no canal real do WhatsApp.

**Critério de aceite:**
Inatividade de 24h → mensagem de reengajamento enviada. Após 72h sem resposta → atendimento finalizado com motivo `abandono`. Issue de integração WhatsApp só vai para "In Progress" quando T-01 a T-09 estiverem Done.

**Subtarefas:**
- [ ] **T-10** — Job/scheduler de detecção de inatividade 24h, mensagem única de reengajamento, finalização após 72h e retomada de contexto em nova conversa
- [ ] **T-11** — Integração Twilio/Meta Cloud API + validação de comportamentos REQ-002 no canal real + ajustes de UX WhatsApp (limites de caracteres, listas, mídia)

**Validação funcional:**
- Simular inatividade de 24h (botão dev ou ajuste de timestamp) → mensagem de reengajamento
- Canal WhatsApp real: enviar 4 mensagens-tipo e conferir roteamento por categoria

**Branch sugerida:** `feature/abandono-reengajamento-whatsapp`

---

## REQ-013 — Pares Q&A Curados

### Issue REQ-013-F01 — Curadoria e workflow de aprovação

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-013`, `REQ-012`, `REQ-005`
**Sprint:** Sprint 03

**Descrição:**
Completar o ciclo de curadoria de pares Q&A: criação a partir de reports de problema, alerta de duplicatas antes de salvar e histórico completo de revisões com notificação de rascunhos pendentes.

**Critério de aceite:**
Report de categoria `resposta_inadequada` exibe botão "Criar par Q&A" com campos pré-preenchidos. Tentativa de criar par com pergunta similar exibe modal de alerta. Editar um par gera entrada na timeline de revisões.

**Subtarefas:**
- [ ] **T-01** — Botão "Criar par Q&A" no detalhe de report (categorias `resposta_inadequada` e `template`) com pré-preenchimento
- [ ] **T-04** — Detecção de duplicatas na criação: busca de similaridade (score ≥ 0.85) antes de salvar, com modal de confirmação
- [ ] **T-07** — Tabela `revisoes_par_qa` com histórico de edições + notificação in-app de rascunhos pendentes há mais de 7 dias

**Validação funcional:**
- Abrir report `resposta_inadequada` → botão visível; clicar → modal pré-preenchido
- Criar par com pergunta similar → modal de alerta com candidatos
- Editar pergunta → timeline mostra snapshot antes + ator + timestamp

**Branch sugerida:** `feature/REQ-013-curadoria-workflow-aprovacao`

---

### Issue REQ-013-F02 — Busca, auditoria e estatísticas da base Q&A

**Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-013`, `REQ-005`
**Sprint:** Sprint 03

**Descrição:**
Adicionar filtro por contexto na busca, registrar o caminho de cada resposta (Q&A curada vs. RAG vs. LLM) em `ProcessamentoMensagem` e exibir estatísticas de uso no cabeçalho da tela de gestão.

**Critério de aceite:**
Detalhe de mensagem no painel exibe qual caminho de resposta foi usado e o ID do par Q&A quando aplicável. Cabeçalho da tela Q&A exibe 4 cards de contadores (total ativos, rascunhos, mais usados 7d/30d).

**Subtarefas:**
- [ ] **T-02** — Parâmetro `contexto` opcional no endpoint de busca Q&A com index parcial no Postgres
- [ ] **T-03** — Campos `caminho_resposta`, `par_qa_id` e `qa_score` em `ProcessamentoMensagem` + migration Alembic
- [ ] **T-05** — Endpoint `GET /api/pares-qa/estatisticas` + 4 cards de contadores no cabeçalho de `QABasePage`

**Validação funcional:**
- Detalhe da mensagem mostra `qa_curada | ID: 42 | score: 0.91`
- Aprovar/desativar par → contadores atualizam imediatamente

**Branch sugerida:** `feature/REQ-013-busca-auditoria-estatisticas`

---

### Issue REQ-013-F03 — Configuração persistente e ingestão em lote

**Labels:** `tipo:feature`, `prio:media`, `area:backend`, `area:frontend`, `REQ-013`, `REQ-014`
**Sprint:** Sprint 04

**Descrição:**
Persistir as configurações de runtime do RAG (QA_ENABLED, QA_SCORE_MINIMO) entre reinicializações e permitir ingestão em lote de pares Q&A a partir de CSV/Markdown.

**Critério de aceite:**
Alterar `QA_SCORE_MINIMO` via painel, reiniciar servidor → valor persiste. Upload de CSV com 20 perguntas → tela de revisão em massa com checkboxes; aprovar selecionados → embeddings gerados.

**Subtarefas:**
- [ ] **T-06** — Tabela `configuracoes_runtime` + persistência no banco + histórico de alterações; PATCH `/api/config/rag` persiste; boot carrega antes de aceitar requisições
- [ ] **T-08** — Script `scripts/ingerir_pares_qa.py` (markdown/CSV/JSON) + endpoint admin `POST /api/pares-qa/ingestao` + tela de revisão em massa com seleção múltipla

**Validação funcional:**
- Mudar `QA_SCORE_MINIMO`, reiniciar servidor → valor persiste
- Subir CSV de 20 perguntas → tabela de revisão com checkboxes; aprovar 5 → embedding gerado

**Branch sugerida:** `feature/REQ-013-config-persistente-ingestao-lote`

---

## REQ-015 — Validação de CPF e Consulta de Débitos

> **Nota:** As issues do REQ-015 seguem o mesmo padrão das demais. As 9 tarefas originais (T-01 a T-09) ficam agrupadas em 3 issues funcionais abaixo.

### Issue REQ-015-F01 — Captura e confirmação de CPF com política de tentativas

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-015`, `REQ-004`
**Sprint:** Sprint 03

**Subtarefas:**
- [ ] **T-01** — Eco e confirmação do CPF capturado (análogo ao REQ-001 T-01)
- [ ] **T-02** — Política de 3 tentativas + escalonamento para CPF inválido
- [ ] **T-03** — Tratamento de PF que recusa fornecer CPF: prosseguir com campos independentes e escalar antes de finalizar orçamento

**Validação funcional:**
- CPF válido → confirmação; 3 CPFs inválidos → escalonamento
- Cliente recusa CPF → campos de nome/endereço ainda são coletados antes de escalar

**Branch sugerida:** `feature/REQ-015-captura-cpf-completo`

---

### Issue REQ-015-F02 — Consulta de débitos e tratamento de restrição

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-015`, `REQ-004`, `REQ-010`
**Sprint:** Sprint 04

**Subtarefas:**
- [ ] **T-04** — Decisão e integração do provedor de consulta de débitos (Serasa/SPC/Boa Vista/Quod)
- [ ] **T-05** — Tratamento de restrição financeira: registrar, sinalizar no painel e escalar (não negar automaticamente — LGPD art. 20)
- [ ] **T-08** — Sinalização visual de restrição no painel sem expor CPF completo

**Validação funcional:**
- CPF com restrição → painel exibe badge de alerta + escalonamento; CPF não aparece em texto pleno

**Branch sugerida:** `feature/REQ-015-consulta-debitos-restricao`

---

### Issue REQ-015-F03 — LGPD, auditoria e reuso de CPF

**Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-015`, `REQ-005`
**Sprint:** Sprint 04

**Subtarefas:**
- [ ] **T-06** — Mascaramento de CPF em logs, modal de raciocínio e auditoria (LGPD art. 20)
- [ ] **T-07** — Evento de auditoria por consulta de débitos com CPF mascarado
- [ ] **T-09** — Reuso de CPF já validado em conversas futuras do mesmo telefone

**Validação funcional:**
- CPF não aparece em texto pleno em nenhum log ou tela do painel
- Cliente que já validou CPF em conversa anterior não precisa fornecer novamente

**Branch sugerida:** `feature/REQ-015-lgpd-auditoria-reuso-cpf`

---

## Resumo

| Issue | REQ | Sprint | Subtarefas agrupadas | Testável isoladamente? |
|-------|-----|--------|----------------------|------------------------|
| REQ-016-F01 | REQ-016 | 03 | T-A1 + T-A1b + T-A2 + T-A11 | ✅ Sim — painel sem "Negociação" |
| REQ-016-F02 | REQ-016 | 03 | T-A3 + T-A4 + T-A8 | ✅ Sim — Atendimento #N visível |
| REQ-016-F03 | REQ-016 | 04 | T-A5 + T-A6 + T-A7 | ✅ Sim — ciclo de vida testável |
| REQ-016-F04 | REQ-016 | 04 | T-A9 + T-A10 + T-A12 | ✅ Sim — painel + auditoria |
| REQ-001-F01 | REQ-001 | 03 | T-01 a T-04 | ✅ Sim — fluxo CNPJ completo |
| REQ-001-F02 | REQ-001 | 03 | T-05 + T-06 | ✅ Sim — métricas visíveis |
| REQ-002-F01 | REQ-002 | 03 | T-01 + T-02 | ✅ Sim — classificador funcional |
| REQ-002-F02 | REQ-002 | 03 | T-03 + T-04 | ✅ Sim — fluxo PF/PJ |
| REQ-002-F03 | REQ-002 | 04 | T-05 a T-09 | ✅ Sim — qualificação completa |
| REQ-002-F04 | REQ-002 | 04 | T-10 + T-11 | ✅ Sim — abandono + WhatsApp |
| REQ-013-F01 | REQ-013 | 03 | T-01 + T-04 + T-07 | ✅ Sim — curadoria funcional |
| REQ-013-F02 | REQ-013 | 03 | T-02 + T-03 + T-05 | ✅ Sim — busca + auditoria |
| REQ-013-F03 | REQ-013 | 04 | T-06 + T-08 | ✅ Sim — config + ingestão |
| REQ-015-F01 | REQ-015 | 03 | T-01 a T-03 | ✅ Sim — fluxo CPF completo |
| REQ-015-F02 | REQ-015 | 04 | T-04 + T-05 + T-08 | ✅ Sim — restrição visível |
| REQ-015-F03 | REQ-015 | 04 | T-06 + T-07 + T-09 | ✅ Sim — LGPD + auditoria |

**Total: 16 issues** (vs. 38 originais) — cada uma entregável e validável de forma independente.
