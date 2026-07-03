# FASE-esclarecendo

**Nome exibido:** Esclarecendo  
**Versão:** 0.1  
**Status:** Rascunho

---

## Propósito

Cliente tira dúvidas sobre produtos, serviços e a empresa (Inforrel). O sistema responde via base de conhecimento e **acumula interesses** e informações espontâneas para usar depois em Finalizando — sem pressionar por dados de orçamento antes da hora.

---

## Situação do atendimento

- **Situação:** `ativo`
- **Fase terminal?** Não

---

## Como o cliente chega aqui

| Origem | Condição |
|--------|----------|
| Primeiro contato | Dúvida sobre produto/empresa (REQ-002.1 cat. 3) ou intenção ainda não explícita de orçamento |
| Novo atendimento qualificado | REQ-016.6 — criação automática ao detectar intenção de compra |
| Retorno após pausa | Cliente escolheu "Continuar" na PERG-016-009 |
| Retorno após continuidade | Após PERG-esclarecendo-confirmar-interesse (se ainda houver interesses a validar) |

---

## O que o sistema faz nesta fase

- Responde **perguntas sobre produto/serviço/empresa** via base de conhecimento (`consultar_base` — REQ-003, REQ-002.1B).
- **Registra interesses** mencionados pelo cliente: tipo de produto, modelo, software, quantidade aproximada — mesmo sem pedir formalmente.
- **Registra informações espontâneas** que seriam perguntadas em Finalizando (ex.: software de ponto já citado → `CAMPO-software-ponto` fica pré-preenchido).
- Aceita conversa **sem CNPJ/CPF** quando o assunto é só esclarecimento (REQ-002.1B).
- **Não faz:** insistir em documento fiscal ou campos de orçamento se o cliente fizer outra pergunta (regra CNPJ flexível — brainstorming §4.3, REQ-002.17).
- **Não faz:** bloquear resposta com saudação genérica pedindo CNPJ de imediato.

---

## Informações acumuladas

| Tipo | Exemplos | Uso posterior |
|------|----------|---------------|
| **Interesses** | "relógio biométrico", "catraca pedestal" | Resumo em perguntas de continuidade; contexto para vendedor |
| **Informações capturadas** | software mencionado, cidade, porte da empresa | Evitar repetir pergunta em Finalizando (`nao_perguntar_de_novo`) |
| **Pendências identificadas** | falta CNPJ, falta modelo exato | Lista de `CAMPO-xxx` a perguntar em Finalizando |

---

## Como sair desta fase

| Se... | Efeito |
|-------|--------|
| Cliente pede orçamento, quer comprar ou demonstra intenção clara de fechar negócio | `ir_para_fase` → FASE-finalizando |
| Cliente desiste explicitamente ("não quero mais", "desisti") | `encerrar_atendimento` (motivo: desistência) |
| Cliente pede atendimento humano ou situação crítica | `escalar_humano` (REQ-004) — pode permanecer em Esclarecendo ou ir para Criando Orçamento conforme REQ-004 |
| Inatividade configurada (timer) | `ir_para_fase` → FASE-encerrado-por-inatividade |
| Vendedor encerra manualmente pelo painel | `encerrar_atendimento` (motivo: decisão do vendedor — REQ-016) |

---

## Perguntas associadas

| ID | Quando dispara |
|----|----------------|
| PERG-esclarecendo-confirmar-interesse | Após "Continuar" na PERG-016-009, quando há interesses do atendimento anterior |
| PERG-016-010 | Ao final de um ciclo de dúvidas sem qualificação aberta (REQ-016.10) |

---

## Campos associados

Nesta fase os campos **não são obrigatórios**, mas podem ser **pré-capturados** se o cliente informar espontaneamente:

| ID | Obrigatório nesta fase? |
|----|------------------------|
| CAMPO-cnpj | Não — só obrigatório em Finalizando para PJ |
| CAMPO-software-ponto | Não — captura passiva se mencionado |

---

## REQs relacionados

- REQ-002.1, REQ-002.1B, REQ-002.17
- REQ-003 (respostas a dúvidas)
- REQ-016.6 (criação de atendimento)
- Brainstorming continuidade §4.2, §4.3

---

## Notas para implementação

- Fase inicial padrão para atendimentos novos com foco em esclarecimento.
- Separar `fase = esclarecendo` de `status = ativo` (brainstorming §5.2).
