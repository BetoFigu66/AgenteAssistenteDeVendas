# Tarefa — Calibração do Classificador de Intenções (REQ-002.1 / REQ-002.1A)

**De:** Kika (Analista de Requisitos)  
**Para:** Beto (Implementador)  
**Data:** 2026-06-03  
**Origem:** bug observado — pergunta `"Quais produtos a Inforrel vende?"` foi respondida com "não entendi" mesmo havendo Q&A correspondente na base.  
**Requisitos relacionados:** REQ-002.1, REQ-002.1A (novo), REQ-003, REQ-005.6, REQ-014.

---

## 1. Resumo do problema

O classificador da porta de entrada (REQ-002.1) errou em uma pergunta canônica que deveria cair na **categoria 3** (pergunta sobre produto/serviço/empresa) e ser delegada ao REQ-003 (RAG/Q&A). Em vez disso, devolveu fallback genérico ao cliente.

A correção atual aplicada — **"sempre consultar Q&A em toda mensagem"** — é um workaround que resolve o sintoma mas:

- Dilui a responsabilidade do classificador (anti-padrão arquitetural);
- Aumenta custo e latência em mensagens corretamente classificadas;
- Pode poluir respostas de qualificação em curso (categoria 2) com trechos irrelevantes da base;
- Torna o roteamento não-auditável.

A solução correta tem **duas frentes em paralelo**: calibrar o classificador (causa raiz) e formalizar fallback condicional no requisito (já feito — REQ-002.1A).

---

## 2. Próximos passos (handoff)

### Passo 1 — Reverter o "sempre consulta Q&A"

Voltar o código a respeitar o roteamento por categoria do REQ-002.1. O fallback para REQ-003 deve passar a ser **condicional** conforme REQ-002.1A.

### Passo 2 — Expor confiança do classificador

O retorno do classificador deve passar a conter, além da categoria, um indicador numérico ou enumerado de confiança (`confianca_classificacao`). Sem isso, REQ-002.1A não tem como decidir se aciona fallback.

Sugestão mínima: campo float em `[0.0, 1.0]` ou enum `alta` / `media` / `baixa`. Documentar no schema do retorno.

### Passo 3 — Implementar fallback condicional (REQ-002.1A)

Implementar os 3 casos do REQ-002.1A:

- **Caso 1 (confiança alta):** rota direta para o fluxo da categoria. Sem consulta extra.
- **Caso 2 (confiança baixa ou "não identificado"):** tentar REQ-003 antes de devolver "não entendi"; se REQ-003 também não retornar resposta confiável, segue REQ-002.21 (esclarecimento) e, esgotado, REQ-004.9 (escalar humano).
- **Caso 3 (heurística opcional):** confiança alta em outra categoria + forma interrogativa de produto pode acionar REQ-003 como complemento. **Nunca** aplicar a respostas de qualificação em curso (categoria 2).

### Passo 4 — Calibrar o prompt do classificador (causa raiz)

#### 4.1 Princípio de distinção a deixar explícito no prompt

Na prática, a confusão acontece entre **categoria 1** (intenção de compra/orçamento) e **categoria 3** (pergunta sobre produto/empresa) quando ambas mencionam "produto". Sugiro a regra:

- **Verbo de posse/oferta da empresa** ("vende", "vendem", "trabalha com", "tem", "fornece", "faz", "atende", "comercializa") + objeto produto → **categoria 3**.
- **Verbo de compra/desejo do cliente** ("quero", "preciso", "gostaria de", "tô precisando", "vou comprar", "fechar") + quantidade explícita ou contexto de uso → **categoria 1**.
- Forma puramente **interrogativa de catálogo** ("quais", "que tipos de", "vocês têm", "tem alguma...") → **categoria 3**.

#### 4.2 Exemplos canônicos para incluir no prompt

Recomendo embutir uma seção `## Exemplos` no prompt do classificador, com pelo menos os pares abaixo:

**Categoria 1 — Intenção de compra/orçamento (mensagem inicial):**
- `"Preciso de orçamento para 5 catracas"` → categoria 1
- `"Quero comprar um relógio de ponto biométrico"` → categoria 1
- `"Tô precisando de uma cancela para meu estacionamento"` → categoria 1
- `"Bom dia, gostaria de orçar 10 leitores faciais"` → categoria 1

**Categoria 2 — Resposta a pergunta de qualificação em curso:**
- `"5"` (após pergunta "qual a quantidade?") → categoria 2
- `"São Paulo"` (após pergunta "qual a cidade?") → categoria 2
- `"00.000.000/0001-91"` (após pergunta "qual o CNPJ?") → categoria 2

**Categoria 3 — Pergunta sobre produto/serviço/empresa:**
- `"Quais produtos a Inforrel vende?"` → categoria 3
- `"Vocês trabalham com câmeras?"` → categoria 3
- `"Que tipos de catraca vocês têm?"` → categoria 3
- `"Qual o prazo de entrega?"` → categoria 3
- `"A Inforrel tem assistência técnica?"` → categoria 3
- `"Quanto custa a catraca pedestal?"` → categoria 3 (pergunta de preço, não intenção de compra)

