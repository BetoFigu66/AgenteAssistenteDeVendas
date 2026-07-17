# Revisão de Alinhamento: Catálogo de Conversação × REQs Formais

<!-- CLASSIFICACAO: ANDAMENTO -->

**Versão:** 0.1  
**Data:** 2026-07-04  
**Autor:** Cascade (rascunho para revisão da Kika)  
**Status:** Rascunho  

---

## 1. Escopo

Revisão cruzada entre os artefatos do `catalogo_conversacao` (fases, perguntas, campos) e os requisitos formais `REQ-002`, `REQ-016`, `REQ-004`, `REQ-007` e `REQ-014`. Objetivo: identificar inconsistências, gaps e conceitos novos gerados pelo catálogo que precisam ser espelhados nos REQs.

---

## 2. Inventário do catálogo

### Fases

| ID | REQ principal | Observações |
|----|---------------|-------------|
| FASE-esclarecendo | REQ-002.1B, REQ-002.17 | Acumula interesses; novo conceito de **pré-requisitos para ir a Finalizando** |
| FASE-finalizando | REQ-002.2, REQ-002.3, REQ-002.5 | Coleta de campos; origem "Primeiro contato com todos os dados" |
| FASE-criando-orcamento | REQ-006, REQ-016.12 | Fase operacional/comercial; vendedor elabora orçamento |
| FASE-encerrado-por-inatividade | REQ-002.22, REQ-016.7 | Nome pode gerar confusão com situação `encerrado` — pendente renomear para "Suspenso" |
| FASE-encerrado | REQ-016.4 | Fase terminal; motivo `desistencia` aparece no catálogo mas não no REQ-016.4 |

### Perguntas de decisão

| ID | REQ espelho | Status |
|----|-------------|--------|
| PERG-016-009 | REQ-016.9 | Catálogo detalha sinônimos e efeitos; REQ contém texto base |
| PERG-016-010 | REQ-016.10 | Catálogo detalha opções; REQ descreve comportamento |
| PERG-002-022 | REQ-002.22 | Catálogo detalha reengajamento; REQ menciona a mensagem |
| PERG-esclarecendo-confirmar-interesse | Brainstorming §4.4 | **Sem REQ formal** — precisa de decisão Kika |

### Campos

| ID | REQ espelho | Status |
|----|-------------|--------|
| CAMPO-cnpj | REQ-002.2, REQ-001 | OK |
| CAMPO-software-ponto | REQ-002.3C, REQ-002.14 | OK |
| CAMPO-cpf | **Não existe** | Aparece em FASE-finalizando.md; precisa criar ficha |
| Demais campos (modelo, endereço, contato, etc.) | REQ-002.3B, REQ-002.3C, REQ-002.3D | **Não existem** no catálogo; FASE-finalizando os lista como associados |

---

## 3. Gaps e inconsistências

### 3.1 Conceitos novos no catálogo sem espelho em REQ

- **Pré-requisitos para sair de Esclarecendo** (`modelo + quantidade + software`) ✅ Ajustado
  - Local: `FASE-esclarecendo.md` — Informações acumuladas
  - Ajuste aplicado: criado REQ-002.1C em `REQ-002-fluxo-conversacional-guiado.md` v1.28, formalizando a transição de FASE-esclarecendo para FASE-finalizando com dados mínimos.

- **Origem "Primeiro contato com todos os dados"** ✅ Ajustado
  - Local: `FASE-finalizando.md` — Como o cliente chega aqui
  - Ajuste aplicado: REQ-002.2 v1.28 agora prevê entrada direta em FASE-finalizando quando a mensagem inicial já contém os dados mínimos.

- **Eco de dados extraídos vs. resumo final** ✅ Ajustado
  - Local: `FASE-finalizando.md` — O que o sistema faz
  - Ajuste aplicado: REQ-002.16 e REQ-002.5 v1.28 explicitam a diferença entre eco inicial (mensagem inicial) e resumo final (qualificação completa).

### 3.2 Referências do catálogo ausentes nos REQs

