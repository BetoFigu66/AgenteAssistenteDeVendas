# Cobertura dos REQs pelo desenvolvimento — fim da Sprint 2

**Data:** 2026-05-18
**Autor:** `[gerente]` (Cascade)
**Período analisado:** até o final da Sprint 2 (2026-05-15)
**Fontes:** `artefatos/requisitos_formais/REQ-001` a `REQ-010`, código em `backend/` e `frontend/`, sprint report `artefatos/gerente_de_projetos/reports/sprint_02_20260510_interno.yaml`.

**Legenda:**
- ✅ **Integral** — todos os subitens do critério de aceite implementados.
- 🟡 **Parcial** — parte dos subitens implementados; restantes pendentes.
- 🔴 **Não iniciado** — nenhum subitem implementado de forma efetiva.

> **Aviso:** este relatório avalia a presença do mecanismo no código (modelo, endpoint, fluxo). **Não substitui** validação funcional pelo `[qa]`. Subitens marcados como 🟡 podem ter regressões não detectadas; subitens ✅ podem ter cobertura de teste insuficiente.

---

## 1. Visão consolidada

| REQ | Tema | Status global | Comentário curto |
|-----|------|---------------|------------------|
| **REQ-001** | Integração Receita Federal | 🟡 Parcial | Modelo, consulta API e regex prontos; faltam fluxo de confirmação, política de tentativas e tratamento de falhas |
| **REQ-002** | Fluxo conversacional guiado | 🟡 Parcial inicial | Classificador + extração + estado de campos prontos; perguntas dinâmicas adaptativas e regras específicas faltam |
| **REQ-003** | RAG / respostas automáticas | 🟡 **Parcial substancial** | RAG completo (chunks, embeddings, retrieval, auditoria); regras de negócio (devolver controle, catálogo, fallback) faltam |
| **REQ-004** | Escalonamento para humano | 🟡 Parcial | Takeover manual e estado HUMANO ✅; gatilhos automáticos, notificação e resumo faltam |
| **REQ-005** | Registro de interações | 🟡 **Parcial substancial** | Mensagens e auditoria IA/RAG ✅; eventos de transição de estado e de orçamento faltam |
| **REQ-006** | Rastreamento de orçamentos | 🟡 Parcial inicial | Modelos e associações prontos; atualização manual, motivos, listagem/UI faltam |
| **REQ-007** | Sentimento / conversa crítica | 🔴 Não iniciado | Apenas intents `reclamar`/`escalar_humano` no classificador (não é sentimento formal) |
| **REQ-008** | WhatsApp / Twilio | 🟡 Parcial mínimo | Webhook `/webhook` recebe `From`/`Body`; assinatura, deduplicação, envio ativo e retry faltam |
| **REQ-009** | Reclamações pós-venda | 🔴 Não iniciado | Nada do fluxo implementado |
| **REQ-010** | Painel administrativo | 🟡 Parcial | Cockpit `AcompanhamentoPage` cobre histórico/escalonamentos; auth, orçamentos e atualização de status faltam |
| **REQ-011** | Modos de execução e aprovação de mensagens | 🟡 Parcial | Workflow de aprovação/reprovação com feedback ✅ (já implementado, agora formalizado); enum de 3 modos (`simulacao`/`conversa_controlada`/`execucao_normal`) e gate de envio Twilio faltam |
| **REQ-012** | Reports de problema | 🟡 **Parcial substancial** | Modelo `ReportProblema`, endpoints `/api/reports/*` e UI (`ReportsPage` + `ReportDetalhe`) implementados; gaps em histórico de transições, alguns filtros e ação "criar par Q&A a partir do report" |
| **REQ-013** | Pares Q&A curados | 🟡 **Parcial substancial** | Modelo `ParQA`, endpoints `/api/pares-qa/*`, UI `QABasePage`, lazy embedding, configuração dinâmica `/api/config/rag` e criação a partir de reprovação ✅; gaps em criação a partir de report (REQ-012), filtro por contexto na busca, auditoria do uso em `ProcessamentoMensagem`, detecção de duplicatas e estatísticas |
| **REQ-014** | Configuração runtime das camadas de conhecimento | 🟡 Parcial inicial | `GET/PATCH /api/config/rag` e settings em `config.py` ✅ (só RAG); gaps em parâmetros Q&A no `PATCH`, toggles `*_enabled`, **persistência entre reinícios** (hoje só memória), histórico de alterações e tela dedicada no painel |

