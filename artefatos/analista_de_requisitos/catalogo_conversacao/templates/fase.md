# FASE-<nome-curto>

**Nome exibido:** (nome para humanos, ex. Esclarecendo)  
**Versão:** 0.1  
**Status:** Rascunho | Em revisão | Aprovado

---

## Propósito

(Uma frase: o que o cliente e o sistema estão fazendo nesta fase.)

---

## Situação do atendimento

- **Situação:** `ativo` | `encerrado`
- **Fase terminal?** Sim | Não

---

## Como o cliente chega aqui

| Origem | Condição |
|--------|----------|
| (ex. Primeiro contato) | (ex. Intenção de compra ou dúvida — REQ-002.1) |
| | |

---

## O que o sistema faz nesta fase

- (Comportamento 1 — referenciar REQ se aplicável)
- (Comportamento 2)
- **Não faz:** (ex. não insistir em CNPJ se cliente fizer outra pergunta)

---

## Informações acumuladas

(O que o sistema vai guardando para usar depois — interesses, campos já capturados, etc.)

---

## Como sair desta fase

| Se... | Efeito |
|-------|--------|
| | `ir_para_fase` → |
| | `encerrar_atendimento` (motivo: ) |

---

## Perguntas associadas

| ID | Quando dispara |
|----|----------------|
| PERG-xxx | |

---

## Campos associados

| ID | Obrigatório nesta fase? |
|----|------------------------|
| CAMPO-xxx | Sim / Não / Condicional |

---

## REQs relacionados

- REQ-xxx

---

## Notas para implementação

_(Opcional — a analista pode deixar em branco; implementador preenche na tradução para código.)_
