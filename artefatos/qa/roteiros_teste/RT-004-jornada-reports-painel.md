# RT-004 — Jornada: Gestão de reports de problema no painel

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~10 min
**REQs cobertos:** REQ-012, REQ-010

---

## Pré-requisitos

- Backend e painel em execução.
- Acesso à tela de Reports.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-004/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Criar um report de problema

**Resultado esperado:** ao preencher categoria, severidade e descrição e confirmar, o report aparece na lista com status inicial "aberto" e com os dados informados.

**Valida:** ✅ REQ-012 (criação de report)

**Status:** `[ ]`

---

## Passo 2 — Filtrar reports por status

**Resultado esperado:** ao aplicar o filtro "aberto", apenas reports nesse status são exibidos. Ao aplicar outro status, a lista muda correspondentemente.

**Valida:** ✅ REQ-012 (filtro por status)

**Status:** `[ ]`

---

## Passo 3 — Abrir detalhe de um report

**Resultado esperado:** a tela de detalhe exibe descrição completa, categoria, severidade, status e a mensagem associada (quando houver).

**Valida:** ✅ REQ-012 (detalhe do report) · ✅ REQ-010.7 (navegação no painel)

**Status:** `[ ]`

---

## Passo 4 — Transitar o report para "em análise" e depois para "resolvido"

**Resultado esperado:** cada transição reflete imediatamente na lista e no detalhe do report. A data/hora de atualização muda a cada transição.

**Valida:** ✅ REQ-012 (transições de status)

**Status:** `[ ]`

---

## Passo 5 — Verificar modal de raciocínio em mensagem associada ao report

**Resultado esperado:** se o report estiver vinculado a uma mensagem, ao abrir o modal de raciocínio dessa mensagem no painel, são exibidos classificação, trechos consultados e resposta gerada.

**Valida:** ✅ REQ-010.7 (modal de raciocínio) · ✅ REQ-005.6 (auditoria IA/RAG)

**Status:** `[ ]`

---

## Passo 6 — Verificar painel sem autenticação

**Resultado esperado:** ao acessar o painel em uma janela anônima, ele carrega sem solicitar credenciais. Confirma que autenticação ainda não está implementada (gap conhecido).

**Valida:** 🚧 REQ-010.1 (autenticação — não implementada)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Criar report | REQ-012 | `[ ]` |
| 2 — Filtrar por status | REQ-012 | `[ ]` |
| 3 — Detalhe do report | REQ-012, REQ-010.7 | `[ ]` |
| 4 — Transições de status | REQ-012 | `[ ]` |
| 5 — Modal de raciocínio | REQ-010.7, REQ-005.6 | `[ ]` |
| 6 — Gap: autenticação 🚧 | REQ-010.1 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
