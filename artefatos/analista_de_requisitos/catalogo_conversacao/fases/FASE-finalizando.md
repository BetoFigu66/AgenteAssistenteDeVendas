# FASE-finalizando

**Nome exibido:** Finalizando  
**Versão:** 0.1  
**Status:** Rascunho

---

## Propósito

Cliente decidiu que quer orçamento. O sistema **coleta as informações necessárias** (campos pendentes), confirma o entendimento e prepara o handoff para o vendedor elaborar o orçamento.

---

## Situação do atendimento

- **Situação:** `ativo`
- **Fase terminal?** Não

---

## Como o cliente chega aqui

| Origem | Condição |
|--------|----------|
| Esclarecendo | Cliente manifesta intenção de orçamento/compra (REQ-002.1 cat. 1) |
| Retorno direto | Mensagem inicial já é pedido de orçamento com dados (REQ-002.2) |

---

## O que o sistema faz nesta fase

- Identifica **campos pendentes** com base no produto e no tipo de cliente (PF/PJ) — REQ-002.3 a REQ-002.5.
- Faz **perguntas de coleta** (`CAMPO-xxx`) apenas para o que ainda falta — REQ-002.4.
- Aplica **`nao_perguntar_de_novo`** para dados já capturados em Esclarecendo.
- Se cliente intercalar **dúvida sobre produto**, responde via REQ-003 e **retoma** a última pergunta pendente — REQ-002.17.
- **Ecoa dados extraídos** da mensagem inicial para confirmação — REQ-002.16 (CNPJ confirmado via REQ-001.4).
- Ao completar todos os campos, apresenta **resumo do pedido** e pede confirmação — REQ-002.5.
- **CNPJ/CPF tornam-se obrigatórios** nesta fase (não em Esclarecendo) — brainstorming §4.3.

---

## Informações acumuladas

Todos os campos do REQ-002.5 conforme PF ou PJ:

- Documento fiscal (CNPJ ou CPF)
- Tipo e modelo de produto
- Software de integração (quando aplicável)
- Quantidade / faixa de pessoas
- Endereço de entrega/instalação
- Contato para envio do orçamento
- Nome do solicitante (obrigatório PF)

---

## Como sair desta fase

| Se... | Efeito |
|-------|--------|
| Cliente confirma resumo; qualificação completa | `ir_para_fase` → FASE-criando-orcamento; `notificar_vendedor` |
| Cliente desiste durante a coleta | `encerrar_atendimento` (motivo: desistência) |
| Cliente pede humano | `escalar_humano` |
| Esclarecimento esgotado sem capturar campo (REQ-002.21) | `escalar_humano` preservando dados válidos |
| Inatividade 24h durante coleta | `fazer_pergunta` → PERG-002-022; se abandono total → ver REQ-002.22 |
| Cliente volta a só tirar dúvidas sem fechar orçamento | Permanece ou `ir_para_fase` → FASE-esclarecendo (decisão Kika — registrar em DEC se necessário) |

---

## Perguntas associadas

| ID | Quando dispara |
|----|----------------|
| PERG-002-022 | 24h sem resposta durante coleta de campos |
| (resumo/confirmação) | Todos os campos obrigatórios preenchidos — REQ-002.5 |

---

## Campos associados

| ID | Obrigatório nesta fase? |
|----|------------------------|
| CAMPO-cnpj | Sim, para PJ (após REQ-002.2A) |
| CAMPO-software-ponto | Condicional — Relógio de Ponto |
| CAMPO-tipo-produto | Sim — REQ-002.3A |
| CAMPO-modelo-produto | Sim — REQ-002.3B |
| CAMPO-endereco | Sim — REQ-002.3D |
| CAMPO-contato-orcamento | Sim — REQ-002.3C |
| _(demais em indice.md — pendente Kika)_ | |

---

## REQs relacionados

- REQ-002.2 a REQ-002.6, REQ-002.14, REQ-002.14A, REQ-002.15, REQ-002.16, REQ-002.17, REQ-002.21
- REQ-001 (CNPJ), REQ-015 (CPF)
- Brainstorming §4.2 item 3, §4.3

---

## Notas para implementação

- Ordem das perguntas dinâmicas é contextual (REQ-002.4) — catálogo lista campos, não ordem fixa.
- Motor `campos_pendentes()` deve consultar produto + dados já capturados.
