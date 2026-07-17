# CAMPO-software-ponto

<!-- CLASSIFICACAO: ANDAMENTO -->

**Título:** Software de controle de ponto  
**Tipo:** Coleta  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Produto / situação:** Relógio de Ponto (controle de ponto)
- **Fase em que pergunta:** FASE-finalizando
- **Obrigatório quando:** Cliente solicita orçamento de relógio de ponto e integração com software é relevante para o modelo (REQ-002.3C)
- **REQ espelho:** REQ-002.3C, REQ-002.14

---

## Pergunta de coleta

> Qual software de ponto vocês usam hoje? (ex.: Domínio, Alterdata, TOTVS, ou **nenhum**)

---

## Resposta esperada

- **Formato:** Nome de software conhecido ou indicação de que não há software
- **Exemplos válidos:** "Domínio", "não temos sistema", "planilha Excel", "nenhum"
- **Exemplos inválidos:** resposta vaga "um sistema" → REQ-002.21 pede esclarecimento ou confirmação do nome

---

## Regras

| Regra | Comportamento |
|-------|---------------|
| Cliente já mencionou software em Esclarecendo | `nao_perguntar_de_novo`; opcionalmente `confirmar_dados`: "Você usa {software}, certo?" |
| Cliente responde **nenhum** / não tem software | `registrar_informacao`; `fazer_pergunta` → faixa de funcionários (REQ-002.14 — CAMPO-faixa-funcionarios, **pendente**) |
| Cliente faz pergunta sobre produto no meio da coleta | `consultar_base` + `retomar_qualificacao` (REQ-002.17) |
| Software conhecido da Inforrel com integração certificada | Registrar para vendedor; não bloquear fluxo se nome não estiver no catálogo interno |

---

## Efeito ao capturar

- `registrar_informacao` → campo `software_controle_ponto`
- Se "nenhum" → acionar regra REQ-002.14 (faixa de funcionários obrigatória)

---

## REQs relacionados

- REQ-002.3C, REQ-002.14, REQ-002.17
- Brainstorming §4.3 (exemplo atributo por produto)

---

## Pendências

- [ ] Criar `CAMPO-faixa-funcionarios` (desdobramento REQ-002.14)
- [ ] Kika: listar softwares comuns que Rita confirma no dia a dia (para opções enumeradas futuras)
