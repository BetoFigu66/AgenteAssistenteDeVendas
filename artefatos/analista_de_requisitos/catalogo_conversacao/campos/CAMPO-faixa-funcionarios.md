# CAMPO-faixa-funcionarios

**Título:** Faixa de funcionários/usuários  
**Tipo:** Coleta (número ou faixa)  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Controle de ponto (relógio de ponto) sem software existente; controle de acesso quando relevante para dimensionamento
- **Fase em que pergunta:** FASE-esclarecendo ou FASE-finalizando
- **Obrigatório quando:** Cliente solicita orçamento de relógio de ponto e não tem software de controle de ponto (REQ-002.14)
- **REQ espelho:** REQ-002.14, REQ-002.3C

---

## Pergunta de coleta

> Quantos funcionários vão usar o relógio de ponto?

_(Variante com faixa): "Pode ser um número aproximado — são até 50, de 50 a 200, ou mais de 200?"_

---

## Resposta esperada

- **Formato:** Número inteiro, faixa ou aproximação
- **Exemplos válidos:** "80", "uns 50", "entre 100 e 150", "mais de 200"
- **Exemplos inválidos:** resposta textual sem indicação numérica quando campo é obrigatório → REQ-002.21 pede esclarecimento

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Já informado em Esclarecendo | `nao_perguntar_de_novo` |
| "Não sei" + campo obrigatório (REQ-002.14) | REQ-002.21: reformular — "Mesmo uma estimativa ajuda. Seria até 50, de 50 a 200, ou mais de 200?" |
| Formato flexível (REQ-002.6) | Aceitar faixa, aproximação ("uns 80"), texto descritivo ("para uma equipe pequena" → pedir número) |
| Cliente tem software de ponto | Este campo **não** é perguntado (o software já dimensiona); marcar como `nao_aplicavel` |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |

---

## Efeito ao capturar

- `registrar_informacao` → campo `faixa_funcionarios`
- Direciona recomendação de modelo/capacidade do equipamento

---

## REQs relacionados

- REQ-002.14, REQ-002.3C, REQ-002.6, REQ-002.17, REQ-002.21
- CAMPO-software-ponto (dependência: só pergunta faixa se software = "nenhum")