- `PERG-016-009`, `PERG-016-010`, `PERG-002-022` ✅ Ajustado em REQ-002
  - REQ-002.1C v1.28 referencia FASE-esclarecendo, FASE-finalizando, PERG-002-022, PERG-016-009 e PERG-016-010.
  - REQ-002.22 v1.28 referencia PERG-002-022.
  - REQ-002.17 v1.28 referencia as regras de Desvios e robustez das PERGs.
  - Ainda falta referenciar os IDs do catálogo em REQ-016 (PERG-016-009, PERG-016-010).

- `CAMPO-cpf` ✅ Ajustado
  - Ficha criada em `campos/CAMPO-cpf.md` (v0.1) espelhando REQ-002.2A e REQ-015.
  - Incluído no índice do catálogo.

- Demais campos de qualificação (modelo, endereço, contato, quantidade, faixa de funcionários) ainda não têm fichas no catálogo.
  - Recomendação: desdobrar gradualmente conforme prioridade da Kika.

### 3.3 Inconsistências entre FASE e REQ

- **Motivo de encerramento `desistencia`** ✅ Ajustado
  - Local: `FASE-encerrado.md`
  - REQ-016.4 lista: `concluido_pelo_cliente`, `abandono`, `manual_vendedor`.
  - Ajuste aplicado: `desistencia` incluído em REQ-016.4 v2.1 (04/07/2026). FASE-encerrado.md já estava coerente.

- **FASE-encerrado-por-inatividade × REQ-016.7**
  - FASE diz: "Cliente envia nova mensagem (dentro ou fora da janela) → PERG-016-009".
  - REQ-016.7 diz: fora da janela + atendimento `encerrado` → cria novo atendimento **sem pergunta**.
  - Recomendação: alinhar FASE com matriz do REQ; manter PERG-016-009 apenas para casos onde o sistema deve perguntar.

- **Transição FASE-criando-orcamento → FASE-encerrado**
  - FASE-criando-orcamento.md diz: "Orçamento enviado + PERG-016-010 com despedida".
  - REQ-016.10 diz: resposta negativa → `encerrado`.
  - Observação: coerente, mas o catálogo deixa mais claro que a pergunta de fechamento é o gatilho.

### 3.4 Perguntas sem REQ formal

- **PERG-esclarecendo-confirmar-interesse**
  - Baseada em Brainstorming §4.4; não há REQ espelho.
  - Recomendação: Kika decide se vira sub-requisito de REQ-016 (continuidade) ou de REQ-002 (qualificação). Sugestão: REQ-016.9A ou REQ-002.18A.

### 3.5 Padrões de robustez não espelhados em todos os REQs

- A seção **Desvios e robustez** agora é padrão nas PERGs, tratando:
  - Pergunta sobre produto embutida (REQ-002.17 / Caso 3)
  - Citação do WhatsApp (REQ-002.1A Caso 4)
  - Insatisfação/escalonamento (REQ-004.7 / REQ-007)
- Recomendação: garantir que REQ-002, REQ-004 e REQ-007 continuem cobrindo esses mecanismos; o catálogo apenas os referencia.

---

## 4. Recomendações de ajuste

### Prioridade alta

1. ✅ **Criar `campos/CAMPO-cpf.md`** — Ajustado (v0.1).
2. ✅ **Adicionar `desistencia` em REQ-016.4** — Ajustado em REQ-016 v2.1.
3. ✅ **Alinhar FASE-encerrado-por-inatividade.md com REQ-016.7** — Ajustado em REQ-016 v2.3: célula `encerrado` + `fora da janela` agora pergunta (com resumo) em vez de criar direto. FASE alinhada.
4. ✅ **Espelhar "pré-requisitos para sair de Esclarecendo"** em REQ-002 — Ajustado via REQ-002.1C v1.28.
5. ✅ **Formalizar `PERG-esclarecendo-confirmar-interesse`** — Incorporado como passo pós-resposta "Continuar" dentro do REQ-016.9 (v2.5). Decisão Kika: não criar REQ separado.

