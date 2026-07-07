# CAMPO-contato

**Título:** Contato para envio do orçamento  
**Tipo:** Coleta (texto livre)  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Qualquer orçamento (PF ou PJ)
- **Fase em que pergunta:** FASE-finalizando
- **Obrigatório quando:** Cliente quer receber orçamento por e-mail ou outro canal (REQ-002.3C)
- **REQ espelho:** REQ-002.3C

---

## Pergunta de coleta

> Para qual e-mail posso enviar o orçamento? (ou prefere receber aqui mesmo pelo WhatsApp?)

---

## Resposta esperada

- **Formato:** E-mail válido ou indicação de que prefere WhatsApp
- **Exemplos válidos:** "joao@empresa.com", "pode mandar aqui mesmo", "meu e-mail é fulano@gmail.com"
- **Exemplos inválidos:** endereço de e-mail claramente malformado (sem @, sem domínio) → REQ-002.6 pede correção

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Cliente diz "aqui mesmo" / "por aqui" / "WhatsApp" | `registrar_informacao` → canal = whatsapp; não pedir e-mail |
| Cliente informa e-mail espontaneamente antes | `nao_perguntar_de_novo` |
| E-mail com formato inválido | REQ-002.6: pedir correção gentilmente |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |

---

## Efeito ao capturar

- `registrar_informacao` → campo `contato_orcamento` (e-mail ou whatsapp)

---

## REQs relacionados

- REQ-002.3C, REQ-002.5, REQ-002.6, REQ-002.17
