# FASE-criando-orcamento

**Nome exibido:** Criando Orçamento  
**Versão:** 0.1  
**Status:** Rascunho

---

## Propósito

Qualificação concluída. O **vendedor (Rita)** elabora e envia o orçamento ao cliente. O sistema acompanha o status e mantém o cliente informado dentro do canal WhatsApp.

---

## Situação do atendimento

- **Situação:** `ativo`
- **Fase terminal?** Não

---

## Como o cliente chega aqui

| Origem | Condição |
|--------|----------|
| Finalizando | Cliente confirmou resumo; todos os campos obrigatórios preenchidos (REQ-002.5) |
| Escalação | Vendedor assume antes da qualificação terminar (REQ-004) — caso excepcional |

---

## O que o sistema faz nesta fase

- `notificar_vendedor` — nova solicitação qualificada disponível no painel (REQ-005.4, REQ-010).
- Modo de operação tende a **humano** (REQ-004, REQ-006) — Rita elabora orçamento.
- Responde dúvidas pontuais do cliente via REQ-003 quando aplicável, sem reabrir qualificação completa.
- Após envio do orçamento pelo vendedor, `fazer_pergunta` → PERG-016-010 quando ciclo natural terminar.
- **Não faz:** gerar orçamento automaticamente no POC (REQ-006 §7 — manual).

---

## Informações acumuladas

- Pacote de qualificação completo (REQ-002.5)
- Vínculo com um ou mais orçamentos (REQ-006, REQ-016.12)
- Histórico de mensagens e eventos de envio

---

## Como sair desta fase

| Se... | Efeito |
|-------|--------|
| Orçamento enviado; cliente satisfeito; PERG-016-010 com resposta negativa | `encerrar_atendimento` (motivo: concluido_pelo_cliente) → FASE-encerrado |
| Orçamento enviado; negócio perdido (REQ-006 desfecho) | `encerrar_atendimento` (motivo: conforme REQ-006 — não confundir com situação do atendimento) |
| Cliente abandona | `ir_para_fase` → FASE-encerrado-por-inatividade ou `encerrar_atendimento` (abandono) |
| Cliente pede novo produto/orçamento diferente | `ir_para_fase` → FASE-esclarecendo ou `criar_novo_atendimento` (decisão contextual) |
| Inatividade prolongada | `ir_para_fase` → FASE-encerrado-por-inatividade |

---

## Perguntas associadas

| ID | Quando dispara |
|----|----------------|
| PERG-016-010 | Após envio de orçamento ou demanda atendida (REQ-016.10) |

---

## Campos associados

Nenhum campo novo de qualificação — fase de operação comercial.

---

## REQs relacionados

- REQ-004, REQ-005.3, REQ-005.4
- REQ-006 (orçamento e desfecho comercial)
- REQ-010 (painel vendedor)
- REQ-016.10, REQ-016.12
- Brainstorming §4.2 item 4

---

## Notas para implementação

- Transição automática Finalizando → Criando Orçamento ao confirmar qualificação.
- Desfecho ganha/perdida pertence ao orçamento (REQ-006), não à fase.
