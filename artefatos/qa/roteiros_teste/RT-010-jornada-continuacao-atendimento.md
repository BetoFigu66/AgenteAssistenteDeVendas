# RT-010 — Jornada: Janela de continuação e pergunta de continuação

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-06-19
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~20 min
**REQs cobertos:** REQ-016.7, REQ-016.8, REQ-016.9, REQ-016.5, REQ-016.17
**Status geral:** 🚧 Aguardando implementação (REQ-016 não implementado)

---

## Pré-requisitos

- Backend e painel em execução.
- Contato com pelo menos um atendimento encerrado (`status = encerrado`).
- Parâmetro `janela_continuacao_atendimento` configurado em 24h (default).
- Possibilidade de manipular `ultima_mensagem_at` no banco para simular passagem de tempo (ou usar endpoint de dev).

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-010/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Rajada de mensagens dentro da janela (atendimento ativo)

**Pré-requisito:** Atendimento `ativo` com `ultima_mensagem_at` há menos de 24h.

**Ação:** Enviar 3 mensagens em sequência rápida (ex.: "preciso de orçamento", "para 5 catracas", "biométricas").

**Valida:**
🚧 REQ-016.7 (atendimento ativo + dentro da janela → continua automaticamente sem perguntar)

**Verificação:**
- Sistema NÃO envia a mensagem de pergunta "Quer continuar de onde paramos?".
- Todas as mensagens ficam vinculadas ao mesmo `atendimento_id`.
- Banco: `ultima_mensagem_at` atualizada a cada mensagem.

**Status:** `[ ]`

---

## Passo 2 — Cliente volta dentro da janela com atendimento encerrado

**Ação:** Simular atendimento `encerrado` com `ultima_mensagem_at` há menos de 24h (ajustar no banco). Enviar nova mensagem.

**Valida:**
🚧 REQ-016.7 (atendimento encerrado + dentro da janela → pergunta ao cliente)
🚧 REQ-016.9 (template da pergunta de continuação enviado)

**Verificação:**
- Sistema envia mensagem no formato: "Oi! Vi que você já conversou conosco antes sobre **{resumo_curto}**. Quer continuar de onde paramos ou é um pedido novo? 1) Continuar 2) Novo pedido".
- Painel mostra a mensagem de transição no histórico.

**Status:** `[ ]`

---

## Passo 3 — Cliente responde "Continuar" à pergunta de continuação

**Pré-requisito:** Passo 2 executado, pergunta de continuação enviada.

**Ação:** Responder "1" ou "continuar" à pergunta.

**Valida:**
🚧 REQ-016.9 (resposta afirmativa → reabre atendimento encerrado)
🚧 REQ-016.4 (transição `encerrado` → `ativo` registrada)
🚧 REQ-016.5 (timestamp e autoria da reabertura registrados)
🚧 REQ-016.17 (evento `atendimento_reaberto` registrado)

**Verificação:**
- Banco: `status = ativo` no atendimento reaberto.
- `numero_atendimento_cliente` permanece o mesmo (não criou novo).
- Evento `atendimento_reaberto` na auditoria com `origem = cliente`.

**Status:** `[ ]`

---

## Passo 4 — Cliente responde "Novo pedido" à pergunta de continuação

**Pré-requisito:** Repetir o Passo 2 com outro contato ou após encerrar novamente o atendimento.

**Ação:** Responder "2" ou "novo" à pergunta.

**Valida:**
🚧 REQ-016.9 (resposta negativa → cria novo atendimento)
🚧 REQ-016.3 (novo atendimento recebe `numero_atendimento_cliente` = anterior + 1)

**Verificação:**
- Banco: novo registro em `atendimentos` com `numero_atendimento_cliente` incrementado.
- Atendimento anterior permanece `encerrado`.
- Painel exibe "Atendimento #N+1".

**Status:** `[ ]`

---

## Passo 5 — Cliente volta após a janela com atendimento encerrado (cria novo direto)

**Ação:** Simular atendimento `encerrado` com `ultima_mensagem_at` há mais de 24h (ajustar `ultima_mensagem_at = NOW() - INTERVAL '3 days'`). Enviar nova mensagem.

**Valida:**
🚧 REQ-016.7 (atendimento encerrado + fora da janela → cria novo atendimento diretamente, sem perguntar)

**Verificação:**
- Sistema NÃO envia a mensagem de continuação.
- Banco: novo atendimento criado com `numero_atendimento_cliente` incrementado.

**Status:** `[ ]`

---

## Passo 6 — Reabertura manual pelo vendedor no painel

**Ação:** Com atendimento `encerrado` visível no painel, clicar no botão "Reabrir atendimento" e confirmar.

**Valida:**
🚧 REQ-016.8 (vendedor pode reabrir atendimento encerrado pelo painel)
🚧 REQ-016.5 (reabertura registrada com autoria = vendedor, timestamp e justificativa)
🚧 REQ-016.17 (evento `atendimento_reaberto` com `origem = vendedor`)

**Verificação:**
- Banco: `status = ativo`.
- Evento de auditoria com `ator = <usuario_painel>` e campo `justificativa` preenchido.

**Status:** `[ ]`

---

## Passo 7 — Alteração da janela de continuação em runtime

**Ação:** Via endpoint de configuração (RT-005), alterar `janela_continuacao_atendimento` de 24h para 1h. Repetir o Passo 2 com `ultima_mensagem_at` = 2h atrás (antes estava dentro da janela de 24h, agora está fora da de 1h).

**Valida:**
🚧 REQ-016.18 (parâmetro configurável em runtime via REQ-014 sem reiniciar o servidor)

**Verificação:**
- Com janela = 1h e `ultima_mensagem_at` = 2h atrás: cria novo atendimento direto (sem perguntar).
- Restaurar `janela_continuacao_atendimento = 24h` ao final do teste.

**Status:** `[ ]`

---

## Resultado esperado ao final

| Cenário | Comportamento esperado |
|---------|----------------------|
| Rajada (ativo, dentro da janela) | Continua sem perguntar |
| Encerrado + dentro da janela | Pergunta "continuar ou novo?" |
| Continuar | Reabre atendimento, mesmo número |
| Novo pedido | Cria atendimento com número + 1 |
| Encerrado + fora da janela | Cria novo atendimento direto |
| Reabertura manual | Vendedor reabre com justificativa registrada |
| Config runtime | Mudança de janela reflete sem reiniciar |

---

## Evidências

Salvar em `artefatos/qa/evidencias/RT-010/`:
- Screenshots da mensagem de continuação enviada pelo sistema.
- Output do `SELECT` mostrando transições de estado e timestamps.
- Log dos eventos `atendimento_reaberto` e `atendimento_criado`.
