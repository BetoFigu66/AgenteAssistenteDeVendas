# CAMPO-<nome>

**Título:** (nome do dado para humanos)  
**Tipo:** Coleta (texto livre ou lista fechada)  
**Versão:** 0.1  
**Status:** Rascunho | Em revisão | Aprovado

---

## Contexto

- **Produto / situação:** (ex. Relógio de Ponto, qualquer PJ)
- **Fase em que pergunta:** FASE-xxx
- **Obrigatório quando:** (condição de negócio)
- **REQ espelho:** REQ-xxx

---

## Pergunta de coleta

> (Texto que o sistema envia ao cliente.)

---

## Resposta esperada

- **Formato:** (ex. CNPJ com 14 dígitos; nome de software; número ou faixa)
- **Exemplos válidos:** 
- **Exemplos inválidos:** (e o que o sistema faz — REQ-002.6 / REQ-002.21)

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Já informado em Esclarecendo | `nao_perguntar_de_novo` |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |
| | |

---

## Efeito ao capturar

- `registrar_informacao` → campo `{nome_campo}`
- (outros efeitos, ex. `confirmar_dados`, `fazer_pergunta` → CAMPO-xxx)

---

## REQs relacionados

- REQ-xxx
