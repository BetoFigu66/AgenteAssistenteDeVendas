# CAMPO-quantidade

<!-- CLASSIFICACAO: ANDAMENTO -->

**Título:** Quantidade de equipamentos  
**Tipo:** Coleta (número ou faixa)  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Controle de acesso (catracas) sem software existente; outros produtos quando aplicável
- **Fase em que pergunta:** FASE-esclarecendo ou FASE-finalizando
- **Obrigatório quando:** Cliente solicita orçamento de controle de acesso e não tem software de controle (REQ-002.14A); opcional para catraca com software existente (REQ-002.15)
- **REQ espelho:** REQ-002.14A, REQ-002.15, REQ-002.3C

---

## Pergunta de coleta

> Quantas catracas/equipamentos você precisa?

_(Variante quando opcional — REQ-002.15): "Você sabe quantas catracas vai precisar? Se não souber agora, tudo bem, a gente segue."_

---

## Resposta esperada

- **Formato:** Número inteiro ou faixa (ex.: "entre 3 e 5")
- **Exemplos válidos:** "5", "umas 3", "entre 4 e 6", "não sei ainda"
- **Exemplos inválidos:** resposta textual sem número quando campo é obrigatório → REQ-002.21 pede esclarecimento

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Já informado em Esclarecendo | `nao_perguntar_de_novo` |
| "Não sei" + campo obrigatório (REQ-002.14A) | REQ-002.21: reformular — "Mesmo uma estimativa ajuda. Seria 1, 2-5, ou mais de 5?" |
| "Não sei" + campo opcional (REQ-002.15) | Aceitar; marcar como `nao_informado`; seguir fluxo |
| Formato flexível (REQ-002.6) | Aceitar faixa, aproximação ("umas 5"), texto descritivo ("para duas entradas") |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |

---

## Efeito ao capturar

- `registrar_informacao` → campo `quantidade_equipamentos`

---

## REQs relacionados

- REQ-002.14A, REQ-002.15, REQ-002.3C, REQ-002.6, REQ-002.17, REQ-002.21