**Agregado:** 0 REQs integrais ✅ · 12 REQs parciais 🟡 · 2 REQs não iniciados 🔴.

### 1.1 Estimativa percentual de cobertura

> **Metodologia:** percentual calculado contando subitens marcados como ✅ (peso 1.0), 🟡 (peso 0.5) e 🔴 (peso 0.0) na §2 deste documento, dividido pelo total de subitens do REQ. Os percentuais de REQ-011, REQ-012, REQ-013 e REQ-014 foram estimados pela densidade de critérios de aceite já cobertos pelo código descrito em §3 (esses REQs foram criados em 2026-05-18 e ainda não tem detalhamento subitem-a-subitem na §2).
>
> **Limitações importantes:**
> - O peso é **uniforme por subitem** — um subitem trivial vale o mesmo que um crítico. NFRs e regras complexas não são ponderadas por esforço.
> - **Não reflete qualidade**: um ✅ pode ter cobertura de teste insuficiente; um 🟡 pode estar 90% completo ou 10%.
> - **Não substitui validação funcional pelo `[qa]`**.
> - Trate os números como **ordem de grandeza**, não como métrica precisa de progresso.

| REQ | Tema | % estimado |
|-----|------|-----------:|
| REQ-001 | Integração Receita Federal | ~40% |
| REQ-002 | Fluxo conversacional guiado | ~25% |
| REQ-003 | RAG / respostas automáticas | ~60% |
| REQ-004 | Escalonamento para humano | ~30% |
| REQ-005 | Registro de interações | ~55% |
| REQ-006 | Rastreamento de orçamentos | ~25% |
| REQ-007 | Sentimento / conversa crítica | ~5% |
| REQ-008 | WhatsApp / Twilio | ~20% |
| REQ-009 | Reclamações pós-venda | 0% |
| REQ-010 | Painel administrativo | ~30% |
| REQ-011 | Modos de execução e aprovação de mensagens | ~25% |
| REQ-012 | Reports de problema | ~70% |
| REQ-013 | Pares Q&A curados | ~70% |
| REQ-014 | Configuração runtime das camadas de conhecimento | ~25% |

**Média simples (não ponderada por esforço) dos 14 REQs: ~34% concluído, ~66% pendente.**

**Distribuição por faixa:**
- ≥ 50% concluído: **4 REQs** — REQ-003 (RAG), REQ-005 (histórico), REQ-012 (reports), REQ-013 (Q&A).
- 25-49% concluído: **7 REQs** — REQ-001, REQ-002, REQ-004, REQ-006, REQ-010, REQ-011, REQ-014.
- < 25% concluído: **3 REQs** — REQ-007 (sentimento, ~5%), REQ-008 (Twilio, ~20%), REQ-009 (pós-venda, 0%).

**Leitura executiva:** o sistema tem **base sólida no cérebro** (RAG, Q&A, registro, reports) mas **canal real (WhatsApp via Twilio) e fluxos críticos de pós-venda/sentimento ainda mal cobertos**. Para chegar a um POC operacional em produção, o gargalo é REQ-008 (Twilio) e o fechamento dos fluxos de qualificação (REQ-002).

---

## 2. Detalhamento por REQ

### REQ-001 — Integração Receita Federal — 🟡 Parcial

| Subitem | Status | Evidência |
|---|---|---|
| 001.1 reconhecer formatos CNPJ | ✅ | `_REGEX_CNPJ` em `backend/services/classificador.py:113` |
| 001.2 validar formato | ✅ | Mesma regex + `extrair_entidades` |
| 001.3 consultar API + retornar dados (razão social, endereço, situação, CNAE) | ✅ | `backend/services/cnpj/receitaws.py` + `persistencia.py` |
| 001.4 confirmação dos dados pelo cliente | 🟡 | `Empresa` é persistida e retornada (`GET /api/empresas/{id}`); fluxo conversacional "está correto? (S/N)" não fechado |
| 001.5 disponibilização para orçamento | 🟡 | Modelos `Empresa` ↔ `Contato` ↔ `Negociacao` ↔ `Orcamento` existem; uso ativo no fluxo ainda incipiente |
| 001.6 política de 3 tentativas + escalonamento | 🔴 | Não implementado |
| 001.7 persistência no perfil | ✅ | Tabelas `empresas`, `atividades_empresa`, `socios_empresa` |
| 001.8/.9/.10 NFR (tempo, disponibilidade, falhas) | 🔴 | Sem instrumentação/medição formal |