### Prioridade média

6. ✅ **Referenciar IDs do catálogo no REQ-002** — Ajustado em v1.28.
7. ✅ **Parametrizar tempos de abandono de conversa** (REQ-002.22) — Ajustado em REQ-002 v1.30 + REQ-014.2D v1.3 (`abandono_inatividade_horas`, `abandono_total_horas`, `abandono_reengajamento_max_mensagens`).
8. ✅ **Referenciar IDs do catálogo no REQ-016** (PERG-016-009, PERG-016-010) — Ajustado em REQ-016 v2.2.
9. ✅ **Criar fichas de campo pendentes** — Criados: `CAMPO-modelo`, `CAMPO-endereco`, `CAMPO-contato`, `CAMPO-quantidade`, `CAMPO-faixa-funcionarios` (todos v0.1).
10. ✅ **Decidir nome da fase `FASE-encerrado-por-inatividade`** — Decisão Kika: manter o nome atual. Equipe já está acostumada com o termo.
11. ✅ **Criar `PERG-002-2A` (PF vs PJ)** — Criado como ficha no catálogo (`PERG-002-2A.md` v0.1). Decisão Kika: manter padrão uniforme com as outras PERGs.

### Prioridade baixa

12. ✅ **Reforçar distinção "eco inicial" vs. "resumo final"** em REQ-002.16/REQ-002.5 — Ajustado em v1.28.
13. ✅ **Adicionar origem "Primeiro contato com todos os dados"** em REQ-002.2 — Ajustado em v1.28.

---

## 5. Tabela de rastreabilidade resumida

| Catálogo | REQ espelho | Alinhamento |
|----------|-------------|---------------|
| FASE-esclarecendo | REQ-002.1B, REQ-002.1C, REQ-002.17 | ✅ coerente |
| FASE-finalizando | REQ-002.2, REQ-002.3, REQ-002.5, REQ-002.16 | ✅ coerente |
| FASE-criando-orcamento | REQ-006, REQ-016.12 | ✅ coerente |
| FASE-encerrado-por-inatividade | REQ-002.22, REQ-014.2D, REQ-016.7 | ✅ coerente (matriz alinhada em v2.3; nome mantido) |
| FASE-encerrado | REQ-016.4 | ✅ coerente (desistencia adicionado) |
| PERG-016-009 | REQ-016.9 | ✅ coerente (referenciado em REQ-016 v2.2) |
| PERG-016-010 | REQ-016.10 | ✅ coerente (referenciado em REQ-016 v2.2) |
| PERG-002-022 | REQ-002.22 | ✅ coerente (referenciado em REQ-002.1C e REQ-002.22) |
| PERG-esclarecendo-confirmar-interesse | REQ-016.9 (v2.5) | ✅ coerente (incorporado como sub-passo) |
| CAMPO-cnpj | REQ-002.2, REQ-001 | ✅ coerente |
| CAMPO-software-ponto | REQ-002.3C, REQ-002.14 | ✅ coerente |
| CAMPO-cpf | REQ-002.2A, REQ-015 | ✅ coerente |

---

## 6. Pendências para decisão da Kika

- [x] ~~**PERG-esclarecendo-confirmar-interesse** vira REQ? Qual ID?~~ Incorporado dentro do REQ-016.9 (v2.5).
- [x] ~~Renomear `FASE-encerrado-por-inatividade` para "Suspenso"?~~ Decisão: manter nome atual.
- [x] ~~Alinhar matriz de janela de `FASE-encerrado-por-inatividade.md` com `REQ-016.7`.~~ Ajustado em REQ-016 v2.3.
- [x] ~~Prioridade de criação das fichas de campo pendentes (modelo, endereço, contato, quantidade, faixa-funcionarios).~~ Criados em 06/07/2026.
- [x] ~~Criar `PERG-002-2A` (PF vs PJ) ou manter só como CAMPO/coleta.~~ Criado como PERG-002-2A.md (v0.1).
