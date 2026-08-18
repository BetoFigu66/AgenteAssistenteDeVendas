# Decisões de Requisitos

<!-- CLASSIFICACAO: IA -->
<!-- CLASSIFICACAO: SISTEMA-DEV -->

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

## DEC-006 — Coluna `fase` complementa `status`, não substitui REQ-016

- **Data**: 2026-07-12
- **REQs afetados**: REQ-016.4 (não altera), catálogo de conversação (`FASE-xxx.md`)
- **Status**: vigente

**Contexto**: o plano de MVP Continuidade (`docs/plano_implementacao_mvp_continuidade_2026-07.md`, passos A1/A2) introduziu a coluna `Atendimento.fase` (enum `esclarecendo`/`finalizando`/`em_orcamentacao`) para representar o estágio da jornada conversacional guiada descrita no catálogo de conversação (`artefatos/analista_de_requisitos/catalogo_conversacao/`). Havia dúvida se isso duplicava ou substituía o `status` (`ativo`/`encerrado`) já definido em REQ-016.4 — a prova de que **não** são a mesma coisa: `FASE-encerrado-por-inatividade.md` já documentava uma fase cujo nome sugere encerramento, mas cuja `situação` permanece `ativo` (o catálogo já tratava os dois eixos como independentes desde 2026-07-03/04, antes mesmo da coluna existir no schema).

**Decisão**: `fase` e `status` são eixos **ortogonais** e **ambos persistidos**:
- `status` (REQ-016) — se o atendimento está aberto para interação (`ativo`) ou fechado (`encerrado`); grosso, estável, poucos valores; usado hoje para consultas de "atendimentos ativos" (`/api/atendimentos/ativas`, matriz de continuação do REQ-016.7).
- `fase` (catálogo de conversação) — em que ponto do fluxo guiado o atendimento está enquanto ativo; mais granular, cresce conforme novas fases/produtos entram no catálogo.

Nenhuma fase implementada até aqui (MVP: `esclarecendo`, `finalizando`, `em_orcamentacao`) é terminal — as fases terminais do catálogo (`FASE-encerrado`, `FASE-encerrado-por-inatividade`) permanecem fora do enum até serem implementadas (fora do escopo desta fatia).

**Alternativas descartadas**:
- **Substituir `status` por `fase`** (deixar `status` implícito a partir da fase) — descartada: exigiria manter em código uma lista de "quais fases contam como `ativo`", frágil a cada fase nova adicionada, e quebraria toda a lógica já existente de REQ-016 que consulta `status` diretamente.
- **Derivar `fase` de `status` + outra coisa sem coluna própria** — descartada: `fase` precisa ser consultável e indexável de forma simples (UI, `campos_pendentes()`), e não há como derivá-la de `status` (um único `status=ativo` cobre 3+ fases diferentes).

**Consequências**:
- `backend/models.py::Atendimento` tem agora `status` (REQ-016) e `fase` (MVP Continuidade) como colunas independentes, cada uma com seu próprio enum e índice.
- Documentado em detalhe em `docs/dicionario_termos.md` (entradas "Fase (do atendimento)" e "Situação (do atendimento)").
- Futuras fases terminais do catálogo, quando implementadas, não devem tentar unificar com `motivo_encerramento`/`status` — continuam como valores adicionais do enum `FaseAtendimento`.

---

## DEC-007 — Transição de fases: imediata pela intenção + ping-pong Finalizando⇄Esclarecendo para dúvidas

- **Data**: 2026-07-14
- **REQs afetados**: REQ-002.1C (v1.33), FASE-esclarecendo.md, FASE-finalizando.md
- **Status**: vigente

**Contexto**: existiam duas opções concorrentes para a regra de transição Esclarecendo→Finalizando (documentadas em `artefatos/analista_de_requisitos/TransicaoEscalrecendoFinalizandoClaude.md`):
- Opção 1 (REQ-002.1C v1.28): exigir modelo/quantidade confirmados antes de transitar.
- Opção 2 (plano MVP v2.3, implementação Fases E/F): transição imediata pela intenção (cat. 1).

Adicionalmente, o Beto propôs que dúvidas durante a coleta devem causar **transição real de fase** (Finalizando→Esclarecendo), não apenas resposta inline. Rationale: manter a separação conceitual limpa — Esclarecendo é sempre reativo (responde dúvidas), Finalizando é sempre ativo (cobra campos).

**Decisão**: adotada a Opção 2 + retorno bidirecional:
1. **Esclarecendo → Finalizando**: imediata ao detectar intenção de orçamento (cat. 1), sem gate de campos.
2. **Finalizando → Esclarecendo**: quando o cliente faz dúvida (cat. 3) durante a coleta.
3. **Esclarecendo → Finalizando (retorno)**: automático quando a próxima mensagem do cliente não é dúvida (cat. 3).