### REQ-002 — Fluxo conversacional guiado — 🟡 Parcial inicial

| Subitem | Status | Evidência |
|---|---|---|
| 002.1 classificação e roteamento (porta de entrada) | ✅ | `classificar_por_regras` + LLM em `backend/services/classificador.py` (14 intenções) |
| 002.2 extrair dados iniciais | ✅ | `extrair_entidades`: CNPJ, email, quantidade, tipo_produto |
| 002.3 estado dos campos (capturado/pendente/n.a.) | ✅ | Modelo `NegociacaoInfo` com `OrigemInfo` (user/inferido/atendente) |
| 002.3A identificar tipo de produto | 🟡 | Só `catraca` e `relogio_ponto` na regex; faltam câmera, roteador, software, cancela, assistência |
| 002.3B identificar modelo | 🔴 | Não implementado |
| 002.3C info adicional (quantidade, software, contato) | 🟡 | Quantidade e email sim; software existente e contato dedicado faltam |
| 002.3D endereço de entrega | 🔴 | Não implementado |
| 002.4 perguntas dinâmicas adaptativas | 🟡 | `ProcessadorMensagem` orquestra, mas lógica de "próxima melhor pergunta" não está completa |
| 002.5 sumarização final | 🔴 | Não implementado |
| 002.6 validação de respostas | 🟡 | CNPJ sim; demais (modelo, endereço, faixa) não |
| 002.10 reuso de CNPJ já validado | 🟡 | Empresa cacheada; regras de conflito/troca não |
| 002.14 / 002.14A / 002.15 regras por produto | 🔴 | Não implementado |
| 002.16 eco/confirmação dos dados extraídos | 🔴 | Não implementado |
| 002.17 consultar RAG durante qualificação | 🟡 | RAG funciona; integração "retomar qualificação após responder" não fechada |
| 002.21 ambiguidade (até 2 esclarecimentos) | 🔴 | Não implementado |
| 002.22 abandono (24h/72h) | 🔴 | Não implementado |
| NFR (002.19 / .20) | 🟡 | Sem medição |

### REQ-003 — RAG — 🟡 Parcial substancial

| Subitem | Status | Evidência |
|---|---|---|
| 003.1 classificação FAQ | 🟡 | Intents `perguntar_preco`, `perguntar_produto`, `perguntar_prazo` existem; classificação dedicada "é FAQ?" implícita no fluxo |
| 003.2 recuperação RAG | ✅ | `backend/services/rag/` + `DocumentoConhecimento` + pgvector + `RetrievalService` |
| 003.3 geração baseada em referências | ✅ | `services/llm/` + `respostas/` + auditoria de trechos |
| 003.4 conteúdo da base (preço, modelos, prazos, instalação, compat, catálogo) | 🟡 | Chunks de produtos ingeridos; preços/prazos detalhados, condições de instalação e compat incompletos |
| 003.5 registro pergunta/refs/resposta | ✅ | Modelo `ProcessamentoMensagem` registra classificação, trechos RAG, resposta |
| 003.6 não prometer prazo | 🟡 | Depende do prompt do LLM; Q&A v1 cobre algumas |
| 003.7 fallback insuficiente (1 clarificação + escalar) | 🔴 | Não implementado |
| 003.8 não negociar desconto | 🟡 | Depende do prompt |
| 003.9 devolver controle ao REQ-002 | 🔴 | Não implementado |
| 003.10 não acionar para respostas de qualificação | 🟡 | Roteamento parcial via classificador |
| 003.11 envio de catálogo | 🔴 | Não implementado |
| NFR (003.12 / .13 / .14) | 🟡 | Auditabilidade ✅ (ProcessamentoMensagem), tempo/concisão sem medição |

### REQ-004 — Escalonamento para humano — 🟡 Parcial

