# Backlog de Tarefas — REQ-002 (Fluxo Conversacional)

<!-- CLASSIFICACAO: ANDAMENTO -->

**Versão:** 0.3 (revisão pós-análise de código)
**Data:** 2026-06-10
**Autor:** Beto (`[gerente]`)
**Base:** `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` v1.25 + REQ-016 v2.0

---

## Contexto

- Cada item desta lista vira **uma issue** no GitHub Projects.
- Granularidade: agrupada por tema; subitens grandes ganham issue própria.
- **Canal de teste:** painel administrativo (REQ-010). **Sem integração WhatsApp** nesta fase — todo teste de conversa é simulado pelo painel (envio manual de mensagens do "cliente" e visualização das respostas do sistema).
- A integração com WhatsApp foi consolidada em **uma única tarefa agregadora** (T-11), que depende da maturidade dos demais itens.

## Legenda de status

| Símbolo | Significado |
|---------|-------------|
| 🟢 | Pronto — validação + ajustes finos no painel |
| 🟡 | Parcial — base no código, falta completar |
| 🔴 | Pendente — não há nada implementado |

## Convenções

- **Subitens REQ**: lista os critérios do REQ-002 cobertos pela tarefa.
- **Validação no painel**: como verificar usando o painel admin (sem WhatsApp).
- **Labels sugeridas**: para aplicar quando virar issue (`tipo:*`, `prio:*`, `area:*`, `REQ-002`).
- **Branch**: nome descritivo (sem ID, conforme política v1.1). ID do cenário/bug vai no commit.

---

## Mapa de tarefas

| # | Tarefa | Status | Prioridade |
|---|--------|--------|------------|
| T-01 | Alinhar classificador às 4 categorias canônicas + nível de confiança | 🟡 | Alta |
| T-02 | Fallback condicional ao REQ-003 (Caso 2) e tratamento composto (Caso 3) | 🔴 | Alta |
| T-03 | Roteamento pré-identificação para perguntas de produto/empresa | 🔴 | Alta |
| T-04 | Identificação PF/PJ e roteamento do documento fiscal | � | Alta |
| T-05 | Estado dos campos do atendimento e mecanismo de perguntas dinâmicas | 🟡 | Alta |
| T-06 | Captura adaptativa por etapa (tipo, modelo, dados adicionais, endereço) | 🟡 | Alta |
| T-07 | Validações de respostas capturadas | 🟡 | Média |
| T-08 | Confirmação dos dados extraídos e sumarização | 🔴 | Média |
| T-09 | Tratamento de ambiguidade com retry e RAG durante qualificação | 🔴 | Média |
| T-10 | Abandono de conversa e reengajamento | 🔴 | Baixa |
| T-11 | Integração WhatsApp (agregadora — após maturidade do painel) | 🔴 | Baixa |

---

## T-01 — Alinhar classificador às 4 categorias canônicas + nível de confiança

- **Status atual:** 🟡 Parcial
- **Subitens REQ:** REQ-002.1, REQ-002.1A
- **Contexto:** `services/classificador.py` retorna `Intencao` (15 valores), `confianca` (float) e `confianca_nivel` (`alta`/`media`/`baixa`) — este último já implementado com thresholds padrão 0.70/0.40. Não há ainda o campo `categoria` (1–4) nem `justificativa_curta`. O roteamento no `processador.py` ainda é por `Intencao`, não por categoria.
- **Escopo:**
  - Adicionar campo `categoria` (enum 1–4) em `ResultadoClassificacao`, derivado da intenção atual ou de uma classificação direta no prompt da LLM.
  - Consumir limiares de REQ-014 (`classificador_conf_alta_min`, `classificador_conf_baixa_max`) em vez de hardcoded.
  - Adicionar coluna `justificativa_curta` (opcional, string) para auditoria.
  - Adaptar `_decidir_resposta` no processador para rotear por **categoria** antes de qualquer outra decisão.
- **Validação no painel:**
  - Painel exibe a categoria e o nível de confiança no detalhe da mensagem (REQ-005.6).
  - Enviar 4 mensagens-tipo (uma por categoria) e conferir o roteamento.
