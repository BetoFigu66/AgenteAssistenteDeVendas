# CAMPO-modelo

**Título:** Modelo/especificação do produto  
**Tipo:** Coleta (lista fechada por tipo de produto)  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Qualquer tipo de produto Inforrel (catraca, relógio de ponto, câmera/CFTV, etc.)
- **Fase em que pergunta:** FASE-esclarecendo (pré-requisito para transição) ou FASE-finalizando
- **Obrigatório quando:** Cliente quer orçamento e o tipo de produto já foi identificado (REQ-002.3A)
- **REQ espelho:** REQ-002.3B

---

## Pergunta de coleta

> Qual modelo de {tipo_produto} você precisa?

_(Variantes por tipo de produto — o sistema oferece lista de opções válidas):_

- **Catraca**: "Temos os modelos Fit, Box, Pedestal, Giratória e Cancela. Qual deles?"
- **Relógio de ponto**: "O relógio seria cartográfico ou eletrônico? Se eletrônico: cartão de proximidade, barras, biometria ou reconhecimento facial?"
- **Câmeras / CFTV, Roteadores, Softwares**: "Qual modelo ou especificação?"

---

## Resposta esperada

- **Formato:** Nome de modelo do catálogo Inforrel ou descrição funcional reconhecível
- **Exemplos válidos:** "Fit", "biometria", "facial", "pedestal", "eletrônico com biometria"
- **Exemplos inválidos:** resposta genérica "qualquer um" sem indicação → REQ-002.21 pede esclarecimento; "não sei" → sistema oferece opções enumeradas

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Já informado em Esclarecendo | `nao_perguntar_de_novo` |
| Cliente não sabe qual modelo | Sistema oferece opções enumeradas por tipo de produto |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |
| Modelo não existe no catálogo | Registrar texto do cliente; sinalizar ao vendedor para validação manual |

---

## Efeito ao capturar

- `registrar_informacao` → campo `modelo_produto`
- Habilita perguntas dinâmicas dependentes do modelo (ex.: tecnologia do relógio)

---

## REQs relacionados

- REQ-002.3B, REQ-002.3A, REQ-002.4, REQ-002.17, REQ-002.21