**Alternativas descartadas**:
- **Gate por dados mínimos (Opção 1)**: exigiria manter duas listas de campos por produto (pré-requisitos vs. Finalizando); escala mal com múltiplos produtos; quebra separação conceitual das fases.
- **Dúvida respondida inline sem trocar de fase (F3 original do MVP)**: funciona tecnicamente, mas mistura responsabilidades — Finalizando faz coleta E responde dúvidas, perdendo rastreabilidade e clareza semântica.

**Consequências**:
- A implementação atual (F3 — resposta inline) precisará ser ajustada para fazer `atendimento.fase = ESCLARECENDO` antes de responder e retornar depois.
- `campos_pendentes()` e campos já capturados **não são afetados** pela troca de fase — dados permanecem em `AtendimentoInfo`/`ItemAtendimento`.
- Auditoria/logs ganham visibilidade de quando o cliente está em dúvida vs. em coleta.
- A regra de retorno automático é: "próxima mensagem não é cat. 3 → volta para Finalizando".

---

## DEC-008 — "Vocês vendem/trabalham com X?" deve ser classificado como intenção de orçamento

- **Data**: 2026-08-06
- **REQs afetados**: REQ-002.1, REQ-002.1C
- **Status**: parcialmente superada por DEC-009 (07/08/2026) — a classificação de intenção (categoria 1, não categoria 3) e a exigência de produto continuam vigentes; a intenção específica passou de `pedir_orcamento` para `perguntar_disponibilidade`, com resposta e transição próprias antes de entrar no fluxo de orçamento.

**Contexto**: durante testes do fluxo MVP (2026-08-06), a mensagem "Vocês vendem relógio de ponto biométrico?" foi classificada como categoria 3 (pergunta sobre produto) e caiu no fallback de clarificação do REQ-003.7. O cliente manifestava intenção comercial evidente, mas o sistema interpretou a frase como dúvida informativa e permaneceu em FASE-esclarecendo, exigindo depois uma nova mensagem explícita como "quero orçamento" para avançar a qualificação. O mesmo padrão se aplica a "trabalham com catraca?", "vocês vendem controle de acesso?" e outras formulações similares.

**Decisão**: perguntas do tipo "Vocês vendem X?" e "Vocês trabalham com X?" — quando X for um produto, tecnologia ou marca reconhecida do catálogo — devem ser classificadas como **categoria 1** (intenção de orçamento / `pedir_orcamento`) pelo classificador do REQ-002.1. A transição Esclarecendo → Finalizando passa a ocorrer na mesma mensagem, desde que o tipo de produto seja identificado e a mensagem não contenha dúvida genuína adicional (REQ-002.1C). A definição de "intenção explícita de orçamento/compra" em REQ-002.1C passa a incluir essas formulações comerciais.

**Alternativas consideradas e descartadas**:

- **Criar pares Q&A para cada produto/tecnologia** (ex.: "Vocês vendem relógio de ponto?", "Vocês vendem catraca?") — descartada porque (i) a camada Q&A curada responde conteúdo, mas não muda de fase, então a qualificação não avançaria sem uma nova mensagem do cliente; (ii) a busca full-text usa `plainto_tsquery` com lógica AND, exigindo muitos pares para cobrir variações (produto + tecnologia); (iii) não aproveita as entidades já extraídas na mensagem para resolver o modelo.
- **Apenas expandir o catálogo de respostas RAG** — descartada pelos mesmos motivos: responde dúvida, mas não inicia a qualificação.
- **Mover para um FAQ/Curador com resposta perguntando "quer um orçamento?"** — descartada porque introduz uma etapa extra quando a intenção já é comercial; o classificador é a porta de entrada correta para tomar essa decisão (REQ-002.1).

**Consequências**:

- O regex de `PEDIR_ORCAMENTO` em `backend/services/classificador.py` deve incluir `vende(m|mos)?` e `trabalha(m|mos)?(?:\s+com)?`.
- O prompt do LLM em `classificador.py` deve ser atualizado para ensinar que "vocês vendem X?" e "trabalham com X?" com produto/tecnologia marcam `pedir_orcamento`.
- Se a mensagem já trouxer produto/tecnologia (ex.: `tipo_leitor_mencionado=biometria`), `FinalizandoState._resolver_modelo` usará as entidades da mensagem atual e evitará reperguntar o modelo/tecnologia.
- Perguntas puramente informativas ("Vocês vendem para todo o Brasil?") podem gerar falso positivo — devem ser mitigadas pela presença de produto/tecnologia no regex e, quando persistirem, tratadas como Caso 3 (intenção + dúvida) se houver ambiguidade.
- Roteiros de teste e casos de QA devem incluir variantes dessas frases.

---

## DEC-009 — "Vocês vendem X?" ganha intenção própria (`perguntar_disponibilidade`) com confirmação e marcas antes de qualificar

- **Data**: 2026-08-07
- **REQs afetados**: REQ-002.1, REQ-002.1C
- **Status**: vigente