- **Dependências:** REQ-014 já tem os limiares definidos; só precisa expor.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`

## T-02 — Fallback condicional ao REQ-003 (Caso 2) e tratamento composto (Caso 3)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-002.1A (Caso 2 + Caso 3)
- **Contexto:** Nenhum fallback condicional; mensagens compostas não são detectadas.
- **Escopo:**
  - Caso 2: quando `confianca_nivel = baixa` ou `categoria = nao_identificado`, consultar REQ-003 (Q&A/RAG) antes de devolver fallback genérico. Registrar `fallback_req003 = true` em `ProcessamentoMensagem`.
  - Caso 3: detectar mensagem composta (heurística: presença de marcadores como `?`, conjunção adversativa após resposta curta) e classificar a pergunta embutida via REQ-002.1, combinando a resposta.
  - Persistir `resultado_fallback` (`resposta_entregue` / `pediu_esclarecimento` / `escalou`).
- **Validação no painel:**
  - "Quais produtos a Inforrel vende?" deve voltar com resposta da base mesmo se o classificador hesitar.
  - "5, mas vocês têm modelo facial?" deve registrar `quantidade=5` E responder sobre facial.
- **Dependências:** T-01.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`, `REQ-003`

## T-03 — Roteamento pré-identificação para perguntas de produto/empresa

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-002.1B
- **Contexto:** Hoje o processador exige contato/empresa identificados antes de delegar à RAG. É a causa-raiz documentada em DEC-003 (`decisoes_requisitos.md`).
- **Escopo:**
  - Criar contato e atendimento **anônimos** (`empresa_id=null`, `tipo_documento=indefinido`) quando categoria 3 com confiança alta vier sem CNPJ/CPF.
  - Delegar à REQ-003 normalmente.
  - Quando o cliente informar documento fiscal posteriormente, **promover** o contato/atendimento preservando histórico.
- **Validação no painel:**
  - Telefone novo envia "Quais relógios de ponto vocês vendem?" → painel deve mostrar contato anônimo + resposta da base.
  - Em mensagem subsequente, cliente envia CNPJ → contato é vinculado à empresa, conversa anterior preservada.
- **Dependências:** T-01.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`

## T-04 — Identificação PF/PJ e roteamento do documento fiscal

- **Status atual:** � Parcial
- **Subitens REQ:** REQ-002.2A, REQ-002.10 (parte PF↔PJ)
- **Contexto:** Fluxo PF já existe no código: `FORNECER_CPF` no classificador, `_processar_cpf_fornecido` no processador, validação de CPF (REQ-015.2), persistência em `Pessoa` e `Negociacao` com `tipo_documento=CPF`. O fluxo PJ (CNPJ via REQ-001) também existe. O que falta é a **inferência automática** PF/PJ a partir da mensagem inicial e o roteamento dirigido antes de pedir o documento.
- **Escopo:**
  - Adicionar inferência PF/PJ a partir da mensagem inicial (palavras-chave + heurística do classificador / LLM).
  - Pergunta direta quando ambíguo: "É para uma empresa (CNPJ) ou pessoa física (CPF)?".
  - Roteamento dirigido: detectado PJ → REQ-001; detectado PF → REQ-015; ambíguo → pergunta.
  - Tratar troca de tipo no meio da conversa (preservar campos comuns, redefinir documento fiscal).
  - Reuso: se telefone já tem PJ validada e cliente menciona CPF → confirmação pontual.
- **Validação no painel:**
  - Mensagem "Quero orçamento para minha casa" → pergunta dirigida ou inferência PF.
  - Mensagem com CNPJ explícito → fluxo PJ.
- **Dependências:** REQ-015 já implementado (validação de CPF + consulta de débitos). T-01.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`, `REQ-015`

## T-05 — Estado dos campos do atendimento e mecanismo de perguntas dinâmicas

- **Status atual:** 🟡 Parcial
- **Subitens REQ:** REQ-002.3, REQ-002.4
- **Contexto:** `NegociacaoInfo` (ainda não renomeado para `AtendimentoInfo` — depende de REQ-016 T-A2) existe com `chave/valor/pendente/origem`. `_atualizar_infos_negociacao` no `processador.py` já grava nome, email, tipo_produto e quantidade. Não há ainda catálogo canônico de campos nem cálculo de "próxima pergunta".
- **Escopo:**
  - Definir o **catálogo canônico de campos** por tipo de cliente (PF/PJ) e tipo de produto, marcando obrigatórios/opcionais/não-aplicáveis.
  - Implementar serviço `proxima_pergunta(atendimento)` que devolve o campo prioritário pendente, com base em ordem natural (tipo → modelo → quantidade → software → contato → endereço).
  - Atualizar processador para chamar `proxima_pergunta` ao final de cada turno (quando categoria = 1 ou 2 e qualificação não concluída).
  - Suportar marcação `nao_aplicavel` (ex.: catraca com software → quantidade opcional).
- **Validação no painel:**
  - Painel mostra a lista de campos com status (capturado / pendente / não-aplicável) na tela da conversa.
  - Cada resposta do cliente atualiza o estado e a próxima pergunta muda.
