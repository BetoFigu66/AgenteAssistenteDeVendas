# Tarefa — Calibração do Classificador de Intenções (REQ-002.1 / REQ-002.1A)

**De:** Kika (Analista de Requisitos)  
**Para:** Beto (Implementador)  
**Data:** 2026-06-03  
**Origem:** bug observado — pergunta `"Quais produtos a Inforrel vende?"` foi respondida com "não entendi" mesmo havendo Q&A correspondente na base.  
**Requisitos relacionados:** REQ-002.1, REQ-002.1A (novo), REQ-003, REQ-005.6, REQ-014.

---

## 1. Resumo do problema

O classificador da porta de entrada (REQ-002.1) errou em uma pergunta canônica que deveria cair na **categoria 3** (pergunta sobre produto/serviço/empresa) e ser delegada ao REQ-003 (RAG/Q&A). Em vez disso, devolveu fallback genérico ao cliente.

**Diagnóstico revisado (06/06/2026 — Beto):** revisão do código confirmou que **não existe** workaround de "consultar Q&A antes da classificação". A ordem real é sempre: identificar → classificar → decidir resposta. As causas prováveis do bug são:

1. **Roteamento pré-identificação** — telefone novo recebia saudação/pedido de CNPJ **antes** de delegar cat. 3 ao REQ-003 (corrigido em requisito: REQ-002.1B).
2. **Prompt do classificador** a calibrar (exemplos cat. 1 vs 3).
3. **Fallback condicional** (REQ-002.1A) ainda não implementado com gate de `confianca_nivel`.

Havia um fallback QA **após** classificação, apenas para intenções não mapeadas (commit `125abcc`), sem condicional de confiança — distinto do anti-padrão "toda mensagem".

A solução correta tem **três frentes**: (a) REQ-002.1B — cat. 3 antes do documento fiscal; (b) calibrar classificador; (c) fallback condicional formalizado em REQ-002.1A.

---

## 2. Próximos passos (handoff)

### Passo 0 — REQ-002.1B: cat. 3 antes do documento fiscal *(infra parcial no código)*

Permitir que perguntas cat. 3 com confiança alta sejam atendidas via REQ-003 **sem CNPJ/CPF**, criando contato/negociação anônimos e promovendo depois. Infraestrutura (`empresa_id` nullable, `criar_contato_sem_empresa`, promoção ao CNPJ) já iniciada; falta ligar ao roteamento em `_decidir_resposta`.

### Passo 1 — Implementar fallback condicional (REQ-002.1A)

Substituir o fallback QA genérico (intenções não mapeadas) por decisão baseada em `confianca_nivel`, lendo limiares da tabela `parametros` via `ParametroService`:

- **Alta** → rota direta (Caso 1).
- **Média** → REQ-002.21 esclarecimento, **sem** REQ-003 (Caso 1b).
- **Baixa / não identificado** → tentar REQ-003 antes de "não entendi" (Caso 2).
- **Caso 3** → fora do POC (backlog).

### Passo 2 — Expor confiança do classificador *(parcial — enum persistido; limiares ainda hardcoded)*

O retorno do classificador deve conter, além da categoria, score float `[0.0, 1.0]` e enum `confianca_nivel` (`alta` / `media` / `baixa`), derivado dos limiares em `parametros` (`classificador_conf_alta_min=0.70`, `classificador_conf_baixa_max=0.40`). Pendente: integrar `ParametroService` no cálculo do nível.

### Passo 3 — Calibrar o prompt do classificador (causa raiz)

#### 3.1 Princípio de distinção

Na prática, a confusão acontece entre **categoria 1** (intenção de compra/orçamento) e **categoria 3** (pergunta sobre produto/empresa) quando ambas mencionam "produto". Sugiro a regra:

- **Verbo de posse/oferta da empresa** ("vende", "vendem", "trabalha com", "tem", "fornece", "faz", "atende", "comercializa") + objeto produto → **categoria 3**.
- **Verbo de compra/desejo do cliente** ("quero", "preciso", "gostaria de", "tô precisando", "vou comprar", "fechar") + quantidade explícita ou contexto de uso → **categoria 1**.
- Forma puramente **interrogativa de catálogo** ("quais", "que tipos de", "vocês têm", "tem alguma...") → **categoria 3**.

#### 3.2 Exemplos canônicos

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

#### 3.3 Casos limítrofes

- `"Vocês têm catracas? Preciso de 5"` → **categoria 1** (a intenção de compra com quantidade prevalece sobre a pergunta inicial).
- `"Catracas"` (mensagem solta, sem verbo) → **categoria 3** se confiança alta na interpretação como "vocês têm catracas?"; caso contrário, baixa confiança e cai no fallback do REQ-002.1A.
- `"Quero saber sobre catracas"` → **categoria 3** (interesse em informação, não compra explícita).

#### 3.4 Saída esperada

O classificador deve retornar, para cada mensagem:

```json
{
  "categoria": 1 | 2 | 3 | 4 | "nao_identificado",
  "confianca": 0.0 a 1.0,
  "justificativa_curta": "string opcional, útil para auditoria"
}
```