| Subitem | Status | Evidência |
|---|---|---|
| 004.1 detecção de gatilhos | 🟡 | Intents `escalar_humano` e `reclamar` detectadas; ação automática de escalar não |
| 004.2 resumo + notificação ao vendedor | 🔴 | Não implementado |
| 004.3 takeover manual pelo vendedor | ✅ | `PATCH /api/negociacoes/{id}/modo-operacao` em `backend/main.py:410` |
| 004.4 estado persistente "em atendimento humano" | ✅ | `ModoOperacao.HUMANO` na `Negociacao` |
| 004.5 registro histórico de escalonamento | 🟡 | Mensagens manuais registradas; evento dedicado de escalonamento não |
| 004.5A pré-qualificação antes de escalar | 🔴 | Não implementado |
| 004.6 escalonamento explícito (cliente pede) | 🟡 | Detectado; bloqueio automático e notificação não |
| 004.7 escalonamento por insatisfação | 🟡 | `reclamar` detectado; ação não |
| 004.8 análise técnica / projeto complexo | 🔴 | Não implementado |
| 004.9 baixa confiança da IA | 🔴 | Confiança existe em `ProcessamentoMensagem`, mas regra não |
| 004.10 suspensão de respostas automáticas | 🟡 | Modo HUMANO suspende; cobertura por todos os módulos não verificada |
| 004.11 mensagem de transição ao cliente | 🔴 | Não implementado |
| NFR (004.13 SLA / .14 auditabilidade) | 🔴 | Não medido |

### REQ-005 — Registro de interações — 🟡 Parcial substancial

| Subitem | Status | Evidência |
|---|---|---|
| 005.1 mensagens recebidas | ✅ | Modelo `Mensagem` + `OrigemMensagem.USER` |
| 005.2 mensagens enviadas automaticamente | ✅ | `Mensagem` + `OrigemMensagem.SYSTEM` |
| 005.3 eventos de transição de estado da conversa | 🔴 | `StatusNegociacao` existe (novo, em_contato, em_negociacao, arquivado), mas eventos auditáveis com ator/motivo/timestamp por transição não |
| 005.4 eventos de orçamento e erros | 🔴 | Não implementado |
| 005.5 consulta histórico | 🟡 | `GET /api/historico/{telefone}`, `/api/negociacoes/ativas`; filtros por período/status/cliente parciais |
| 005.6 auditoria IA/RAG | ✅ | `ProcessamentoMensagem` registra pergunta, contexto recuperado, resposta, classificação |
| 005.7 imutabilidade | 🟡 | Modelo permite update; regra não enforced |
| 005.8 dados sensíveis | 🔴 | Sem política implementada |
| NFR | 🟡 | Sem medição |

### REQ-006 — Rastreamento de orçamentos — 🟡 Parcial inicial

| Subitem | Status | Evidência |
|---|---|---|
| 006.1 id único | ✅ | Modelo `Orcamento` |
| 006.2 associação conversa/cliente | ✅ | FKs `negociacao_id`/`contato_id` |
| 006.3 múltiplos orçamentos | ✅ | Modelo suporta |
| 006.4 conteúdo registrado (inline / livre / referência) | 🟡 | `ItemOrcamento` existe; metadados (canal, origem, imutabilidade) e modos não normalizados |
| 006.5 estados | 🟡 | `StatusOrcamento` não bate 1:1 com o REQ (rascunho/enviado/convertido/perdido) |
| 006.6 timestamp por transição | 🟡 | Tem `criado_em` e `atualizado_em`; histórico por transição não |
| 006.7 motivo "perdido" | 🔴 | Campo não previsto |
| 006.8 / .9 atualização manual via painel | 🔴 | UI/endpoint não implementados |
| 006.10 auditoria autoria | 🔴 | Não implementado |
| 006.11 listagem por período/cliente/status | 🔴 | Endpoint não exposto |
| 006.12 visualização consolidada | 🔴 | Tela não existe |

### REQ-007 — Sentimento / conversa crítica — 🔴 Não iniciado

- Apenas o classificador detecta `reclamar` e `escalar_humano`, **não é** uma classificação formal de sentimento positivo/neutro/negativo.
- Sem persistência das classificações, sem registro de critérios (REQ-007.3), sem vínculo com REQ-004/REQ-005.

### REQ-008 — Twilio / WhatsApp — 🟡 Parcial mínimo