- **Dependências:** T-04 (PF/PJ define o conjunto de campos); REQ-016 T-A2 (rename de `NegociacaoInfo` → `AtendimentoInfo`).
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `area:frontend`, `REQ-002`

## T-06 — Captura adaptativa por etapa (tipo, modelo, dados adicionais, endereço)

- **Status atual:** 🟡 Parcial (extração de tipo_produto, quantidade, nome e email via regex/LLM existe; modelo, endereço completo, software e telefone ainda não)
- **Subitens REQ:** REQ-002.2, REQ-002.3A, REQ-002.3B, REQ-002.3C, REQ-002.3D
- **Subtarefas (podem virar issues filhas se a tarefa ficar grande):**
  - **T-06.1** — Tipo de produto/serviço (REQ-002.3A): expandir lista além de catraca/relógio (CFTV, roteador, software, cancela, assistência).
  - **T-06.2** — Modelo (REQ-002.3B): catálogo de modelos por tipo (catraca: Fit/Box/Pedestal/Giratória; relógio: cartográfico/biométrico/facial; etc.).
  - **T-06.3** — Dados adicionais (REQ-002.3C): nome do solicitante, quantidade/faixa, software existente, contato (e-mail/telefone). Atenção ao nome para PF (obrigatório).
  - **T-06.4** — Endereço (REQ-002.3D): logradouro, número, bairro, cidade, UF, CEP, indicador instalação/entrega/retirada.
- **Validação no painel:**
  - Mensagem inicial rica ("orçamento de catraca biométrica para 10 pessoas em SP") deve preencher múltiplos campos de uma vez.
  - Painel permite ver e corrigir manualmente cada campo coletado.
- **Dependências:** T-05.
- **Labels:** `tipo:feature`, `prio:alta`, `area:backend`, `REQ-002`

## T-07 — Validações de respostas capturadas

- **Status atual:** 🟡 Parcial (CNPJ via `validar_cnpj`)
- **Subitens REQ:** REQ-002.6
- **Escopo:**
  - Validar formato e dígitos verificadores de **CPF** (referência REQ-015.2).
  - Validar formato de **e-mail** e **telefone**.
  - Validar **modelo de produto** contra catálogo (T-06.2).
  - Validar **endereço completo** (campos obrigatórios mínimos).
  - Validar **quantidade/faixa** aceitando número exato, "até N", "N-M", "N+".
  - Quando inválido → marcar campo como pendente e gerar pergunta de esclarecimento (T-09).
- **Validação no painel:**
  - Submeter respostas inválidas (CPF errado, e-mail malformado, "umas tantas" como quantidade) e ver mensagem de esclarecimento.
- **Dependências:** T-05, T-06.
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-002`

## T-08 — Confirmação dos dados extraídos e sumarização

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-002.5, REQ-002.16
- **Escopo:**
  - Quando a mensagem inicial extrair múltiplos campos, gerar um **eco consolidado** ("Entendi: catraca facial, 10 unidades, SP. Confere?").
  - Para CNPJ usar a confirmação do REQ-001.4; demais campos vão no eco do REQ-002.16.
  - Ao final da qualificação, gerar **sumarização** (REQ-002.5) com todos os campos, separados por tipo de cliente, antes de encaminhar para orçamento.
- **Validação no painel:**
  - Mensagem inicial com 4 dados → uma única mensagem de confirmação.
  - Cliente confirma → sistema avança; cliente corrige → campo correspondente volta para pendente.
- **Dependências:** T-05, T-06, T-07.
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-002`

## T-09 — Tratamento de ambiguidade com retry e RAG durante qualificação

- **Status atual:** 🔴 Pendente (RAG existe mas sem retomada)
- **Subitens REQ:** REQ-002.17, REQ-002.21
- **Escopo:**
  - Contador de tentativas de esclarecimento por campo (até 2 retries; 3 interações no total).
  - Reformulação dirigida com opções enumeradas quando aplicável.
  - Após esgotar tentativas → escalar via REQ-004.9 preservando dados válidos.
  - Distinguir resposta ambígua de **pergunta sobre produto camuflada**: aplicar REQ-002.17 (delega à RAG) sem consumir tentativa.
  - REQ-002.17: após responder dúvida via RAG, **retomar** a pergunta pendente (reapresentar a última pergunta de qualificação).
  - Auditoria por evento (REQ-005).
- **Validação no painel:**
  - Painel mostra contador de tentativas no campo.
  - "Qual a diferença entre biométrico e facial?" no meio do fluxo → resposta + retomada da pergunta anterior.
