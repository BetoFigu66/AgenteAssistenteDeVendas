# FASE-encerrado

**Nome exibido:** Encerrado  
**Versão:** 0.1  
**Status:** Rascunho

---

## Propósito

Atendimento **encerrado** — não há expectativa de continuação imediata. O histórico permanece disponível para consulta e possível reabertura futura.

---

## Situação do atendimento

- **Situação:** `encerrado`
- **Fase terminal?** Sim

---

## Como o cliente chega aqui

| Origem | Condição |
|--------|----------|
| Esclarecendo | Desistência explícita do cliente |
| Finalizando | Desistência ou abandono após REQ-002.22 |
| Criando Orçamento | Orçamento enviado + PERG-016-010 com despedida; ou desfecho operacional |
| Encerrado por Inatividade | Abandono 72h (REQ-002.22) |
| Vendedor | Encerramento manual pelo painel (REQ-016) |

---

## O que o sistema faz nesta fase

- **Não inicia** novo ciclo de qualificação automaticamente.
- Se cliente enviar mensagem **dentro da janela** REQ-016.7 → pode `reabrir_atendimento` ou `fazer_pergunta` → PERG-016-009.
- Se cliente enviar mensagem **fora da janela** → `criar_novo_atendimento` ou PERG-016-009 conforme matriz REQ-016.7.
- Mensagens estritamente sociais ("obrigado") em atendimento encerrado **não** criam atendimento novo (REQ-016.13).
- Preserva histórico e dados capturados (REQ-002.22).

---

## Motivos de encerramento (REQ-016.4)

| Motivo | Origem típica |
|--------|---------------|
| `concluido_pelo_cliente` | PERG-016-010 — "não preciso de mais nada" |
| `abandono` | REQ-002.22 — 72h sem resposta após reengajamento |
| `desistencia` | Cliente desiste em Esclarecendo ou Finalizando |
| Decisão do vendedor | Painel REQ-010 / REQ-016.8 |

> Desfecho comercial **ganha/perdida** pertence ao orçamento (REQ-006), não a este motivo.

---

## Como sair desta fase

| Se... | Efeito |
|-------|--------|
| Cliente retorna e escolhe continuar (PERG-016-009) | `reabrir_atendimento` → `ir_para_fase` FASE-esclarecendo (ou fase onde parou) |
| Cliente retorna e escolhe novo pedido | `criar_novo_atendimento` |
| Vendedor reabre manualmente | `reabrir_atendimento` (REQ-016.8) |
| _(permanece encerrado)_ | Nenhuma ação até novo contato |

---

## Perguntas associadas

| ID | Quando dispara |
|----|----------------|
| PERG-016-009 | Novo contato após encerramento, conforme REQ-016.7 |

---

## Campos associados

Nenhum — fase terminal.

---

## REQs relacionados

- REQ-016.4, REQ-016.7, REQ-016.8, REQ-016.9, REQ-016.13
- REQ-002.22
- REQ-006 (desfecho comercial separado)
- Brainstorming §4.2 item 5

---

## Notas para implementação

- `status = encerrado` + `fase = encerrado` + `motivo_encerramento` preenchido.
- Registrar eventos auditáveis: `atendimento_encerrado`, `atendimento_reaberto` (REQ-016.17).
