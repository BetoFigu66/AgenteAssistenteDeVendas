# Decisões de Requisitos

Este documento registra **decisões importantes** tomadas ao longo da evolução dos requisitos formais (`artefatos/requisitos_formais/REQ-XXX-*.md`).

Os REQs em si são mantidos enxutos — descrevem **o que** o sistema deve fazer. Este documento captura **por que** algumas decisões foram tomadas daquela forma, alternativas que foram consideradas e descartadas, e contexto histórico que ajuda a entender o estado atual sem poluir o requisito.

## Quando registrar uma decisão aqui

- Quando há mais de uma forma plausível de implementar um requisito e a discussão concluiu por uma delas com motivo não-óbvio.
- Quando um requisito muda em resposta a um bug observado ou feedback de stakeholder.
- Quando uma abordagem foi explicitamente descartada (anti-padrão) e existe risco de alguém tentar usá-la novamente.
- Quando há diagnóstico técnico relevante (ex.: revisão de código que descartou hipótese).

## Quando NÃO registrar

- Mudança trivial de redação ou formatação.
- Decisões puramente operacionais (ex.: escolher cor de botão).
- Discussões que ficaram só no chat e foram superadas sem afetar o requisito.

## Formato de cada decisão

```
### DEC-XXX — Título curto

- **Data**: YYYY-MM-DD
- **REQs afetados**: REQ-002.1A, REQ-014.2A, ...
- **Status**: vigente | revisada | descartada

**Contexto**: o que motivou a decisão.

**Decisão**: o que foi decidido.

**Alternativas consideradas e descartadas** (quando relevante): listar e dizer por que foram rejeitadas.

**Consequências**: o que muda no sistema, o que vira anti-padrão.
```

IDs `DEC-XXX` são estáveis e não reciclados. Decisões revisadas ou descartadas permanecem no documento (com status atualizado) para preservar histórico.

---

## DEC-001 — Fallback condicional ao REQ-003 (não consultar a base em toda mensagem)

- **Data**: 2026-06-03
- **REQs afetados**: REQ-002.1, REQ-002.1A, REQ-003
- **Status**: vigente

**Contexto**: bug observado em 03/06/2026 — pergunta canônica `"Quais produtos a Inforrel vende?"` foi respondida com "não entendi" mesmo havendo Q&A correspondente na base. Solução inicial cogitada pelo desenvolvedor foi **sempre** consultar a base de Q&A em toda mensagem, como rede de segurança.

**Decisão**: o REQ-003 é acionado **condicionalmente** como rede de segurança (REQ-002.1A), não como caminho default. O classificador (REQ-002.1) continua sendo a porta de entrada; consulta à base só acontece quando a confiança da classificação é baixa ou em mensagens compostas (Caso 3).

**Alternativas descartadas**:

- **Sempre consultar REQ-003 antes/depois da classificação** — descartada porque (i) dilui a responsabilidade do classificador, (ii) introduz custo e latência desnecessários em mensagens corretamente classificadas, (iii) pode poluir respostas de qualificação em curso (categoria 2) com trechos irrelevantes da base, e (iv) torna o roteamento não-auditável.

**Consequências**:

- O classificador precisa expor `confianca` (float) e `confianca_nivel` (alta/media/baixa) — formalizado no REQ-002.1A.
- Cada decisão de fallback deve ser auditada em REQ-005.6.
- O prompt do classificador continua sendo a primeira linha de defesa — fallback não substitui prompt bem calibrado.

---

## DEC-002 — Confiança média não aciona fallback REQ-003

- **Data**: 2026-06-06
- **REQs afetados**: REQ-002.1A (Caso 1b)
- **Status**: vigente

**Contexto**: ao formalizar os níveis de confiança em REQ-002.1A, surgiu a dúvida sobre o que fazer com a faixa intermediária (`media`).

**Decisão**: nível `media` segue diretamente para REQ-002.21 (pedir esclarecimento ao cliente) sem tentar fallback automático para REQ-003. Após tentativas esgotadas, escalar via REQ-004.9.

**Alternativas descartadas**:

- **Tratar `media` como `baixa`** (acionar REQ-003) — descartada porque a base de respostas tem maior chance de gerar resposta irrelevante quando o classificador já tem alguma confiança em outra categoria, piorando a experiência em vez de melhorar.

**Consequências**: limiares `classificador_conf_alta_min` e `classificador_conf_baixa_max` (REQ-014.2A) precisam ser calibrados; a zona `media` deve ser estreita o suficiente para não engolir casos legítimos de cat. 3.

---

## DEC-003 — Causa raiz do bug "Quais produtos a Inforrel vende?" não era ausência de fallback

- **Data**: 2026-06-06
- **REQs afetados**: REQ-002.1, REQ-002.1B, REQ-003
- **Status**: vigente

