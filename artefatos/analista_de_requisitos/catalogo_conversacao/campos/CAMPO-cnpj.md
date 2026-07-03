# CAMPO-cnpj

**Título:** CNPJ da empresa  
**Tipo:** Coleta  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Pessoa Jurídica (PJ) em qualificação para orçamento
- **Fase em que pergunta:** FASE-finalizando (obrigatório); FASE-esclarecendo apenas se cliente informar espontaneamente
- **Obrigatório quando:** Cliente é PJ e quer orçamento (REQ-002.2A, REQ-002.5)
- **REQ espelho:** REQ-002.2, REQ-002.2A, REQ-001

---

## Pergunta de coleta

> Qual o CNPJ da empresa?

_(Variante após REQ-002.2A ambíguo: incluída na pergunta PF/PJ — "O orçamento é para uma **empresa** (CNPJ) ou para **pessoa física** (CPF)?")_

---

## Resposta esperada

- **Formato:** CNPJ com 14 dígitos (com ou sem máscara)
- **Exemplos válidos:** `12.345.678/0001-90`, `12345678000190`
- **Exemplos inválidos:** CPF no lugar de CNPJ, número com dígitos incorretos → REQ-002.6 pede correção; após 3 tentativas → REQ-002.21 escala humano

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Já informado em Esclarecendo | `nao_perguntar_de_novo`; `confirmar_dados` via REQ-001.4 se ainda não consultado |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) — **não insistir** no CNPJ na mesma mensagem |
| Esclarecendo — cliente só tira dúvidas | **Não perguntar** CNPJ (brainstorming §4.3, REQ-002.1B) |
| CNPJ extraído da mensagem inicial | `confirmar_dados` — confirmação do CNPJ via REQ-001.4 (Receita Federal), não duplicar REQ-002.16 |

---

## Efeito ao capturar

- `registrar_informacao` → campo `cnpj`
- Consulta Receita Federal (REQ-001.3)
- `confirmar_dados` com razão social retornada (REQ-001.4)

---

## REQs relacionados

- REQ-001, REQ-002.2, REQ-002.2A, REQ-002.6, REQ-002.16, REQ-002.17
- Brainstorming §4.3 (CNPJ flexível)
