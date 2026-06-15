# RT-008 — Jornada: Reclamação pós-venda com identificação de orçamento

> ## 🚧 NÃO PRONTO PARA EXECUÇÃO
>
> Este roteiro cobre REQ-009 (tratamento de reclamações pós-venda), que **não está implementado**. Também depende da conclusão de REQ-006 (rastreamento de orçamentos com UI e listagem).
>
> **Pré-requisitos de desenvolvimento antes de executar:**
> - REQ-006 completo (atualização manual de status, listagem por cliente/período, visualização consolidada no painel).
> - REQ-009 implementado (detecção de reclamação pós-venda, busca de orçamento por telefone, confirmação com cliente, escalonamento com contexto).
>
> **Quando executar:** após entrega das histórias de REQ-009 e fechamento dos gaps de REQ-006.

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~20 min (estimado)
**REQs cobertos:** REQ-009, REQ-006, REQ-004, REQ-005

---

## Pré-requisitos

- Backend e painel em execução.
- Contato com orçamento anterior registrado no sistema (estado convertido ou enviado).
- REQ-006 completo (UI e listagem de orçamentos).
- REQ-009 implementado.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-008/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Cliente com orçamento anterior inicia conversa com reclamação

**Resultado esperado:** o sistema detecta a reclamação e identifica que o contato possui orçamento anterior. A conversa é tratada como pós-venda, não como qualificação de novo cliente.

**Valida:** 🚧 REQ-009 (detecção de reclamação pós-venda) · 🚧 REQ-009 ↔ REQ-006 (busca de orçamento por telefone)

**Status:** `[ ]`

---

## Passo 2 — Sistema confirma o orçamento identificado com o cliente

**Resultado esperado:** o agente apresenta ao cliente o orçamento identificado (número, produto, data) e solicita confirmação de que é o correto.

**Valida:** 🚧 REQ-009 (confirmação do orçamento com o cliente)

**Status:** `[ ]`

---

## Passo 3 — Escalonamento com contexto para atendimento humano

**Resultado esperado:** após a confirmação, o sistema escala para um atendente humano e inclui no contexto o número do orçamento, o produto, a reclamação relatada e o histórico da conversa.

**Valida:** 🚧 REQ-009 (escalonamento com contexto completo) · 🚧 REQ-004.2 (resumo ao vendedor)

**Status:** `[ ]`

---

## Passo 4 — Verificar orçamento vinculado à reclamação no painel

**Resultado esperado:** o vendedor, ao assumir a conversa no painel, consegue visualizar o orçamento associado e o histórico da reclamação sem precisar buscar manualmente.

**Valida:** 🚧 REQ-009 ↔ REQ-010 (visibilidade do contexto pós-venda no painel)

**Status:** `[ ]`

---

## Passo 5 — Verificar registro do evento no histórico

**Resultado esperado:** o histórico da conversa registra a reclamação, o orçamento identificado, a confirmação do cliente e o escalonamento, com timestamps.

**Valida:** 🚧 REQ-005.3 (eventos de transição registrados) · 🚧 REQ-009 ↔ REQ-005

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Detecção de reclamação pós-venda 🚧 | REQ-009, REQ-006 | `[ ]` |
| 2 — Confirmação do orçamento 🚧 | REQ-009 | `[ ]` |
| 3 — Escalonamento com contexto 🚧 | REQ-009, REQ-004.2 | `[ ]` |
| 4 — Visibilidade no painel 🚧 | REQ-009, REQ-010 | `[ ]` |
| 5 — Registro no histórico 🚧 | REQ-005.3, REQ-009 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial — roteiro esboçado, aguardando implementação de REQ-009 e conclusão de REQ-006. |