| Subitem | Status | Evidência |
|---|---|---|
| 008.1 webhook | 🟡 | `POST /webhook` existe (`backend/main.py:156`), mas só esqueleto |
| 008.2 extração campos (From, Body) | ✅ | Form fields parseados |
| 008.4 associação conversa | ✅ | Via `Contato` (telefone) → `Negociacao` |
| 008.5 envio efetivo via Twilio | 🔴 | Mensagens manuais só registram no banco; sem chamada Twilio outbound |
| 008.7 links/arquivos | 🔴 | Não implementado |
| 008.8 / .9 deduplicação | 🔴 | Não implementado |
| 008.10 validação assinatura Twilio | 🔴 | Não implementado |
| 008.11 segredos protegidos | 🟡 | `.env.example` presente, mas validação não auditada |
| 008.12 registro histórico | ✅ | REQ-005 cobre |
| 008.13 erros de envio registrados | 🔴 | Sem envio, sem registro |
| 008.14 respeito ao estado humano | 🟡 | Modo HUMANO existe; aplicação no canal não verificada |
| 008.15 retry | 🔴 | Não implementado |

### REQ-009 — Reclamações pós-venda — 🔴 Não iniciado

Nada do fluxo (detecção pós-venda, identificação do orçamento por telefone, confirmação com cliente, escalonamento com contexto) implementado.

### REQ-010 — Painel administrativo — 🟡 Parcial

| Subitem | Status | Evidência |
|---|---|---|
| 010.1 autenticação | 🔴 | Endpoints abertos |
| 010.2 identidade do usuário | 🟡 | Modelo `User` existe; `aprovador_id`/`reprovador_id` registram autoria |
| 010.3 usuário único POC | 🟡 | Modelo suporta múltiplos, mas sem auth |
| 010.4 expiração de sessão | 🔴 | Sem sessão |
| 010.5 tela de orçamentos | 🔴 | Não existe |
| 010.6 detalhe do orçamento | 🔴 | Não existe |
| 010.7 histórico de conversas | ✅ | `AcompanhamentoPage.jsx` — listagem de negociações, mensagens, modal de raciocínio, aprovação/reprovação |
| 010.8 tela de escalonamentos | 🟡 | Cobertura parcial via filtros de modo HUMANO em `AcompanhamentoPage` |
| 010.9 atualização manual de status do orçamento | 🔴 | Não implementado |
| 010.10 somente leitura no histórico | 🟡 | Em parte (mensagens recebidas são read-only; mensagens system pendentes são editáveis pelo aprovar/reprovar — fluxo distinto) |
| 010.11 / .12 / .13 NFR | 🟡 | Stack React + Vite + Tailwind atende; sem medição formal |

---

## 3. Funcionalidades implementadas que não estão em nenhum REQ atual

Blocos entregues mas sem requisito formal correspondente — candidatos a virarem REQs novos para preservar rastreabilidade:

1. ~~**Workflow de aprovação humana de mensagens da IA antes do envio**~~ — **formalizado em `REQ-011` em 2026-05-18.**
   - Endpoints `/api/mensagens/pendentes`, `/api/mensagens/{id}/aprovar`, `/api/mensagens/{id}/reprovar` e UI `AcompanhamentoPage` agora têm REQ de referência (`@/c:/Kika/AgenteAssistenteDeVendas/artefatos/requisitos_formais/REQ-011-modos-execucao-aprovacao-mensagens.md`).
   - O REQ-011 amplia o escopo: além do workflow já existente, introduz **três modos de execução** (`simulacao`, `conversa_controlada`, `execucao_normal`) — ver §1 (REQ-011) para status de cobertura.

2. ~~**Sistema de Reports de problema**~~ — **formalizado em `REQ-012` em 2026-05-18.**
   - Modelo `ReportProblema`, endpoints `/api/reports/*` e UI (`ReportsPage` + `ReportDetalhe`) agora têm REQ de referência (`@/c:/Kika/AgenteAssistenteDeVendas/artefatos/requisitos_formais/REQ-012-reports-problema-evolucao-agente.md`).
   - O REQ-012 fixa categorias, severidades, workflow de status, regras de criação automática via reprovação (vincula com REQ-011) e critérios de triagem — ver §1 (REQ-012) para status de cobertura.

