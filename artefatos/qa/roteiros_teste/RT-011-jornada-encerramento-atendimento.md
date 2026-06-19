# RT-011 — Jornada: Encerramento de atendimento (manual, pergunta de fechamento e abandono)

**Data de criação:** 2026-06-19
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~20 min
**REQs cobertos:** REQ-016.4, REQ-016.5, REQ-016.10, REQ-016.12, REQ-016.15, REQ-016.17
**Status geral:** 🚧 Aguardando implementação (REQ-016 não implementado)

---

## Pré-requisitos

- Backend e painel em execução.
- Contato com atendimento `ativo` existente, com ao menos um orçamento vinculado.
- Possibilidade de manipular timestamps no banco para simular abandono.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-011/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Encerramento via pergunta de fechamento ("Posso ajudar em mais alguma coisa?")

**Pré-requisito:** Atendimento `ativo` após envio de orçamento ou resposta a dúvida pré-venda.

**Ação:** Aguardar o sistema enviar a pergunta de fechamento automaticamente, ou simulá-la diretamente. Em seguida, responder "Não, obrigado".

**Valida:**
🚧 REQ-016.10 (sistema envia "Posso te ajudar em mais alguma coisa?" após ciclo natural)
🚧 REQ-016.10 (resposta negativa → transição `ativo` → `encerrado` com `motivo = concluido_pelo_cliente`)
🚧 REQ-016.4 (motivo de encerramento = `concluido_pelo_cliente`)

**Verificação:**
- Banco: `status = encerrado`, `motivo_encerramento = concluido_pelo_cliente`.
- Sistema envia mensagem de despedida cordial.
- Painel exibe atendimento com badge "Encerrado".

**Status:** `[ ]`

---

## Passo 2 — Resposta afirmativa mantém atendimento ativo

**Pré-requisito:** Sistema enviou pergunta de fechamento (Passo 1, antes de responder).

**Ação:** Responder "Sim, tenho mais uma dúvida" à pergunta "Posso ajudar em mais alguma coisa?".

**Valida:**
🚧 REQ-016.10 (resposta afirmativa → atendimento permanece `ativo`, novo ciclo de qualificação)

**Verificação:**
- Banco: `status = ativo` após a resposta.
- Sistema inicia novo ciclo de atendimento (pergunta sobre o que mais precisa).

**Status:** `[ ]`

---

## Passo 3 — Encerramento manual pelo vendedor no painel

**Ação:** Com atendimento `ativo` visível no painel, clicar em "Encerrar atendimento", selecionar motivo e confirmar.

**Valida:**
🚧 REQ-016.4 (transição `ativo` → `encerrado` com `motivo = manual_vendedor`)
🚧 REQ-016.5 (timestamp, autoria e motivo registrados)
🚧 REQ-016.17 (evento `atendimento_encerrado` com `origem = vendedor`)

**Verificação:**
- Banco: `status = encerrado`, `motivo_encerramento = manual_vendedor`.
- Evento de auditoria com `ator = <usuario_painel>` e timestamp correto.

**Status:** `[ ]`

---

## Passo 4 — Orçamento perdido não encerra o atendimento

**Ação:** Com atendimento `ativo` e orçamento vinculado, marcar o orçamento como `perdido` no painel.

**Valida:**
🚧 REQ-016.4 (desfecho do orçamento não altera o estado do atendimento)
🚧 REQ-016.12 (independência entre desfecho comercial do orçamento e ciclo do atendimento)

**Verificação:**
- Banco: `atendimentos.status = ativo` após marcar orçamento como `perdido`.
- Painel exibe atendimento como ativo com orçamento sinalizado como perdido.

**Status:** `[ ]`

---

## Passo 5 — Abandono por inatividade (motivo = abandono)

**Ação:** Simular abandono ajustando `ultima_mensagem_at` para `NOW() - INTERVAL '73 hours'` no banco. Aguardar ou forçar execução do job de inatividade (REQ-002.22).

**Valida:**
🚧 REQ-016.4 (abandono após 72h → `motivo = abandono`)
🚧 REQ-016.17 (evento `atendimento_encerrado` com `motivo = abandono`)

**Verificação:**
- Banco: `status = encerrado`, `motivo_encerramento = abandono`.
- Evento de auditoria registrado com `origem = sistema`.

**Status:** `[ ]`

---

## Passo 6 — Navegação por atendimento no painel

**Ação:** Abrir o detalhe de um atendimento com múltiplos orçamentos no painel.

**Valida:**
🚧 REQ-016.15 (painel permite navegar para todas as conversas e orçamentos vinculados ao atendimento)
🚧 REQ-016.15 (histórico de transições de estado visível)

**Verificação:**
- Painel lista todas as conversas vinculadas ao atendimento.
- Painel lista todos os orçamentos vinculados, com seus desfechos independentes.
- Histórico de estados exibe a sequência: criado → encerrado → reaberto (se aplicável), com timestamps.

**Status:** `[ ]`

---

## Passo 7 — Integridade referencial: orçamento sem atendimento rejeitado

**Ação:** Tentar inserir via Swagger (POST `/api/orcamentos`) um orçamento sem `atendimento_id`.

**Valida:**
🚧 REQ-016.16 (FK `orcamentos.atendimento_id` NOT NULL — banco rejeita)

**Verificação:**
- Backend retorna erro 422 ou 400.
- Banco não permite inserção com `atendimento_id = NULL` para novos orçamentos.

**Status:** `[ ]`

---

## Resultado esperado ao final

| Cenário | Comportamento esperado |
|---------|----------------------|
| Resposta negativa ao fechamento | `encerrado`, motivo `concluido_pelo_cliente` |
| Resposta afirmativa ao fechamento | Permanece `ativo` |
| Encerramento manual | `encerrado`, motivo `manual_vendedor`, autoria registrada |
| Orçamento perdido | Atendimento permanece `ativo` |
| Abandono 72h | `encerrado`, motivo `abandono` |
| Navegação no painel | Conversas, orçamentos e histórico de estados acessíveis |
| Orçamento sem atendimento | Banco/API rejeita |

---

## Evidências

Salvar em `artefatos/qa/evidencias/RT-011/`:
- Screenshots do painel mostrando badge "Encerrado" e histórico de estados.
- Output do `SELECT` de `atendimentos` com `status` e `motivo_encerramento`.
- Log dos eventos `atendimento_encerrado` e `atendimento_reaberto`.
