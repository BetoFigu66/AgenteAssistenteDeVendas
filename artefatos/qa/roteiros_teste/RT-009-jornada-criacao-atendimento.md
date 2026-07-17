# RT-009 — Jornada: Criação automática de atendimento e numeração sequencial

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-06-19
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~15 min
**REQs cobertos:** REQ-016.1, REQ-016.2, REQ-016.3, REQ-016.4, REQ-016.6, REQ-016.14, REQ-016.16, REQ-016.17
**Status geral:** 🚧 Aguardando implementação (REQ-016 não implementado)

---

## Pré-requisitos

- Backend e painel em execução.
- Dois contatos sem histórico no sistema (telefones distintos).
- Migration `atendimentos` aplicada (`alembic upgrade head`).

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-009/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Cliente novo envia intenção de compra

**Ação:** No simulador, enviar mensagem com CNPJ válido e intenção de compra (ex.: "Olá, gostaria de orçamento para 5 catracas").

**Valida:**
🚧 REQ-016.6 (criação automática de atendimento na primeira intenção de compra)
🚧 REQ-016.2 (atendimento recebe `atendimento_id` único e `numero_atendimento_cliente = 1`)
🚧 REQ-016.4 (estado inicial = `ativo`)

**Verificação no painel:**
- Painel exibe "Atendimento #1" no cabeçalho da conversa.
- Banco: `SELECT numero_atendimento_cliente, status FROM atendimentos WHERE telefone = :telefone` retorna `1, ativo`.

**Status:** `[ ]`

---

## Passo 2 — Mesmo cliente cria segundo atendimento

**Pré-requisito:** Atendimento #1 do Passo 1 estar encerrado (executar RT-011 antes ou encerrar manualmente via painel).

**Ação:** Mesmo telefone envia nova intenção de compra após encerramento do Atendimento #1 (aguardar janela de 24h ou ajustar timestamp no banco para simular).

**Valida:**
🚧 REQ-016.3 (numeração sequencial: novo atendimento recebe `numero_atendimento_cliente = 2`)
🚧 REQ-016.3 (número anterior (1) permanece imutável)

**Verificação:**
- Banco: `SELECT numero_atendimento_cliente FROM atendimentos WHERE telefone = :telefone ORDER BY id` retorna `[1, 2]`.
- Painel exibe "Atendimento #2".

**Status:** `[ ]`

---

## Passo 3 — Cliente distinto recebe numeração independente

**Ação:** Telefone diferente (Cliente B) envia intenção de compra pela primeira vez.

**Valida:**
🚧 REQ-016.3 (numeração reinicia em 1 para cada cliente — independente do Cliente A)

**Verificação:**
- Banco: `SELECT numero_atendimento_cliente FROM atendimentos WHERE telefone = :telefone_b` retorna `[1]`.
- Painel exibe "Atendimento #1" para o Cliente B.

**Status:** `[ ]`

---

## Passo 4 — Unicidade de numeração

**Ação:** Verificar constraint de banco para o par `(telefone, numero_atendimento_cliente)`.

**Valida:**
🚧 REQ-016.16 (índice único em `(telefone, numero_atendimento_cliente)`)

**Verificação:**
```sql
SELECT indexname FROM pg_indexes
WHERE tablename = 'atendimentos'
AND indexdef LIKE '%telefone%numero_atendimento_cliente%';
```
Deve retornar pelo menos 1 índice com `UNIQUE`.

**Status:** `[ ]`

---

## Passo 5 — Evento de auditoria de criação

**Ação:** Após o Passo 1, consultar eventos de auditoria da conversa.

**Valida:**
🚧 REQ-016.17 (evento `atendimento_criado` registrado em REQ-005.4)

**Verificação:**
- Modal de raciocínio ou tabela `eventos_auditoria`: deve conter evento do tipo `atendimento_criado` com `atendimento_id` e timestamp.

**Status:** `[ ]`

---

## Passo 6 — Exibição no painel (cabeçalho e lista de orçamentos)

**Ação:** Abrir a tela da conversa do Passo 1 no painel.

**Valida:**
🚧 REQ-016.14 (painel exibe "Cliente — Atendimento #N" no cabeçalho)

**Verificação:**
- Cabeçalho exibe formato "Nome / Empresa — Atendimento #1".
- Lista de orçamentos (se houver) exibe coluna ou badge com o número do atendimento.

**Status:** `[ ]`

---

## Resultado esperado ao final

| Critério | Esperado |
|----------|---------|
| Cliente A — 2 atendimentos | `numero_atendimento_cliente` = 1 e 2 |
| Cliente B — 1 atendimento | `numero_atendimento_cliente` = 1 |
| Constraint única | índice `UNIQUE (telefone, numero_atendimento_cliente)` presente |
| Evento de auditoria | `atendimento_criado` registrado para cada criação |
| Painel | Exibe "Atendimento #N" no cabeçalho |

---

## Evidências

Salvar em `artefatos/qa/evidencias/RT-009/`:
- Screenshots do painel mostrando "Atendimento #N".
- Output do `SELECT` de verificação do banco.
- Log do evento `atendimento_criado`.