A `justificativa_curta` pode ser exibida no modal de raciocínio (REQ-005.6) e ajuda a entender o motivo da classificação em casos de bug.

### Passo 4 — Auditoria (REQ-005.6) *(parcial — `confianca_nivel` no banco; falta fallback no modal)*

Cada mensagem processada deve registrar no modal de raciocínio:

- Categoria escolhida pelo classificador.
- Confiança da classificação.
- Se houve fallback para REQ-003 (sim/não).
- Resultado do fallback (resposta entregue / pediu esclarecimento / escalou).

Sem essa instrumentação, próximos bugs vão ficar invisíveis — voltamos a depender de o cliente reclamar para descobrir.

### Passo 5 — Validação

Após implementação, executar os cenários de teste já criados em `artefatos/qa/cenarios_teste_funcionais_sprint02.md`:

- **CTF-002-08** — pergunta "Quais produtos a Inforrel vende?" deve responder pela Q&A com confiança alta, sem fallback.
- **CTF-002-09** — mensagem ambígua aciona fallback via REQ-003 quando a confiança é baixa; o sistema nunca devolve "não entendi" sem ter tentado.
- **CTF-002-10** — anti-padrão: resposta de qualificação ("5") **não** consulta a base; valida gate de confiança do REQ-002.1A.

---

## 3. Estado da implementação (06/06/2026)

| Item | Status |
|------|--------|
| `NivelConfianca` + `confianca_nivel` no classificador | Feito |
| Persistência `confianca_nivel` em `ProcessamentoMensagem` | Feito |
| Tabela `parametros` + seed + `ParametroService` | Feito (não integrado ao classificador/processador) |
| Contato/negociação anônima + promoção CNPJ | Feito (não integrado ao roteamento cat. 3) |
| Fallback condicional REQ-002.1A | Pendente |
| Prompt calibrado + `justificativa_curta` | Pendente |
| Auditoria fallback no modal | Pendente |
| CTF-002-08/09/10 | Pendente |

---

## 4. Por que esta abordagem é melhor que consulta indiscriminada ao REQ-003

| Aspecto | Consulta indiscriminada ao REQ-003 | Calibrar + REQ-002.1A + REQ-002.1B |
|---|---|---|
| Resolve o caso `"Quais produtos a Inforrel vende?"` | Sim, por acaso | Sim, por design |
| Custo por mensagem | Alto (RAG sempre roda) | Baixo (RAG só roda quando necessário) |
| Latência por mensagem | Alta sempre | Baixa em > 90% dos casos |
| Risco de poluir resposta de qualificação | Alto | Zero (proibido pelo anti-padrão) |
| Auditável | Não | Sim (cada decisão registrada) |
| Resolve causa raiz | Não, mascara | Sim, calibra o classificador |
| Aderente à arquitetura REQ-002.1 (porta de entrada) | Não, dilui | Sim, preserva |

---

## 5. Estimativa

| Atividade | Horas |
|-----------|-------|
| Reverter workaround inexistente | — |
| REQ-002.1B (roteamento cat. 3 pré-identificação) | 3h |
| Integrar `ParametroService` nos limiares | 1h |
| Expor confiança no retorno do classificador | 2h |
| Implementar fallback condicional (REQ-002.1A) | 4h |
| Atualizar prompt do classificador com exemplos | 2h |
| Adicionar auditoria de fallback no modal (REQ-005.6) | 2h |
| Rodar e validar CTF-002-08, CTF-002-09, CTF-002-10 | 2h |
| **Total** | **15h** |

---

## 6. Referências

- `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` — REQ-002.1, REQ-002.1A (v1.21), REQ-002.1B (novo).
- `artefatos/requisitos_formais/REQ-003-respostas-automaticas-rag.md` — base de respostas automáticas (Q&A + RAG).
- `artefatos/requisitos_formais/REQ-005-registro-interacoes-historico.md` — REQ-005.6 (auditoria de respostas da IA).
- `artefatos/requisitos_formais/REQ-014-configuracao-runtime-camadas-conhecimento.md` — limiares RAG, Q&A e classificador (`parametros`).
- `artefatos/qa/cenarios_teste_funcionais_sprint02.md` — CTF-002-08, CTF-002-09, CTF-002-10.

---

## 7. Decisões registradas (06/06/2026)

- **Limiar de confiança**: três níveis — `alta` (≥ 0.70), `media` (0.40–0.69), `baixa` (< 0.40); limiares na tabela `parametros`.
- **Comportamento `media`**: pedir esclarecimento (REQ-002.21), **sem** fallback REQ-003.
- **Comportamento `baixa`**: fallback REQ-003 → esclarecimento → escalar (REQ-004.9).
- **Limiar de score do RAG no fallback**: usar REQ-014 / `parametros`; não criar paralelo.
- **Caso 3 (heurística opcional)**: **fora do POC**; backlog pós CTF-002-08/09/10.
- **CTF-002-08**: telefone sempre **novo** (`5511999990020`); valida REQ-002.1B + classificador cat. 3 alta.