**Categoria 4 — Atendimento humano / situação crítica:**
- `"Quero falar com um vendedor humano"` → categoria 4
- `"Estou muito insatisfeito com o atendimento"` → categoria 4
- `"Preciso reclamar do produto que recebi"` → categoria 4

#### 4.3 Casos limítrofes que valem mencionar no prompt

- `"Vocês têm catracas? Preciso de 5"` → **categoria 1** (a intenção de compra com quantidade prevalece sobre a pergunta inicial).
- `"Catracas"` (mensagem solta, sem verbo) → **categoria 3** se confiança alta na interpretação como "vocês têm catracas?"; caso contrário, baixa confiança e cai no fallback do REQ-002.1A.
- `"Quero saber sobre catracas"` → **categoria 3** (interesse em informação, não compra explícita).

#### 4.4 Saída esperada

O classificador deve retornar, para cada mensagem:

```json
{
  "categoria": 1 | 2 | 3 | 4 | "nao_identificado",
  "confianca": 0.0 a 1.0,
  "justificativa_curta": "string opcional, útil para auditoria"
}
```

A `justificativa_curta` pode ser exibida no modal de raciocínio (REQ-005.6) e ajuda a entender o motivo da classificação em casos de bug.

### Passo 5 — Auditoria (REQ-005.6)

Cada mensagem processada deve registrar no modal de raciocínio:

- Categoria escolhida pelo classificador.
- Confiança da classificação.
- Se houve fallback para REQ-003 (sim/não).
- Resultado do fallback (resposta entregue / pediu esclarecimento / escalou).

Sem essa instrumentação, próximos bugs vão ficar invisíveis — voltamos a depender de o cliente reclamar para descobrir.

### Passo 6 — Validação

Após implementação, executar os cenários de teste já criados em `artefatos/qa/cenarios_teste_funcionais_sprint02.md`:

- **CTF-002-08** — pergunta "Quais produtos a Inforrel vende?" deve responder pela Q&A com confiança alta, sem fallback.
- **CTF-002-09** — mensagem ambígua aciona fallback via REQ-003 quando a confiança é baixa; o sistema nunca devolve "não entendi" sem ter tentado.
- **CTF-002-10** — anti-padrão: resposta de qualificação ("5") **não** consulta a base; valida que o fix do "sempre Q&A" foi removido.

---

## 3. Por que esta abordagem é melhor que "sempre consultar Q&A"

| Aspecto | "Sempre consulta Q&A" | Calibrar + REQ-002.1A |
|---|---|---|
| Resolve o caso `"Quais produtos a Inforrel vende?"` | Sim, por acaso | Sim, por design |
| Custo por mensagem | Alto (RAG sempre roda) | Baixo (RAG só roda quando necessário) |
| Latência por mensagem | Alta sempre | Baixa em > 90% dos casos |
| Risco de poluir resposta de qualificação | Alto | Zero (proibido pelo anti-padrão) |
| Auditável | Não | Sim (cada decisão registrada) |
| Resolve causa raiz | Não, mascara | Sim, calibra o classificador |
| Aderente à arquitetura REQ-002.1 (porta de entrada) | Não, dilui | Sim, preserva |

---

## 4. Estimativa

| Atividade | Horas |
|-----------|-------|
| Reverter o "sempre Q&A" | 1h |
| Expor confiança no retorno do classificador | 2h |
| Implementar fallback condicional (REQ-002.1A) | 4h |
| Atualizar prompt do classificador com exemplos | 2h |
| Adicionar auditoria de fallback no modal (REQ-005.6) | 2h |
| Rodar e validar CTF-002-08, CTF-002-09, CTF-002-10 | 2h |
| **Total** | **13h** |

---

## 5. Referências

- `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` — REQ-002.1 (classificação) e REQ-002.1A (fallback condicional, novo na v1.20).
- `artefatos/requisitos_formais/REQ-003-respostas-automaticas-rag.md` — base de respostas automáticas (Q&A + RAG).
- `artefatos/requisitos_formais/REQ-005-registro-interacoes-historico.md` — REQ-005.6 (auditoria de respostas da IA).
- `artefatos/requisitos_formais/REQ-014-configuracao-rag.md` — limiares de score do RAG.
- `artefatos/qa/cenarios_teste_funcionais_sprint02.md` — CTF-002-08, CTF-002-09, CTF-002-10.

---

## 6. Dúvidas / decisões pendentes

- **Limiar de confiança "alta" vs "baixa"**: definir em conjunto. Sugiro começar com `>= 0.7` = alta; `< 0.7` = baixa. Ajustar após observar volume real.
- **Limiar de score do RAG no fallback**: aproveitar o já configurado em REQ-014 (`rag_top_k` + score mínimo); não criar paralelo.
- **Heurística do Caso 3** (confiança alta em outra categoria + forma interrogativa): você pode deixar fora do POC se julgar over-engineering. O REQ-002.1A marca como **opcional**.

Quaisquer dessas dúvidas, me chama.