**Contexto**: a hipótese inicial era que o sistema não consultava REQ-003. Revisão do código em 06/06/2026 (Beto) confirmou que **o fluxo já chama o classificador antes de qualquer outra coisa** — o problema era outro.

**Decisão**: documentar as duas causas reais e tratá-las separadamente:

1. **Roteamento exigia identificação fiscal antes de delegar cat. 3** — corrigido pelo novo REQ-002.1B (perguntas sobre produto/empresa podem ser atendidas antes do CNPJ/CPF, com contato/negociação anônimos e promoção posterior).
2. **Prompt do classificador precisava de calibração** — abordado no handoff `artefatos/implementador/tarefa_calibracao_classificador_req002_1.md`.

**Consequências**: REQ-002.1A (fallback condicional) continua válido como rede de segurança, mas **não é a correção do bug específico** — só ajuda em casos genuinamente ambíguos.

---

## DEC-004 — Estilo enxuto dos REQs formais

- **Data**: 2026-06-07
- **REQs afetados**: todos os REQs em `artefatos/requisitos_formais/`
- **Status**: vigente

**Contexto**: ao longo da evolução do REQ-002, várias seções de "Justificativa", "Anti-padrão explícito", "Nota de diagnóstico" e "Calibração complementar" foram acumuladas dentro de critérios de aceite. O documento ficou denso e perdeu foco.

**Decisão**: REQs formais devem conter apenas **o que** o sistema deve fazer e **como** validar. Discussões sobre **por que** uma alternativa foi escolhida, anti-padrões explicitamente proibidos e contexto histórico vão para este documento (`decisoes_requisitos.md`).

**Alternativas descartadas**:

- **Manter tudo no REQ** — descartada por poluir leitura e desviar foco do critério de aceite.
- **Apagar contexto sem registrar em lugar nenhum** — descartada por perder rastreabilidade de decisões que podem ser questionadas no futuro.

**Consequências**:

- Histórico de versões no rodapé dos REQs continua existindo, mas com entradas curtas.
- Exemplos concretos curtos podem ficar no REQ quando ajudam a entender o critério.
- Handoffs detalhados para o time (ex.: tarefa do implementador) ficam em `artefatos/implementador/` ou diretório do agente correspondente.

---

## DEC-005 — Efeito diferenciado de conversão vs. perdido no atendimento

- **Data**: 2026-07-06
- **REQs afetados**: REQ-016.4, REQ-016.12, REQ-006.5
- **Status**: vigente

**Contexto**: a regra original (REQ-016 v2.0) dizia que desfechos comerciais (ganha/perdida) ficam exclusivamente no orçamento e **nunca** afetam o estado do atendimento. Na prática, isso gerava dúvida: se o vendedor marca um orçamento como convertido, o atendimento permanece `ativo` indefinidamente? E se o cliente volta, reabre a mesma conversa de um pedido já concluído?

**Decisão**: criar regra diferenciada:
- Orçamento **convertido** → encerra o atendimento automaticamente com motivo `concluido_conversao`. A compra está concluída; se o cliente voltar, o sistema pergunta (PERG-016-009) e abre novo atendimento se necessário.
- Orçamento **perdido** → **não** encerra o atendimento. O atendimento permanece `ativo` para que o vendedor possa oferecer alternativa ou o cliente volte sem fricção. Se o vendedor concluir que não há mais interesse, encerra manualmente (`manual_vendedor`).

**Alternativas descartadas**:

- **Ambos (convertido e perdido) encerram o atendimento** — descartada porque perdido não significa fim da conversa; o cliente pode querer trocar modelo, ajustar quantidade, negociar preço.
- **Nenhum desfecho afeta o atendimento** (regra original) — descartada porque conversão representa fim natural do ciclo; manter o atendimento `ativo` após a compra gera confusão operacional e acúmulo de atendimentos "vivos".

**Consequências**:
- Novo motivo `concluido_conversao` em REQ-016.4.
- REQ-016.12 deixa de ser "totalmente independente" — conversão é exceção.
- No painel, o vendedor tem **duas ações distintas**: (1) marcar desfecho do orçamento (convertido/perdido) e (2) encerrar atendimento manualmente.

---

## Histórico de revisões deste documento

| Data | Alteração | Autor |
|------|-----------|-------|
| 07/06/2026 | Criação do documento. Registradas DEC-001 (fallback condicional REQ-003), DEC-002 (zona media sem fallback), DEC-003 (causa raiz do bug "Quais produtos a Inforrel vende?"), DEC-004 (estilo enxuto dos REQs). | Kika |
| 06/07/2026 | DEC-005 (efeito diferenciado de conversão vs. perdido no atendimento). | Cascade |
