# CAMPO-endereco

**Título:** Endereço de entrega/instalação  
**Tipo:** Coleta (texto livre estruturado)  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Qualquer produto que exige entrega ou instalação
- **Fase em que pergunta:** FASE-finalizando
- **Obrigatório quando:** Cliente quer orçamento e o modo de entrega não é retirada (REQ-002.3D)
- **REQ espelho:** REQ-002.3D

---

## Pergunta de coleta

> Qual o endereço para entrega/instalação? (logradouro, número, bairro, cidade, UF e CEP)

_(Se o cliente informar parcialmente, o sistema pede os campos faltantes um a um.)_

---

## Resposta esperada

- **Formato:** Endereço completo ou parcial que o sistema pode completar via CEP
- **Exemplos válidos:** "Rua das Flores, 123, Centro, São Paulo-SP, 01001-000", "CEP 01001-000"
- **Exemplos inválidos:** apenas cidade sem rua/número → sistema pede complemento

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Cliente informa CEP | Sistema pode preencher logradouro/bairro/cidade/UF automaticamente (consulta via API); pedir número e complemento |
| Cliente informa "retirada" ou "vou buscar" | `registrar_informacao` → modo = retirada; **não** perguntar endereço |
| Já informado em Esclarecendo | `nao_perguntar_de_novo` |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |

---

## Efeito ao capturar

- `registrar_informacao` → campos `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `uf`, `cep`, `modo_entrega`
- Habilita cálculo de frete (evolução futura)

---

## REQs relacionados

- REQ-002.3D, REQ-002.4, REQ-002.5, REQ-002.17
