# Índice de Cobertura dos REQs pelos Roteiros de Teste

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Fonte de status de implementação:** `artefatos/gerente_de_projetos/cobertura_reqs_sprint02.md`

---

## Legenda

| Símbolo | Significado |
|---------|-------------|
| ✅ Roteiro pronto | REQ coberto por roteiro executável agora |
| 🚧 Roteiro esboçado | REQ coberto por roteiro que aguarda implementação |
| — | REQ não coberto por nenhum roteiro ainda |

---

## Matriz REQ × Roteiro

| REQ | Tema | Status de implementação | Roteiro(s) | Pronto p/ testar? |
|-----|------|------------------------|------------|-------------------|
| REQ-001 | Integração Receita Federal | 🟡 Parcial | RT-001 | ✅ Majoritariamente |
| REQ-002 | Fluxo conversacional guiado | 🟡 Parcial | RT-001 | ✅ Parcialmente (perguntas adaptativas faltam) |
| REQ-003 | RAG / respostas automáticas | 🟡 Parcial substancial | RT-001, RT-002, RT-005 | ✅ Majoritariamente |
| REQ-004 | Escalonamento para humano | 🟡 Parcial | RT-003, RT-007, RT-008 | ✅ Takeover manual sim · 🚧 Automático não |
| REQ-005 | Registro de interações | 🟡 Parcial substancial | RT-001, RT-002, RT-003, RT-008 | ✅ Majoritariamente |
| REQ-006 | Rastreamento de orçamentos | 🟡 Parcial inicial | RT-006, RT-008 | ✅ Backend sim · 🚧 UI não |
| REQ-007 | Análise de sentimento | 🔴 Não iniciado | RT-007 | 🚧 Não pronto |
| REQ-008 | Integração WhatsApp / Twilio | 🟡 Parcial mínimo | RT-001 | ✅ Webhook sim · 🚧 Envio real não |
| REQ-009 | Reclamações pós-venda | 🔴 Não iniciado | RT-008 | 🚧 Não pronto |
| REQ-010 | Painel administrativo | 🟡 Parcial | RT-003, RT-004 | ✅ Cockpit e reports sim · 🚧 Auth e orçamentos não |
| REQ-011 | Modos de execução e aprovação | 🟡 Parcial | RT-002 | ✅ Workflow de aprovação sim · 🚧 3 modos formais não |
| REQ-012 | Reports de problema | 🟡 Parcial substancial | RT-004 | ✅ Majoritariamente |
| REQ-013 | Pares Q&A curados | 🟡 Parcial substancial | RT-002 | ✅ Majoritariamente |
| REQ-014 | Configuração runtime RAG | 🟡 Parcial inicial | RT-005 | ✅ Parâmetros RAG sim · 🚧 Persistência e Q&A não |
| REQ-015 | Validação CPF / débitos | — | — | — |
| REQ-016 | Identificação / numeração atendimentos | 🔴 Não iniciado | RT-009, RT-010, RT-011 | 🚧 Aguardando implementação |

---

## Roteiros por status de execução

### Prontos para executar agora

| Roteiro | Jornada | Tempo est. |
|---------|---------|-----------|
| RT-001 | Novo cliente: CNPJ → pergunta técnica → RAG | ~15 min |
| RT-002 | Aprovação de mensagem pendente → par Q&A | ~15 min |
| RT-003 | Takeover humano suspende agente | ~10 min |
| RT-004 | Gestão de reports no painel | ~10 min |
| RT-005 | Configuração RAG em runtime | ~10 min |
| RT-006 | Orçamentos via backend (Swagger) | ~10 min |

**Total estimado para execução completa:** ~70 min

### Aguardando implementação

| Roteiro | Jornada | Bloqueado por |
|---------|---------|--------------|
| RT-007 | Reclamação e escalonamento por sentimento | REQ-007, REQ-004.2 |
| RT-008 | Reclamação pós-venda com orçamento | REQ-009, REQ-006 (UI) |
| RT-009 | Criação automática de atendimento e numeração sequencial | REQ-016 (não implementado) |
| RT-010 | Janela de continuação e pergunta de continuação | REQ-016 (não implementado) |
| RT-011 | Encerramento de atendimento (manual, fechamento e abandono) | REQ-016 (não implementado) |

---

## REQs sem cobertura de roteiro

- **REQ-015** (Validação CPF / débitos) — nenhum roteiro criado ainda.

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial com 8 roteiros (RT-001 a RT-008). |
| 2026-06-19 | 1.1 | Adição de RT-009, RT-010 e RT-011 para REQ-016 (todos com status 🚧 aguardando implementação). |
