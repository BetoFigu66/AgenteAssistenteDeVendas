# RT-001 — Jornada: Novo cliente envia CNPJ e faz pergunta técnica

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~15 min
**REQs cobertos:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-008

---

## Pré-requisitos

- Backend e painel em execução.
- Contato sem histórico prévio no sistema.
- Base de conhecimento com ao menos um produto cadastrado.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-001/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Enviar saudação

**Resultado esperado:** a mensagem aparece no painel; o sistema responde de forma coerente com uma saudação, sem pedir CNPJ nem iniciar qualificação técnica imediatamente.

**Valida:** ✅ REQ-002.1 (classificação de saudação) · ✅ REQ-008.1 (webhook aceita mensagem) · ✅ REQ-005.1 (mensagem registrada)

**Status:** `[ ]`

---

## Passo 2 — Enviar CNPJ da empresa

**Resultado esperado:** o painel exibe, na negociação correspondente, a empresa identificada com razão social, situação cadastral e ao menos um endereço. O CNPJ é reconhecido no formato enviado.

**Valida:** ✅ REQ-001.1 (reconhecimento do formato CNPJ) · ✅ REQ-001.2 (validação do formato) · ✅ REQ-001.3 (consulta à Receita Federal e retorno de dados) · ✅ REQ-001.7 (persistência no perfil da empresa) · ✅ REQ-002.2 (extração de dados da mensagem) · ✅ REQ-005.1 (mensagem registrada)

**Status:** `[ ]`

---

## Passo 3 — Verificar vínculo da empresa com a negociação

**Resultado esperado:** ao abrir a negociação no painel, os dados da empresa aparecem como contexto associado.

**Valida:** ✅ REQ-001.5 (empresa disponibilizada para orçamento/negociação)

**Status:** `[ ]`

---

## Passo 4 — Enviar quantidade e tipo de produto

**Resultado esperado:** a negociação no painel reflete os campos "quantidade" e "tipo de produto" capturados. O sistema continua a conversa sem reiniciar o fluxo.

**Valida:** ✅ REQ-002.2 (extração de entidades) · ✅ REQ-002.3 (estado dos campos capturado/pendente)

**Status:** `[ ]`

---

## Passo 5 — Verificar campos pendentes na negociação

**Resultado esperado:** o painel indica quais campos já foram coletados (CNPJ, quantidade, tipo) e quais ainda estão pendentes (ex.: modelo, endereço de entrega).

**Valida:** ✅ REQ-002.3 (visibilidade do estado de qualificação)

**Status:** `[ ]`

---

## Passo 6 — Enviar pergunta técnica sobre produto

**Resultado esperado:** o sistema responde com conteúdo baseado na base de conhecimento. O modal de raciocínio (acessível pelo painel) exibe os trechos consultados e a resposta gerada.

**Valida:** ✅ REQ-003.2 (recuperação RAG) · ✅ REQ-003.3 (geração baseada em referências) · ✅ REQ-003.5 (auditoria da resposta) · ✅ REQ-005.6 (auditoria IA/RAG no painel)

**Status:** `[ ]`

---

## Passo 7 — Verificar histórico completo da conversa

**Resultado esperado:** o endpoint de histórico retorna todas as mensagens da sessão em ordem cronológica, com origem correta (cliente / sistema).

**Valida:** ✅ REQ-005.2 (mensagem do sistema registrada) · ✅ REQ-005.5 (consulta ao histórico por cliente)

**Status:** `[ ]`

---

## Passo 8 — Enviar o mesmo CNPJ por um segundo contato

**Resultado esperado:** os dados da empresa são os mesmos da consulta anterior, sem nova chamada à Receita Federal (uso de cache). Ambas as negociações exibem a mesma razão social e endereço.

**Valida:** ✅ REQ-001.7 (reuso da empresa já consultada) · ✅ REQ-002.10 (reaproveitamento de CNPJ validado)

**Status:** `[ ]`

---

## Passo 9 — Confirmar que agente não enviou mensagens reais ao WhatsApp

**Resultado esperado:** todas as respostas aparecem apenas no painel interno; nenhum envio outbound real foi realizado pelo sistema.

**Valida:** 🚧 REQ-008.5 (envio efetivo via Twilio — gap conhecido, não implementado)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Saudação | REQ-002.1, REQ-008.1, REQ-005.1 | `[ ]` |
| 2 — CNPJ | REQ-001.1, REQ-001.2, REQ-001.3, REQ-001.7, REQ-002.2, REQ-005.1 | `[ ]` |
| 3 — Vínculo empresa/negociação | REQ-001.5 | `[ ]` |
| 4 — Quantidade e tipo | REQ-002.2, REQ-002.3 | `[ ]` |
| 5 — Campos pendentes | REQ-002.3 | `[ ]` |
| 6 — Pergunta técnica (RAG) | REQ-003.2, REQ-003.3, REQ-003.5, REQ-005.6 | `[ ]` |
| 7 — Histórico | REQ-005.2, REQ-005.5 | `[ ]` |
| 8 — Reuso de CNPJ | REQ-001.7, REQ-002.10 | `[ ]` |
| 9 — Gap Twilio 🚧 | REQ-008.5 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
