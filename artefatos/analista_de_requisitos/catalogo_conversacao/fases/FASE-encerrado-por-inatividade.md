# FASE-encerrado-por-inatividade

<!-- CLASSIFICACAO: ANDAMENTO -->

**Nome exibido:** Encerrado por Inatividade  
**Versão:** 0.1  
**Status:** Rascunho

---

## Propósito

Cliente parou de interagir por um período configurável. O atendimento **não está encerrado definitivamente** — aguarda retorno do cliente para perguntar se deseja continuar ou iniciar pedido novo.

---

## Situação do atendimento

- **Situação:** `ativo` (não confundir com `encerrado` — ver nota abaixo)
- **Fase terminal?** Não

> **Nota:** O nome contém "encerrado", mas a **situação** do atendimento permanece `ativo`. Apenas a **fase** indica suspensão por inatividade. Decisão Kika (2026-07-06): manter o nome atual — equipe já está acostumada com o termo.

---

## Como o cliente chega aqui

| Origem | Condição |
|--------|----------|
| Esclarecendo | Timer de inatividade (parâmetro configurável — ex. 1 dia, 1 semana) |
| Finalizando | Timer de inatividade durante coleta de campos |
| Criando Orçamento | Timer de inatividade aguardando vendedor/cliente (se aplicável) |

---

## O que o sistema faz nesta fase

- **Não envia** mensagens proativas de cobrança (salvo regras específicas REQ-002.22 em qualificação — ver PERG-002-022).
- **Preserva** todos os dados e interesses já capturados.
- Quando o cliente **retorna**, dispara PERG-016-009 (continuidade) ou PERG-002-022 conforme contexto.
- Registra `ultima_mensagem_at` para cálculo de janelas (REQ-016.7).

---

## Informações acumuladas

Mantém snapshot do atendimento no momento da inatividade: fase anterior, interesses, campos parciais.

---

## Como sair desta fase

| Se... | Efeito |
|-------|--------|
| Cliente envia nova mensagem — atendimento `ativo` (dentro ou fora da janela) | Continuação automática no mesmo atendimento (sem pergunta); retorna à fase anterior |
| Cliente envia nova mensagem — atendimento `encerrado`, **dentro** da janela (REQ-016.7) | `fazer_pergunta` → PERG-016-009 (default sugerido = continuar) |
| Cliente envia nova mensagem — atendimento `encerrado`, **fora** da janela (REQ-016.7) | `fazer_pergunta` → PERG-016-009 (default sugerido = novo pedido) |
| Timer de abandono definitivo (REQ-002.22 — `abandono_total_horas` após reengajamento) | `encerrar_atendimento` (motivo: abandono) → FASE-encerrado |
| Vendedor encerra manualmente | `encerrar_atendimento` |

---

## Perguntas associadas

| ID | Quando dispara |
|----|----------------|
| PERG-016-009 | Cliente retorna após pausa (matriz REQ-016.7) |
| PERG-002-022 | Reengajamento durante qualificação antes de transitar para esta fase |

---

## Campos associados

Nenhum campo novo é coletado nesta fase.

---

## REQs relacionados

- REQ-002.22
- REQ-016.7, REQ-016.9
- REQ-014 (parâmetros de tempo)
- Brainstorming §4.2 item 2, §4.4

---

## Notas para implementação

- Implementar como `fase = encerrado_por_inatividade` com `status = ativo`.
- Prazos: brainstorming menciona 1 dia / 1 semana / 1 mês como configuráveis; REQ-002.22 usa 24h + 72h para abandono em qualificação — alinhar parâmetros em REQ-014.