3. ~~**Q&A Pairs — camada curada sobre RAG**~~ — **formalizado em `REQ-013` em 2026-05-18.**
   - Modelo `ParQA`, endpoints `/api/pares-qa/*` e UI `QABasePage` agora têm REQ de referência (`@/c:/Kika/AgenteAssistenteDeVendas/artefatos/requisitos_formais/REQ-013-pares-qa-curados.md`).
   - O REQ-013 fixa **precedência sobre o RAG documental (REQ-003)**, regra de **lazy embedding** (gerado só na aprovação), origens de criação (manual / reprovação REQ-011 / report REQ-012 / ingestão em lote) e critérios de busca — ver §1 (REQ-013) para status de cobertura.

4. ~~**Configuração RAG dinâmica em runtime**~~ — **formalizado em `REQ-014` em 2026-05-18.**
   - Endpoints `GET/PATCH /api/config/rag` e settings em `backend/config.py` agora têm REQ de referência (`@/c:/Kika/AgenteAssistenteDeVendas/artefatos/requisitos_formais/REQ-014-configuracao-runtime-camadas-conhecimento.md`).
   - O REQ-014 corrige a percepção anterior: o `PATCH` atual só cobre `rag_score_minimo` e `rag_top_k` (não Q&A nem `*_enabled`); persistência entre reinícios e auditoria de alterações não existem. Esses gaps estão agora formalmente registrados como critérios de aceite — ver §1 (REQ-014) para status.

5. **Modo de operação agente/humano por negociação**
   - `Negociacao.modo_operacao` (`agente`/`humano`). Generaliza parte do REQ-004 mas é mecanismo amplo (ver REQ-004.3/.4).

**Recomendação:** todos os blocos identificados estão agora formalizados em REQs. O item 5 (modo agente/humano por negociação) **não** virou REQ próprio porque já é coberto por REQ-004.3/.4. A rastreabilidade entre código das Sprints 1-2 e requisitos formais está completa.

---

## 4. Resumo executivo

- **REQs com base sólida (parcial substancial):** REQ-003 (RAG), REQ-005 (registro de interações).
- **REQs com fundação técnica + UI parcial:** REQ-001 (CNPJ), REQ-002 (classificador), REQ-004 (takeover), REQ-006 (modelos), REQ-010 (cockpit).
- **REQs sem desenvolvimento:** REQ-007 (sentimento), REQ-009 (pós-venda).
- **REQ-008 (Twilio):** webhook estrutural existe mas o canal real (envio, assinatura, dedupe) não está operacional — bloqueio explícito da Sprint 2.

**Dívida acumulada visível:**

- ~~Funcionalidades sem REQ formal~~ — **zerado em 2026-05-18** com a criação de REQ-011, REQ-012, REQ-013 e REQ-014. Item 5 da §3 (modo agente/humano por negociação) já é coberto por REQ-004.3/.4 e não exige REQ próprio.
- REQ-002.22 (abandono de conversa) e REQ-005.3 (eventos de transição) seguem pendentes há 2 sprints — recomendado priorizar antes de ampliar escopo.
- Métricas e NFRs sem instrumentação em quase todos os REQs — `[qa]` deve definir critérios mensuráveis para próxima cadência.

---

## 5. Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-18 | 1.0 | Criação inicial após fim da Sprint 2. Análise por leitura de REQs + inspeção de `backend/main.py`, `backend/models.py`, `backend/services/`, `frontend/src/components/`. |
| 2026-05-18 | 1.1 | Adicionado REQ-011 à §1 (status 🟡 Parcial); §3 item 1 marcado como formalizado pelo REQ-011; §4 dívida reduzida de 4 para 3 funcionalidades sem REQ formal. |
| 2026-05-18 | 1.2 | Adicionado REQ-012 à §1 (status 🟡 Parcial substancial); §3 item 2 marcado como formalizado pelo REQ-012; §4 dívida reduzida de 3 para 2 funcionalidades sem REQ formal. |
| 2026-05-18 | 1.3 | Adicionado REQ-013 à §1 (status 🟡 Parcial substancial); §3 item 3 marcado como formalizado pelo REQ-013; §4 dívida reduzida de 2 para 1 funcionalidade sem REQ formal. |
| 2026-05-18 | 1.4 | Adicionado REQ-014 à §1 (status 🟡 Parcial inicial); §3 item 4 marcado como formalizado pelo REQ-014; §4 dívida de funcionalidades sem REQ formal **zerada**. |
| 2026-05-18 | 1.5 | Adicionada §1.1 ("Estimativa percentual de cobertura") com metodologia, percentuais por REQ, média simples (~34% concluído, ~66% pendente) e distribuição por faixa. |
