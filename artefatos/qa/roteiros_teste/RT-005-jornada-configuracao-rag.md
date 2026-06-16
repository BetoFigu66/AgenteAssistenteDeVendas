# RT-005 — Jornada: Configuração RAG em runtime

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~10 min
**REQs cobertos:** REQ-014, REQ-003

---

## Pré-requisitos

- Backend em execução com acesso ao Swagger UI.
- Base de conhecimento com ao menos um produto cadastrado.
- Anotar o valor atual de `rag_top_k` antes de iniciar (para restaurar ao final).

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-005/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Consultar configuração atual do RAG

**Resultado esperado:** o endpoint retorna os parâmetros configuráveis, incluindo ao menos `rag_score_minimo` e `rag_top_k` com seus valores correntes.

**Valida:** ✅ REQ-014 (consulta de configuração)

**Status:** `[ ]`

---

## Passo 2 — Alterar `rag_top_k` para 1

**Resultado esperado:** o endpoint aceita a alteração e retorna o novo valor. Uma consulta imediata à configuração confirma que o valor foi atualizado.

**Valida:** ✅ REQ-014 (alteração em runtime refletida imediatamente)

**Status:** `[ ]`

---

## Passo 3 — Enviar pergunta técnica e verificar trechos no modal de raciocínio

**Resultado esperado:** com `rag_top_k=1`, o modal de raciocínio da resposta exibe no máximo 1 trecho consultado da base documental.

**Valida:** ✅ REQ-014 ↔ REQ-003.2 (configuração afeta o comportamento do RAG)

**Status:** `[ ]`

---

## Passo 4 — Restaurar valor original de `rag_top_k`

**Resultado esperado:** o endpoint aceita o valor original e a configuração volta ao estado inicial.

**Valida:** ✅ REQ-014 (alteração em runtime)

**Status:** `[ ]`

---

## Passo 5 — Tentar configurar parâmetro da camada Q&A

**Resultado esperado:** ao enviar um campo de configuração da camada Q&A (ex.: `qa_score_minimo`), o campo é ignorado ou rejeitado. Confirma que a configuração da camada Q&A ainda não é exposta (gap conhecido).

**Valida:** 🚧 REQ-014 (gap — parâmetros Q&A não expõem no PATCH)

**Status:** `[ ]`

---

## Passo 6 — Verificar persistência da configuração após reinício do backend

**Resultado esperado:** após reiniciar o backend, o valor de `rag_top_k` volta ao default, não ao valor alterado. Confirma que a configuração ainda não persiste entre reinícios (gap conhecido).

**Nota:** requer que alguém reinicie o backend ou aguarde reinício natural.

**Valida:** 🚧 REQ-014 (gap — persistência entre reinícios não implementada)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Consultar configuração | REQ-014 | `[ ]` |
| 2 — Alterar `rag_top_k` | REQ-014 | `[ ]` |
| 3 — Configuração afeta RAG | REQ-014, REQ-003.2 | `[ ]` |
| 4 — Restaurar valor | REQ-014 | `[ ]` |
| 5 — Gap: parâmetros Q&A 🚧 | REQ-014 | `[ ]` |
| 6 — Gap: persistência entre reinícios 🚧 | REQ-014 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
