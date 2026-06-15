# RT-006 — Jornada: Orçamentos via backend (Swagger)

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~10 min
**REQs cobertos:** REQ-006

> **Observação:** a Sprint 2 não entregou tela de orçamentos no painel. Este roteiro valida o backend via Swagger. A cobertura de UI virá em sprint futura.

---

## Pré-requisitos

- Backend em execução com acesso ao Swagger UI.
- Ao menos uma negociação ativa e um contato existente no sistema.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-006/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Criar orçamento vinculado a uma negociação e contato

**Resultado esperado:** o endpoint retorna um ID único para o orçamento criado. O orçamento é retornado vinculado ao contato e à negociação informados.

**Valida:** ✅ REQ-006.1 (ID único) · ✅ REQ-006.2 (associação conversa/cliente)

**Status:** `[ ]`

---

## Passo 2 — Criar um segundo orçamento na mesma negociação

**Resultado esperado:** o segundo orçamento é criado com ID distinto do primeiro. Ambos coexistem vinculados à mesma negociação.

**Valida:** ✅ REQ-006.3 (múltiplos orçamentos por cliente)

**Status:** `[ ]`

---

## Passo 3 — Adicionar item ao orçamento

**Resultado esperado:** ao adicionar item com produto, quantidade e valor, a consulta ao orçamento retorna o item com os dados informados.

**Valida:** ✅ REQ-006.4 (conteúdo do orçamento registrado)

**Status:** `[ ]`

---

## Passo 4 — Verificar que não há tela de orçamentos no painel

**Resultado esperado:** navegar pelo painel sem encontrar tela dedicada de listagem ou detalhe de orçamentos. Confirma gap conhecido.

**Valida:** 🚧 REQ-006.8 / REQ-006.9 (atualização manual e visualização via painel — não implementados) · 🚧 REQ-010.5 / REQ-010.6 (telas de orçamento no painel — não existem)

**Status:** `[ ]`

---

## Passo 5 — Verificar que listagem de orçamentos por período/cliente não está disponível

**Resultado esperado:** não existe endpoint exposto que retorne orçamentos filtrados por período ou cliente. Confirma gap conhecido.

**Valida:** 🚧 REQ-006.11 (listagem filtrada — não implementada)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Criar orçamento | REQ-006.1, REQ-006.2 | `[ ]` |
| 2 — Múltiplos orçamentos | REQ-006.3 | `[ ]` |
| 3 — Adicionar item | REQ-006.4 | `[ ]` |
| 4 — Gap: UI de orçamentos 🚧 | REQ-006.8, REQ-006.9, REQ-010.5, REQ-010.6 | `[ ]` |
| 5 — Gap: listagem filtrada 🚧 | REQ-006.11 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
