# Transição Esclarecendo → Finalizando: análise de duas propostas antagônicas

**Versão:** 0.1
**Data:** 2026-07-10
**Autor:** Claude (a pedido do Beto)
**Status:** Rascunho — para análise e decisão da Kika
**Contexto:** durante brainstorming de arquitetura sobre `docs/plano_implementacao_mvp_continuidade_2026-07.md` (MVP "Esclarecendo → Finalizando", produto piloto Relógio de Ponto), identificamos duas ideias antagônicas sobre **quando** o atendimento deve sair da fase Esclarecendo e entrar em Finalizando. Este documento analisa os prós e contras de cada uma e recomenda uma direção — mas a decisão final é da Kika, por ser uma regra de negócio/UX da conversa, não só de arquitetura.

---

Prompt: 
"Existem 2 ideias antagônicas sobre os estados Esclarecendo e Finalizando:
1. Considera que só deve ir para o estado Finalizando depois que o cliente forneceu todas as informações para a criação do orçamento;
2. Considera que deve ir para o estado finalizando quando o cliente sinalizar que quer orçamento, só então, no estado finalizando, todas as perguntas pendentes seriam respondidas.
Quero que você faça uma análise de pros e contras de cada uma delas e dê sua opinião de qual é a melhor.
"



## 1. As duas propostas

### Opção 1 — só transita quando já tiver os dados mínimos confirmados

Texto atual de `REQ-002.1C` e `FASE-esclarecendo.md` (v0.2): o sistema só transita de Esclarecendo para Finalizando quando o cliente **já tiver informado (ou o sistema já tiver confirmado)** os dados mínimos — para relógio de ponto: modelo, quantidade/faixa e software (quando aplicável). Se faltar algum desses dados, o sistema **permanece em Esclarecendo** e pergunta o que falta antes de transitar.

Na prática: Esclarecendo passa a fazer perguntas ativas de coleta (modelo, software, faixa de funcionários) **antes** de virar Finalizando — que fica reduzido a coletar o que sobra (CNPJ/CPF, endereço, contato) e apresentar o resumo final.

### Opção 2 — transita assim que o cliente sinaliza intenção de orçamento

Decisão adotada no plano de MVP (`docs/plano_implementacao_mvp_continuidade_2026-07.md` v1.2): o sistema transita **imediatamente** para Finalizando ao reconhecer a intenção de orçamento/compra (categoria 1 do REQ-002.1), independentemente de já ter modelo/quantidade/software confirmados. Uma vez em Finalizando, **todos** os campos obrigatórios são cobrados ali, em qualquer ordem — o cliente pode responder o que quiser primeiro, e cada pergunta pendente reconhece sua própria resposta (inclusive dentro de uma mensagem composta, ex.: "quero orçamento, já uso o Domínio").

---

## 2. Prós e contras

### Opção 1 — gate antes da transição

**Prós**
- "Finalizando" fica fiel ao nome: quando o atendimento entra nela, já está perto do fim.
- Evita abrir um atendimento "carimbado" como negociação em andamento antes de confirmar que o produto atende o caso do cliente (ex.: descobrir no meio da coleta que não temos o modelo que ele quer).
- Aproveita o modo natural de Esclarecendo (conversa livre) para capturar esses dados sem parecer formulário.
- É o que já está formalizado hoje (`REQ-002.1C`, `FASE-esclarecendo.md` v0.2) — zero retrabalho de alinhamento.

**Contras**
- Quebra a separação conceitual que dá nome às fases: Esclarecendo deixa de ser puramente reativo (responde dúvida, acumula o que for espontâneo) e passa a fazer ativamente o mesmo tipo de coleta que Finalizando faz — só que um subconjunto dos campos. A linha entre as duas fica arbitrária (por que modelo é "pré-requisito" e endereço não é?).
- O motor de campos precisa manter **duas listas por produto** (o que é pré-requisito para sair de Esclarecendo vs. o que só é pedido em Finalizando) em vez de uma só — mais superfície de configuração, mais chance de divergência entre produtos, mais decisão manual a cada produto novo que entrar no catálogo (catraca, CFTV, etc.).
- O cliente diz "quero orçamento" e o sistema não reage de forma visível a isso — continua perguntando coisas como se ainda estivesse só esclarecendo, sem confirmar que entendeu a intenção.
- Tende a piorar conforme o catálogo de produtos cresce: cada produto novo exige redecidir onde fica essa linha entre "pré-requisito" e "resto".

