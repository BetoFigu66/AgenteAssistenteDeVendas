# RT-002 — Jornada: Aprovação de mensagem pendente e criação de par Q&A

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~15 min
**REQs cobertos:** REQ-011, REQ-013, REQ-003, REQ-005

---

## Pré-requisitos

- Backend e painel em execução.
- Sistema configurado para enfileirar respostas antes do envio (modo de aprovação ativo).
- Ao menos uma conversa com resposta automática pendente de aprovação — se não houver, disparar uma pergunta de um contato qualquer para gerar uma.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-002/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Verificar fila de mensagens pendentes

**Resultado esperado:** a tela de "Pendentes de aprovação" exibe ao menos uma mensagem aguardando revisão, com a pergunta original do cliente, o conteúdo gerado pela IA e o contexto da conversa.

**Valida:** ✅ REQ-011 (workflow de aprovação — visualização da fila)

**Status:** `[ ]`

---

## Passo 2 — Aprovar uma mensagem da fila

**Resultado esperado:** a mensagem some da fila de pendentes e aparece na conversa correspondente como aprovada, marcada como enviada pelo sistema.

**Valida:** ✅ REQ-011 (aprovação) · ✅ REQ-005.2 (mensagem do sistema registrada)

**Status:** `[ ]`

---

## Passo 3 — Confirmar que mensagem aprovada não reaparece na fila

**Resultado esperado:** ao recarregar a tela de pendentes, a mensagem aprovada não está mais listada.

**Valida:** ✅ REQ-011 (estabilidade da fila após aprovação)

**Status:** `[ ]`

---

## Passo 4 — Reprovar uma mensagem com resposta corrigida

**Resultado esperado:** ao reprovar, o sistema solicita a resposta correta. Após fornecer e confirmar, a mensagem some da fila. Nenhuma mensagem incorreta é enviada ao cliente.

**Valida:** ✅ REQ-011 (reprovação com feedback)

**Status:** `[ ]`

---

## Passo 5 — Verificar que a reprovação gerou um par Q&A como rascunho

**Resultado esperado:** na Base de Q&A, aparece um novo par no status "rascunho" com a pergunta original e a resposta corrigida fornecida na reprovação. O par ainda não está ativo (não é usado em respostas automáticas).

**Valida:** ✅ REQ-013 (par criado por reprovação aparece como rascunho) · ✅ REQ-011 ↔ REQ-013 (integração entre reprovação e base curada)

**Status:** `[ ]`

---

## Passo 6 — Aprovar o par Q&A recém-criado

**Resultado esperado:** o par muda de status para "aprovado" e ativo na Base de Q&A.

**Valida:** ✅ REQ-013 (aprovação de par Q&A)

**Status:** `[ ]`

---

## Passo 7 — Enviar pergunta similar à do par aprovado em uma nova conversa

**Resultado esperado:** a resposta recebida corresponde ao conteúdo do par Q&A aprovado (não à base documental). O modal de raciocínio indica a base de Q&A como fonte, não o RAG documental.

**Valida:** ✅ REQ-013 (par aprovado é usado em respostas) · ✅ REQ-003 (Q&A tem precedência sobre RAG documental) · ✅ REQ-005.6 (auditoria indica fonte correta)

**Status:** `[ ]`

---

## Passo 8 — Desativar o par Q&A e reenviar a pergunta

**Resultado esperado:** após desativar, a mesma pergunta não mais retorna o conteúdo do par. A resposta passa a vir da base documental (RAG) ou do comportamento padrão do agente.

**Valida:** ✅ REQ-013 (par desativado não é usado)

**Status:** `[ ]`

---

## Passo 9 — Confirmar que mensagem reprovada não reaparece na fila

**Resultado esperado:** ao recarregar a tela de pendentes após a reprovação do passo 4, a mensagem reprovada não está mais listada.

**Valida:** ✅ REQ-011 (estabilidade da fila após reprovação)

**Status:** `[ ]`

---

## Passo 10 — Verificar modos de operação disponíveis no painel

**Resultado esperado:** a negociação exibe apenas os modos "agente" e "humano" na interface. Os modos `simulacao`, `conversa_controlada` e `execucao_normal` ainda não aparecem.

**Valida:** 🚧 REQ-011 (gap — três modos formais não implementados na UI)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Fila de pendentes | REQ-011 | `[ ]` |
| 2 — Aprovar mensagem | REQ-011, REQ-005.2 | `[ ]` |
| 3 — Fila estável após aprovação | REQ-011 | `[ ]` |
| 4 — Reprovar com feedback | REQ-011 | `[ ]` |
| 5 — Par Q&A gerado como rascunho | REQ-013, REQ-011↔REQ-013 | `[ ]` |
| 6 — Aprovar par Q&A | REQ-013 | `[ ]` |
| 7 — Par aprovado usado na resposta | REQ-013, REQ-003, REQ-005.6 | `[ ]` |
| 8 — Par desativado não é usado | REQ-013 | `[ ]` |
| 9 — Fila estável após reprovação | REQ-011 | `[ ]` |
| 10 — Gap: modos formais 🚧 | REQ-011 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
