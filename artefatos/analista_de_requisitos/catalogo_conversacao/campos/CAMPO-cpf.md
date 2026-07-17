# CAMPO-cpf

<!-- CLASSIFICACAO: ANDAMENTO -->

**Título:** CPF do solicitante  
**Tipo:** Coleta  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Pessoa Física (PF) em qualificação para orçamento
- **Fase em que pergunta:** FASE-finalizando (obrigatório); FASE-esclarecendo apenas se cliente informar espontaneamente
- **Obrigatório quando:** Cliente é PF e quer orçamento (REQ-002.2A, REQ-002.5)
- **REQ espelho:** REQ-002.2, REQ-002.2A, REQ-015

---

## Pergunta de coleta

> Qual o CPF?

_(Variante após REQ-002.2A ambíguo: incluída na pergunta PF/PJ — "O orçamento é para uma **empresa** (CNPJ) ou para **pessoa física** (CPF)?")_

---

## Resposta esperada

- **Formato:** CPF com 11 dígitos (com ou sem máscara)
- **Exemplos válidos:** `123.456.789-09`, `12345678909`
- **Exemplos inválidos:** CNPJ no lugar de CPF, dígitos verificadores incorretos → REQ-002.6 pede correção; após 3 tentativas → REQ-002.21 escala humano

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Já informado em Esclarecendo | `nao_perguntar_de_novo`; `confirmar_dados` via REQ-015.3 se ainda não consultado |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) — **não insistir** no CPF na mesma mensagem |
| Esclarecendo — cliente só tira dúvidas | **Não perguntar** CPF (brainstorming §4.3, REQ-002.1B) |
| CPF extraído da mensagem inicial | `confirmar_dados` — validação e consulta de débitos via REQ-015.2/REQ-015.3 |

---

## Efeito ao capturar

- `registrar_informacao` → campo `cpf`
- Validação de dígitos verificadores (REQ-015.2)
- Consulta de débitos, se configurada (REQ-015.3)
- `confirmar_dados` com nome do solicitante (REQ-002.3C) quando aplicável

---

## REQs relacionados

- REQ-015, REQ-002.2, REQ-002.2A, REQ-002.3C, REQ-002.6, REQ-002.17
- Brainstorming §4.3 (CNPJ/CPF flexível)