- **Dependências:** T-05, T-06, T-07.
- **Labels:** `tipo:feature`, `prio:media`, `area:backend`, `REQ-002`, `REQ-003`

## T-10 — Abandono de conversa e reengajamento

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** REQ-002.22
- **Escopo:**
  - Job/scheduler que detecta inatividade de 24h da última mensagem do cliente.
  - Enviar mensagem única de reengajamento.
  - Após 72h totais sem resposta → finalizar conversa (status `Finalização` com motivo `abandono`), preservar dados.
  - Ao receber nova mensagem do mesmo telefone após finalização → nova conversa pelo classificador, oferecendo retomada do contexto anterior.
- **Validação no painel:**
  - Painel permite simular passagem do tempo (ex.: botão "envelhecer 24h" em modo dev) ou expor as datas de checkpoint na conversa.
- **Dependências:** T-05.
- **Labels:** `tipo:feature`, `prio:baixa`, `area:backend`, `area:infra`, `REQ-002`

## T-11 — Integração WhatsApp (agregadora — após maturidade do painel)

- **Status atual:** 🔴 Pendente
- **Subitens REQ:** dependentes do canal real (REQ-002.19 — tempo de resposta < 2s; comportamentos sensíveis ao formato WhatsApp em REQ-002.20)
- **Escopo (agregador):**
  - Integração com Twilio/Meta Cloud API (REQ-008).
  - Validação dos comportamentos do REQ-002 no canal real.
  - Ajustes de UX específicos (limite de caracteres, listas com botões, mídia).
  - Métricas de tempo de resposta (REQ-002.19).
  - Reteste dos cenários CTF que dependem do canal.
- **Quando abrir como issues efetivas:** quando T-01 a T-09 estiverem em status Done no painel administrativo.
- **Dependências:** todas as anteriores.
- **Labels:** `tipo:feature`, `prio:baixa`, `area:integracao`, `REQ-002`, `REQ-008`

---

## Itens não-funcionais cobertos transversalmente

- **REQ-002.19 (tempo < 2s)**: validar em T-11 (canal real). No painel, instrumentar telemetria (`duracao_ms` já existe em `ProcessamentoMensagem`).
- **REQ-002.20 (naturalidade)**: já parcial via templates + personalização LLM; reavaliar após T-08 (sumarização) para evitar tom robótico no eco consolidado.

## Fora do escopo desta lista

- REQ-001 (Receita Federal) — REQ próprio.
- REQ-003 (RAG/Q&A) — REQ próprio. Tarefas T-02, T-03, T-09 dependem mas não geram trabalho dentro de REQ-003.
- REQ-004 (escalonamento humano) — REQ próprio. Mencionado nas T-02 e T-09 como destino.
- REQ-005 (registro/auditoria) — REQ próprio. Atualizações em `ProcessamentoMensagem` ficam aqui (T-01) ou em REQ-005 conforme onde a coluna mora.
- REQ-010 (painel) — canal de teste. Cada tarefa cita o que o painel precisa expor; ajustes finos do painel viram tarefas de REQ-010.
- REQ-014 (configuração runtime) — REQ próprio. Limiares de confiança consumidos em T-01.
- REQ-015 (CPF) — REQ próprio. T-04 depende.

---

## Próximos passos

1. **Kika revisa** este documento e marca o que quer ajustar (granularidade, prioridades, omissões).
2. Após aprovação, gerar **`scripts/criar_issues_req002.ps1`** com `gh issue create` para cada tarefa, alinhado às labels já criadas no bootstrap.
3. Ao criar as issues, vinculá-las ao **Project "Assistente de Vendas — Board"** e ao milestone Sprint 03 (a definir no planning).

## Histórico

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-09 | 0.1 | Criação inicial — 11 tarefas agrupadas por tema, com status atual levantado a partir do código (`services/classificador.py`, `services/processador.py`, `models.NegociacaoInfo`). | Beto |
| 2026-06-09 | 0.2 | Rename terminológico Negociação→Atendimento (REQ-016 v2.0): T-03, T-05 atualizadas; referência a `AtendimentoInfo`; T-05 ganha dependência cruzada com `backlog_req016_atendimentos.md` (T-A2). Base atualizada para REQ-002 v1.26. | Beto |
| 2026-06-10 | 0.3 | Revisão pós-análise de código: T-01 contexto atualizado (`confianca_nivel` já existe, thresholds hardcoded); T-04 de 🔴→🟡 (fluxo CPF/CNPJ implementado, falta inferência automática); T-05 contexto atualizado (`NegociacaoInfo` ainda não renomeado); T-06 contexto atualizado (email/quantidade/nome também extraídos). Base atualizada para REQ-002 v1.25. | Beto |
