# RT-007 — Jornada: Reclamação e escalonamento automático por sentimento

> ## 🚧 NÃO PRONTO PARA EXECUÇÃO
>
> Este roteiro cobre REQ-007 (análise de sentimento) e partes do REQ-004 (gatilhos automáticos de escalonamento) que ainda **não estão implementados**.
>
> **O que já existe e pode ser validado parcialmente:** detecção de intenções `reclamar` e `escalar_humano` pelo classificador — visível no modal de raciocínio. A classificação formal de sentimento (positivo/neutro/negativo), a ação automática de escalar e a notificação ao vendedor **não existem**.
>
> **Quando executar:** após implementação de REQ-007 e conclusão de REQ-004.2 (notificação e resumo ao vendedor).

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~15 min (estimado)
**REQs cobertos:** REQ-007, REQ-004

---

## Pré-requisitos

- Backend e painel em execução.
- Conversa ativa em modo agente.
- REQ-007 implementado (análise de sentimento formal).
- REQ-004.2 implementado (notificação ao vendedor com resumo).

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-007/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Enviar mensagem de insatisfação clara

**Resultado esperado:** o modal de raciocínio exibe a classificação formal de sentimento como "negativo". A negociação é marcada como conversa crítica.

**Valida:** 🚧 REQ-007 (classificação de sentimento negativo e flag de conversa crítica)

**Status:** `[ ]`

---

## Passo 2 — Verificar persistência da classificação de sentimento

**Resultado esperado:** ao reabrir a negociação, a classificação de sentimento e o flag de conversa crítica estão registrados e visíveis.

**Valida:** 🚧 REQ-007 (persistência da classificação)

**Status:** `[ ]`

---

## Passo 3 — Verificar escalonamento automático acionado por insatisfação

**Resultado esperado:** com base na classificação negativa, o sistema aciona escalonamento automático — o modo da negociação muda para humano e o vendedor recebe notificação com resumo da conversa.

**Valida:** 🚧 REQ-004.2 (resumo e notificação ao vendedor) · 🚧 REQ-004.7 (ação automática por insatisfação)

**Status:** `[ ]`

---

## Passo 4 — Verificar sentimento positivo em conversa satisfatória

**Resultado esperado:** mensagem de elogio é classificada como sentimento positivo. Nenhum escalonamento é acionado.

**Valida:** 🚧 REQ-007 (classificação de sentimento positivo)

**Status:** `[ ]`

---

## Passo 5 — Verificar integração entre sentimento e histórico de interações

**Resultado esperado:** o histórico da conversa registra as classificações de sentimento por mensagem, com timestamp e critério utilizado.

**Valida:** 🚧 REQ-007 ↔ REQ-005 (sentimento registrado no histórico)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Classificação sentimento negativo 🚧 | REQ-007 | `[ ]` |
| 2 — Persistência da classificação 🚧 | REQ-007 | `[ ]` |
| 3 — Escalonamento automático 🚧 | REQ-004.2, REQ-004.7 | `[ ]` |
| 4 — Classificação sentimento positivo 🚧 | REQ-007 | `[ ]` |
| 5 — Sentimento no histórico 🚧 | REQ-007, REQ-005 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial — roteiro esboçado, aguardando implementação dos REQs. |