**Contexto**: com DEC-008, "Vocês vendem relógio biométrico?" passou a classificar como `pedir_orcamento` e entrar direto em Finalizando — mas a primeira resposta do sistema era a pergunta técnica de modelo ("O relógio seria cartográfico ou eletrônico?"), sem nenhuma confirmação de que a Inforrel vende o produto. Do ponto de vista do cliente, a conversa "pulava" a parte óbvia (confirmar disponibilidade) e ia direto para um interrogatório técnico, soando pouco natural. O cliente esperava algo como "Sim, vendemos. Trabalhamos com as marcas TOPDATA e ControlID de relógio de ponto biométrico. Você conhece esses relógios? Pode me dizer a faixa de funcionários que vai utilizar?".

**Decisão**: criar a intenção `perguntar_disponibilidade` (distinta de `pedir_orcamento`), disparada pelos mesmos verbos de DEC-008 ("vende(m/mos)?", "trabalha(m/mos)? (com)?") quando há produto reconhecido na mensagem. Pedidos explícitos de orçamento/cotação/preço continuam como `pedir_orcamento` e mantêm a resposta atual ("Ótimo! Vou precisar..."). `perguntar_disponibilidade` gera uma resposta nova (`DISPONIBILIDADE_PRODUTO`) que: (1) confirma "Sim, vendemos"; (2) lista as marcas ativas do catálogo para o tipo de produto/tecnologia mencionados (`Modelo.marca`, filtrando por `AtributoAdicionalModelo.tecnologia_leitura` quando aplicável); (3) já entra em Finalizando, mas com a primeira pergunta sendo a faixa de funcionários (`CAMPO_FAIXA_FUNCIONARIOS`), em vez da pergunta de modelo/tecnologia.

**Alternativas consideradas e descartadas**:

- **Manter tudo em `pedir_orcamento` e só trocar a primeira pergunta de Finalizando para "faixa de funcionários"** — descartada porque não resolve o problema de fundo (falta de confirmação "sim, vendemos") e misturaria dois comportamentos de mensagem bem diferentes na mesma intenção, dificultando testes e manutenção futura.
- **Pares Q&A por produto/marca** — descartada pelo mesmo motivo de DEC-008 (não escala, não muda de fase, não aproveita entidades já extraídas).

**Consequências**:

- `backend/services/classificador.py`: nova intenção `Intencao.PERGUNTAR_DISPONIBILIDADE`, regra de regex própria (precede `PEDIR_ORCAMENTO` em `_REGRAS_INTENCAO`), guarda `_pedir_orcamento_exige_produto` estendida para também exigir produto em `PERGUNTAR_DISPONIBILIDADE`, prompt do LLM atualizado.
- `backend/services/respostas/catalogo.py`: novo `MensagemId.DISPONIBILIDADE_PRODUTO` com template "Sim, vendemos. Trabalhamos com as marcas {marcas} de {produto}. Você conhece esses {produto_plural}?".
- `backend/services/conversacao/estados/finalizando.py`: `FinalizandoState.entrar` ganha parâmetros opcionais `mensagem_abertura`, `abertura_contexto` e `primeira_pergunta`, permitindo que fluxos como este substituam a abertura e a primeira pergunta padrão do orçamento sem duplicar a lógica de `campos_pendentes()`.
- `backend/services/conversacao/regras_esclarecendo.py`: nova ação `perguntar_disponibilidade`, busca de marcas via `Modelo`/`AtributoAdicionalModelo`, e ajuste em `_builder_disparar_fechamento` para não disparar "posso ajudar em mais alguma coisa" quando `PERGUNTAR_DISPONIBILIDADE` já abriu uma qualificação.
- Sem marcas cadastradas para o tipo de produto, a resposta cai em "as principais marcas do mercado" (evita mensagem vazia/quebrada).

---

## Histórico de revisões deste documento

| Data | Alteração | Autor |
|------|-----------|-------|
| 07/06/2026 | Criação do documento. Registradas DEC-001 (fallback condicional REQ-003), DEC-002 (zona media sem fallback), DEC-003 (causa raiz do bug "Quais produtos a Inforrel vende?"), DEC-004 (estilo enxuto dos REQs). | Kika |
| 06/07/2026 | DEC-005 (efeito diferenciado de conversão vs. perdido no atendimento). | Cascade |
| 12/07/2026 | DEC-006 (coluna `fase` complementa `status`, não substitui REQ-016 — passo A4 do MVP Continuidade). | Claude |
| 14/07/2026 | DEC-007 (transição de fases: imediata pela intenção + ping-pong Finalizando⇄Esclarecendo para dúvidas). | Cascade |
| 06/08/2026 | DEC-008 ("Vocês vendem/trabalham com X?" classificado como intenção de orçamento). | Cascade |
| 07/08/2026 | DEC-009 (nova intenção `perguntar_disponibilidade` com confirmação de marcas antes de qualificar; parcialmente supera DEC-008). | Cascade |
