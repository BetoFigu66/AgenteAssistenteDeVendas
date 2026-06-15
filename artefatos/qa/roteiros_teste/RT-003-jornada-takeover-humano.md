# RT-003 — Jornada: Takeover humano suspende o agente

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~10 min
**REQs cobertos:** REQ-004, REQ-010, REQ-005

---

## Pré-requisitos

- Backend e painel em execução.
- Conversa ativa com ao menos uma troca de mensagens em modo agente.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-003/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Verificar conversa em modo agente no painel

**Resultado esperado:** a negociação aparece listada com modo "agente" e com as mensagens trocadas visíveis em ordem cronológica, com diferenciação visual entre cliente e sistema.

**Valida:** ✅ REQ-010.7 (histórico de conversas no cockpit) · ✅ REQ-005.5 (listagem de negociações ativas)

**Status:** `[ ]`

---

## Passo 2 — Executar takeover pelo painel

**Resultado esperado:** após acionar o takeover, a negociação passa para o modo "humano". O estado é visível imediatamente no painel.

**Valida:** ✅ REQ-004.3 (takeover manual pelo vendedor) · ✅ REQ-004.4 (estado "em atendimento humano" persistido)

**Status:** `[ ]`

---

## Passo 3 — Confirmar persistência do modo humano após recarregar

**Resultado esperado:** ao recarregar a página, a negociação continua exibindo modo "humano". O estado não foi revertido.

**Valida:** ✅ REQ-004.4 (estado persistente)

**Status:** `[ ]`

---

## Passo 4 — Filtrar negociações em atendimento humano

**Resultado esperado:** ao aplicar o filtro de modo "humano" na tela de Acompanhamento, a negociação em que foi feito o takeover aparece na lista. Negociações em modo agente não aparecem.

**Valida:** ✅ REQ-010.8 (filtro por modo humano)

**Status:** `[ ]`

---

## Passo 5 — Enviar nova mensagem do cliente com conversa em modo humano

**Resultado esperado:** a mensagem aparece na conversa no painel, mas o agente não gera nenhuma resposta automática. O modo humano suspende completamente as respostas da IA.

**Valida:** ✅ REQ-004.10 (suspensão de respostas automáticas no modo humano)

**Status:** `[ ]`

---

## Passo 6 — Verificar detecção de pedido explícito de atendimento humano

**Resultado esperado:** em uma conversa em modo agente, ao enviar mensagem pedindo falar com um vendedor humano, o modal de raciocínio classifica a intenção como pedido de atendimento humano. A ação automática de escalar ainda não ocorre (gap conhecido).

**Valida:** ✅ REQ-004.1 (detecção do gatilho) · 🚧 REQ-004.2 (notificação e resumo automático ao vendedor — não implementado) · 🚧 REQ-004.6 (escalonamento automático — detecção existe, ação não)

**Status:** `[ ]`

---

## Passo 7 — Verificar detecção de reclamação

**Resultado esperado:** ao enviar mensagem expressando insatisfação, o modal de raciocínio classifica como reclamação. Nenhuma ação automática ocorre (gap conhecido).

**Valida:** ✅ REQ-004.7 (detecção de insatisfação) · 🚧 REQ-004.7 (ação automática — não implementada)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Conversa em modo agente | REQ-010.7, REQ-005.5 | `[ ]` |
| 2 — Executar takeover | REQ-004.3, REQ-004.4 | `[ ]` |
| 3 — Persistência após reload | REQ-004.4 | `[ ]` |
| 4 — Filtro por modo humano | REQ-010.8 | `[ ]` |
| 5 — Agente silenciado | REQ-004.10 | `[ ]` |
| 6 — Detecção pedido humano + gap notificação 🚧 | REQ-004.1, REQ-004.2, REQ-004.6 | `[ ]` |
| 7 — Detecção reclamação + gap ação 🚧 | REQ-004.7 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