### Opção 2 — transição imediata pela intenção

**Prós**
- Gatilho único e auditável: categoria 1 (intenção de orçamento) detectada → transita. Fácil de testar, fácil de explicar e de registrar em auditoria (REQ-005.6).
- Mantém a separação de papéis limpa: Esclarecendo = reativo, acumula o que for espontâneo; Finalizando = cobra ativamente o que falta. Facilita modelar cada fase como uma unidade de responsabilidade única (sem sobreposição de comportamento entre as duas).
- Motor de campos único por produto — uma lista de campos obrigatórios, sempre avaliada do mesmo jeito, sem uma segunda lista de "pré-requisitos". Menos configuração para manter conforme o catálogo cresce.
- UX mais alinhada à expectativa do cliente: quando ele sinaliza intenção, o sistema confirma isso explicitamente ("Ótimo! Vou precisar de algumas informações para montar o orçamento...") em vez de continuar num modo ambíguo.
- O custo de perguntar algo que talvez já estivesse implícito é baixo: se o cliente já mencionou dado(s) junto com "quero orçamento" na mesma mensagem, esses dados são reconhecidos e capturados no mesmo turno (a mensagem inteira é testada contra as perguntas pendentes antes de perguntar de novo).
- Consistente com o que o próprio REQ-002.2 já prevê ("primeiro contato com todos os dados" pode ir direto para Finalizando) — é a mesma lógica de fundo, só sem virar regra geral de transição.

**Contras**
- Pode abrir um Finalizando "vazio" (nenhum campo ainda capturado) quando o cliente diz só "quero orçamento" sem ter mencionado nada antes — quebra um pouco a expectativa de que "Finalizando" já estaria perto do fim.
- Diverge do texto formal já escrito (`REQ-002.1C`) — exige uma rodada de ajuste do requisito.

---

## 3. Recomendação

Recomendamos a **Opção 2** (transição imediata pela intenção, coleta completa dentro de Finalizando).

O motivo central: a Opção 1 introduz um problema estrutural que tende a piorar com o tempo — duas listas de campos obrigatórios por produto (o que é "pré-requisito para sair de Esclarecendo" vs. o que é "só de Finalizando") é o tipo de regra que começa simples com um produto (relógio de ponto) e vira inconsistente e difícil de manter a partir do segundo ou terceiro produto (catraca, CFTV, etc.), porque cada produto pode ter uma ideia diferente do que é "pré-requisito mínimo". A Opção 2 mantém uma responsabilidade clara por fase e uma única lista de campos por produto, o que escala melhor e é mais fácil de testar isoladamente.

O contra mais sério da Opção 2 — Finalizando "vazio" logo de cara quando o cliente só diz "quero orçamento" — não parece grave: é um estado transitório de um único turno, resolvido no mesmo fluxo pela mensagem de transição seguida da primeira pergunta pendente.

**Se a Kika concordar com a Opção 2**, o ajuste necessário é atualizar `REQ-002.1C` (e a nota correspondente em `FASE-esclarecendo.md`) para refletir que a transição ocorre pela intenção (categoria 1), não pela confirmação prévia de modelo/quantidade/software.

**Se a Kika preferir manter a Opção 1**, o plano de MVP (`docs/plano_implementacao_mvp_continuidade_2026-07.md`, especialmente §2, §3 e Fases D/E/F) precisa ser ajustado de volta para refletir o gate antes da transição, incluindo o desenho de duas listas de campos por produto.

---

## 4. Referências

| Artefato | Caminho |
|----------|---------|
| REQ-002 (REQ-002.1C) | `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` |
| Fase Esclarecendo | `artefatos/analista_de_requisitos/catalogo_conversacao/fases/FASE-esclarecendo.md` |
| Fase Finalizando | `artefatos/analista_de_requisitos/catalogo_conversacao/fases/FASE-finalizando.md` |
| Plano de implementação do MVP | `docs/plano_implementacao_mvp_continuidade_2026-07.md` |
| Dicionário de termos | `docs/dicionario_termos.md` |
