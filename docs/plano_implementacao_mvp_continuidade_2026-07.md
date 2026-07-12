# Plano de Implementação — MVP Continuidade (jul/2026)

**Versão:** 1.5  
**Data:** 2026-07-06 (atualizado 2026-07-12)  
**Autor:** Beto + Cascade + Claude  
**Status:** Provisório — aguardando validação da Kika  
**Origem:** `docs/brainstorming_continuidade_2026-07.md` (cenário 1 — Laboratório OO)  
**Escopo deste plano:** **um produto, uma jornada** — dúvida → orçamento → coleta mínima

---

## 1. Objetivo do MVP

Implementar o **primeiro fatia vertical** do modelo de fases proposto no brainstorming, exercitando o padrão **Esclarecendo → Finalizando** sem tentar cobrir todos os REQs de uma vez.

### O que o cliente vive

1. Pergunta sobre **um único produto** (relógio de ponto).
2. O sistema **responde a dúvida** via base de conhecimento (Q&A/RAG), **sem pedir CNPJ**.
3. O cliente manifesta intenção de orçamento (“quero comprar”, “manda orçamento”, etc.).
4. O sistema **transita imediatamente para Finalizando** ao reconhecer a intenção (categoria 1 do REQ-002.1) — não espera ter modelo/quantidade confirmados antes de sair de Esclarecendo. Uma vez em Finalizando, cobra **todos** os campos obrigatórios, em qualquer ordem (o cliente pode responder o que quiser primeiro):
   - **Modelo** do relógio (resolve sempre para uma entrada real do catálogo — nunca texto livre)
   - **Software de ponto** que a empresa usa (integração)
   - **Faixa de funcionários** — só perguntada se a empresa **não** tiver software de ponto
5. Com os campos preenchidos, o sistema apresenta **resumo** e encaminha para o vendedor (fase Criando Orçamento — handoff mínimo).

### O que fica de fora deste MVP

- Múltiplos produtos no mesmo atendimento
- Catraca, CFTV e demais linhas
- CNPJ/CPF, endereço, contato (campos existem no catálogo, mas **não** nesta fatia)
- Inatividade / reengajamento (REQ-016.9, REQ-002.22)
- Integração WhatsApp real (testes pelo painel admin — REQ-010)
- Sumarização sofisticada e confirmação campo a campo (REQ-002.16 completo)

---

## 2. Produto piloto e atributo de software

### Produto escolhido: **Relógio de Ponto**

| Fonte | O que diz |
|-------|-----------|
| Brainstorming §4.3 | Exemplo explícito: para comprar **Relógio de Ponto**, é necessário saber o **software** que a empresa usa |
| `CAMPO-software-ponto` | Campo formal no catálogo — obrigatório em Finalizando para relógio de ponto |
| `respostas_rita_v1.md` | Rita também cita que **relógios e catracas** dependem do sistema do cliente |

**Decisão deste MVP:** usar **apenas Relógio de Ponto**. O software de integração é o atributo condicional documentado em `artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-software-ponto.md`.

**Nota para evolução:** catraca terá campo análogo (`CAMPO-software-acesso` — **pendente Kika**). Não misturar no MVP para manter o motor de `campos_pendentes()` simples.

**Atualização 2026-07-09 (pull da Kika, commit `c4cd9ef`):** as fichas de campo que este plano previa criar já existem no catálogo — `CAMPO-modelo.md`, `CAMPO-faixa-funcionarios.md`, `CAMPO-quantidade.md`, `CAMPO-endereco.md`, `CAMPO-contato.md`, `CAMPO-cpf.md` (todas v0.1). **Importante:** `CAMPO-quantidade` é de **controle de acesso/catraca** (chave `quantidade_equipamentos`, mapeia para a coluna real `ItemAtendimento.quantidade`) — **não é** o campo desta fatia. Para relógio de ponto, o campo espelho é `CAMPO-faixa-funcionarios` (chave `faixa_funcionarios`, sizing por número de funcionários, não por unidades físicas do relógio).

### Campos obrigatórios nesta fatia

| ID catálogo | Chave técnica | Quando perguntar | Já existe no código? |
|-------------|----------------------|------------------|----------------------|
| _(interesse implícito)_ | `tipo_produto` = relógio de ponto | Pré-preenchido se cliente mencionou em Esclarecendo. **Não é um `CAMPO-xxx`** do catálogo (REQ-002.3A: "faz parte da estrutura do atendimento") | Parcial (`AtendimentoInfo`) |
| `CAMPO-modelo` | `modelo_produto` | Finalizando, se vazio | Não |
| `CAMPO-software-ponto` | `software_controle_ponto` | Finalizando, se vazio e produto = relógio | Não |
| `CAMPO-faixa-funcionarios` | `faixa_funcionarios` | Finalizando, **somente se** `software_controle_ponto` já respondido = "nenhum"; caso contrário `nao_aplicavel` (nunca perguntado) | Não |

**Sobre a ordem das perguntas:** não há sequência rígida imposta ao cliente — ele pode responder qualquer campo em qualquer mensagem (cada `Pergunta` reconhece a própria resposta, inclusive dentro de uma mensagem composta). A única regra real de ordem é de **dependência de aplicabilidade**: `faixa_funcionarios` só se torna uma pendência depois que `software_controle_ponto` for respondido — antes disso não dá para saber se o campo se aplica. Quando o sistema precisa *iniciar* uma pergunta (nenhum campo veio na mensagem do cliente), a ordem de exibição sugerida é: modelo → software de ponto → faixa de funcionários (se aplicável).

**Resolução de `modelo_produto` (decisão 2026-07-09):** o campo deve sempre resolver para uma entrada real do catálogo (`Modelo`, após a renomeação produto→modelo). Se a resposta do cliente não corresponder a nada reconhecível (após 1-2 tentativas de esclarecimento, REQ-002.21), o sistema **escala para modo atendente** (`escalar_humano` / `ModoOperacao.HUMANO`) em vez de gravar texto livre — evita que o vendedor tenha que reabrir a conversa depois para entender um texto ambíguo. **Isso diverge do texto atual de `CAMPO-modelo.md`/REQ-002.3B** (que hoje permite registrar texto livre e sinalizar pro vendedor) — pendência de alinhamento com a Kika (ver §8).

---

## 3. Jornada narrada (roteiro de aceite)

Telefone novo, sem histórico. Canal: painel admin.

| Turno | Cliente | Sistema (esperado) | Fase |
|-------|---------|-------------------|------|
| 1 | "Vocês têm relógio de ponto biométrico?" | Resposta da base Q&A/RAG sobre relógio biométrico. **Sem** pedir CNPJ. Registra interesse: `tipo_produto=relogio_ponto`. | Esclarecendo |
| 2 | "Qual a diferença pro facial?" | Responde via base. Permanece em Esclarecendo. | Esclarecendo |
| 3 | "Quero orçamento" | Categoria 1 (intenção de orçamento) → `ir_para_fase(finalizando)` **imediato** — não espera modelo/software antes de transitar. Nenhum campo veio nesta mensagem → pergunta o primeiro da ordem sugerida: **modelo** (ex.: biométrico / facial / cartão). | Finalizando |
| 4 | "Biométrico" | Resolve `modelo_produto` para a entrada real do catálogo (Modelo biométrico). Pergunta **software de ponto**. | Finalizando |
| 5 | "Usamos Domínio" | Registra `software_controle_ponto=Domínio`. Como há software, `faixa_funcionarios` vira `nao_aplicavel` (nunca é perguntado). Todos os campos obrigatórios OK → **resumo** + confirmação. | Finalizando |
| 6 | "Pode mandar" | `ir_para_fase` → Criando Orçamento; `notificar_vendedor` (ou equivalente mínimo). | Criando Orçamento |

### Variante: mensagem única com intenção + resposta compostas

Demonstra que a `Pergunta` de um campo pode reconhecer sua resposta **na mesma mensagem** que dispara a transição de fase — não é preciso esperar o próximo turno.

| Turno | Cliente | Sistema |
|-------|---------|---------|
| 1 (Esclarecendo) | "Quero orçamento, já usamos o Domínio pro ponto" | `PEDIR_ORCAMENTO` (categoria 1) → `ir_para_fase(finalizando)`. A mesma mensagem é reprocessada contra as `Pergunta`s de Finalizando: `CAMPO-software-ponto` reconhece "Domínio" e captura `software_controle_ponto=Domínio` **no mesmo turno**. Como há software, `faixa_funcionarios` já nasce `nao_aplicavel`. Sistema pergunta só o que falta: **modelo**. |

### Variante: software já informado em Esclarecendo

| Turno | Cliente | Sistema |
|-------|---------|---------|
| 1 | "Preciso de relógio compatível com Domínio" | Responde sobre compatibilidade + registra `software_controle_ponto=Domínio` passivamente (ainda em Esclarecendo) |
| 2 | "Quero orçamento" | `ir_para_fase(finalizando)` imediato. Único campo ainda pendente é **modelo** — software já capturado (`nao_perguntar_de_novo`) e `faixa_funcionarios` é `nao_aplicavel` (há software) |

### Variante: dúvida no meio da coleta (REQ-002.17 — simplificado)

| Turno | Cliente | Sistema |
|-------|---------|---------|
| _(em Finalizando, aguardando modelo)_ | "E o facial funciona offline?" | Responde via base + **retoma**: "Voltando ao orçamento: qual modelo você prefere — biométrico, facial ou cartão?" |

---

## 4. Arquitetura alvo (mínima)

```
┌─────────────────────────────────────────────────────────────┐
│  ProcessadorMensagem (motor de fases: padrão Estado/Pergunta)│
│    1. Classificar (categoria de roteamento + intenção)       │
│    2. Ler fase do atendimento → delega ao Estado ativo       │
│    3. Esclarecendo: cat.3 → Q&A/RAG + registrar interesse;   │
│       cat.1 (intenção de orçamento) → ir_para_fase(finalizando)│
│       IMEDIATO, sem exigir modelo/software antes             │
│    4. Finalizando: reprocessa a MESMA mensagem contra as     │
│       Perguntas pendentes (qualquer uma reconhece sua parte, │
│       em qualquer ordem) → aplica regras condicionais        │
│       (ex.: faixa_funcionarios só se software="nenhum") →    │
│       pergunta o próximo campo ainda sem valor               │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  services/conversacao/          AtendimentoInfo +
  fases.py                       ItemAtendimento
  campos_pendentes.py            (renomear itens_negociacao → itens_atendimento, passo A0)
  catalogo_campos.py   ◄── espelha CAMPO-xxx do catálogo analista
```

Nota: o desenho de classes (`EstadoAtendimento`, `Pergunta`, `Ação`) ainda está em discussão fora deste documento — ver `docs/dicionario_termos.md` e o histórico da conversa de brainstorming. Este diagrama descreve o comportamento esperado, não a API final das classes.

### Eixo `status` × `fase` (brainstorming §5.2)

| Campo | Valores MVP | Onde persistir |
|-------|-------------|----------------|
| `status` | `ativo` / `encerrado` | Já existe em `Atendimento.status` |
| `fase` | `esclarecendo` / `finalizando` / `em_orcamentacao` | **Novo** — coluna `fase` em `atendimentos` |

Fases fora do MVP (`encerrado_por_inatividade`, `encerrado`) permanecem no catálogo analista, sem implementação agora.

---

## 5. Passos de implementação

Ordem sugerida. Cada passo deve ser testável isoladamente no painel.

### Fase A — Fundação de domínio

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **A0** | ✅ Concluído (2026-07-10) — renomeação Negociação → Atendimento (débito técnico anterior) | Renomeada tabela `itens_negociacao` → `itens_atendimento` via migration Alembic (`2026071001_rename_itens_negociacao_para_itens_atendimento.py`, com rename de PK/FKs/índices/sequence); `backend/models.py::ItemAtendimento.__tablename__` atualizado; comentários/logs remanescentes em `processador.py` corrigidos; fallback morto `?? proc.negociacao_id_ativa` removido de `ProcessamentoDetalhes.jsx`; texto residual do REQ-004.4 corrigido (v1.8). **Achado importante durante a execução, não resolvido ainda** — ver nota abaixo e §8 item 8. | — |

**Nota A0 (2026-07-10):** ao aplicar a migration, descobrimos que o banco local (dev/QA) tem **drift de DDL manual fora do Alembic** bem mais extenso do que o esperado: (a) constraints com nomes com typo em pelo menos 5 tabelas (`atendimentao` no lugar de `atendimento`, `atendimentoes` no lugar de `atendimentos` — ex.: `mensagens_atendimentao_id_fkey`, `atendimentoes_contato_id_fkey`); (b) tabelas fantasmas vazias (`negociacoes`, `negociacao_infos`, 0 linhas) coexistindo com as reais (`atendimentos` 9 linhas, `atendimento_infos` 18 linhas); (c) sequences nunca renomeadas (`atendimentos.id` ainda usa `negociacoes_id_seq`). **Causa raiz identificada:** `backend/database.py::Database._criar_tabelas()` chama `Base.metadata.create_all()` em **todo startup do backend** — isso cria tabelas fantasmas toda vez que um `__tablename__` muda e o app recarrega (via `--reload`) antes do `alembic upgrade head` rodar. A migration do A0 já inclui uma proteção defensiva (`_dropar_fantasma_vazia`) para não quebrar por causa disso, mas o problema de fundo (linhas 37-39 de `database.py`) continua e pode recriar fantasmas em qualquer edição futura de model. Registrado como pendência separada — ver §8 item 8. Não mexi nos 5 tabelas com typo nem nas tabelas fantasmas `negociacoes`/`negociacao_infos` (0 linhas, seguras de remover) porque isso está fora do escopo literal do A0; aguardando decisão do Beto sobre até onde estender essa limpeza.
| **A1** | ✅ Concluído (2026-07-11) — Enum `FaseAtendimento` | `esclarecendo`, `finalizando`, `em_orcamentacao` em `models.py`, com docstring explicando o eixo `fase` × `status` (complementa REQ-016) | — |
| **A2** | ✅ Concluído (2026-07-11) — Migration Alembic | Migration `2026071101_adiciona_fase_em_atendimentos.py`: ENUM `faseatendimento` + coluna `fase` em `atendimentos` (NOT NULL, `server_default='esclarecendo'`, indexada), mesmo padrão da migration de `modo_operacao`. Aplicada e verificada — os 9 atendimentos existentes foram backfilled com `esclarecendo` | A1 |
| **A3** | ✅ Concluído (2026-07-12) — Atendimentos novos iniciam em Esclarecendo | `services/atendimentos.py::obter_ou_criar_atendimento` e `obter_ou_criar_atendimento_pf_pendente` — `fase=FaseAtendimento.ESCLARECENDO` explícito na criação. Testado ponta a ponta via API real (`/api/mensagem` com telefone novo → `fase='esclarecendo'` no banco); dados de teste limpos depois | A2 |
| **A4** | ✅ Concluído (2026-07-12) — DEC-006 | Decisão registrada em `artefatos/analista_de_requisitos/decisoes_requisitos.md`: `fase` complementa `status`, não substitui REQ-016 (eixos ortogonais, alternativas descartadas, consequências) | — |

**Nota (2026-07-12):** ao concluir o A2, notamos que as constraints de **PK** de `atendimentos` e `atendimento_infos` também tinham ficado com nome antigo (`negociacoes_pkey`, `negociacao_infos_pkey` — mesma categoria de drift do A0, só que sem typo). Corrigido em migration separada `2026071102_renomeia_pks_atendimentos.py` (idempotente, condicional — não faz nada em bases onde os nomes já estão corretos).

### Fase B — Catálogo de campos (código)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **B1** | `catalogo_campos.py` | Definição declarativa dos campos do MVP: chave, texto da pergunta, produtos aplicáveis, regra de aplicabilidade | Catálogo analista |
| **B2** | Mapear `CAMPO-software-ponto` | Texto de `campos/CAMPO-software-ponto.md` (existe, v0.1); chave `software_controle_ponto` | B1 |
| **B3** | Mapear `CAMPO-modelo` | Texto de `campos/CAMPO-modelo.md` (existe, v0.1 — criado pela Kika); chave `modelo_produto`; lista de modelos p/ relógio: cartográfico/eletrônico (cartão, barras, biometria, facial); **deve resolver para uma linha real do catálogo** — sem correspondência → `escalar_humano` (ver §2, diverge do texto atual da ficha) | B1 |
| **B4** | Mapear `CAMPO-faixa-funcionarios` | Texto de `campos/CAMPO-faixa-funcionarios.md` (existe, v0.1 — criado pela Kika); chave `faixa_funcionarios`; aplicável **somente se** `software_controle_ponto = "nenhum"` | B1, B2 |
| **B5** | `MensagemId.PEDIR_MODELO`, `PEDIR_SOFTWARE_PONTO`, `PEDIR_FAIXA_FUNCIONARIOS` | Novos templates em `respostas/catalogo.py` (não reutilizar genéricos demais) | B1 |

**Nota:** `campos/CAMPO-quantidade.md` (também criado pela Kika) é de **controle de acesso/catraca** — fora desta fatia. Quando entrarmos em catraca (próxima fatia, §9), mapeia para a coluna real `ItemAtendimento.quantidade`, não para `AtendimentoInfo`.

### Fase C — Motor `campos_pendentes()`

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **C1** | `campos_pendentes(atendimento) -> list[CampoDef]` | Cruza catálogo + `AtendimentoInfo` + `ItemAtendimento`; ignora preenchidos e não aplicáveis | B1 |
| **C2** | `proxima_pergunta(atendimento) -> CampoDef \| None` | Primeiro pendente entre os **aplicáveis**, na ordem de exibição sugerida (modelo → software → faixa de funcionários). **Não é uma regra de sequência obrigatória** — o cliente pode responder qualquer campo antes de ser perguntado; isso só decide o que perguntar quando nada veio na mensagem | C1 |
| **C3** | Regra `nao_perguntar_de_novo` | Se `AtendimentoInfo`/`ItemAtendimento` já tem valor, não retorna o campo | C1 |
| **C4** | Regras condicionais (aplicabilidade) | (a) `software_controle_ponto` só é campo se `tipo_produto` = relógio de ponto; (b) `faixa_funcionarios` só é **pendente/aplicável** depois que `software_controle_ponto` for respondido = "nenhum" — antes disso ou se houver software, fica `nao_aplicavel` | C1 |


### Fase D — Esclarecendo (responder sem qualificar)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **D1** | Roteamento por fase no processador | Se `fase=esclarecendo` e categoria 3 → delegar Q&A/RAG **antes** de pedir documento | T-03 backlog REQ-002 |
| **D2** | Registrar interesse passivo | Ao detectar menção a relógio de ponto: gravar `tipo_produto` em `AtendimentoInfo` ou `ItemAtendimento` | A3 |
| **D3** | Extração passiva de software | Se mensagem mencionar software conhecido (Domínio, TOTVS, etc.) → pré-preencher `software_controle_ponto` | B2 |
| **D4** | Extração passiva de modelo/faixa de funcionários | Regex/heurística leve + opcional LLM para entidades já usadas no processador | — |

**Referência backlog:** T-03 (pré-identificação), parcialmente implementado — validar se já permite Q&A sem CNPJ; completar se necessário.

### Fase E — Transição Esclarecendo → Finalizando

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **E1** | Detectar intenção de orçamento | `PEDIR_ORCAMENTO` (categoria 1) com confiança alta → `ir_para_fase(finalizando)` **imediato**, sem exigir modelo/software confirmados antes (decisão 2026-07-09 — diverge do texto atual do REQ-002.1C, ver §6) | Classificador |
| **E2** | Mensagem de transição | Template curto: "Ótimo! Vou precisar de algumas informações para montar o orçamento." — só enviado se sobrar algum campo pendente após E3 | B5 |
| **E3** | Reprocessar mensagem de transição contra Finalizando | A mesma mensagem que disparou `ir_para_fase` é imediatamente testada contra as `Pergunta`s de Finalizando (pode já responder um ou mais campos — ex.: "quero orçamento, já uso Domínio"); só depois chama `proxima_pergunta()` para o que sobrar sem resposta | C2, E1 |

### Fase F — Finalizando (coleta ativa)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **F1** | Loop de coleta no processador | A cada mensagem em Finalizando: testar contra todas as `Pergunta`s pendentes (não só a "próxima") → validar e gravar as que reconhecerem algo → recalcular aplicabilidade (`campos_pendentes`) → perguntar o que ainda falta | C2, C4, D4 |
| **F2** | Validação mínima | Modelo: deve resolver para uma linha real do catálogo — sem correspondência após 1-2 tentativas de esclarecimento (REQ-002.21) → `escalar_humano` (nunca aceitar texto livre); faixa de funcionários: inteiro/faixa > 0, só quando aplicável; software: texto não vazio | — |
| **F3** | Retomada após dúvida (simplificado) | Se categoria 3 durante Finalizando: responder Q&A + reapresentar última pergunta pendente | D1 |
| **F4** | Resumo ao completar | Template listando modelo, software, faixa de funcionários (quando aplicável); pedir confirmação | C1 |

### Fase G — Criando Orçamento (handoff mínimo)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **G1** | Confirmação → `em_orcamentacao` | Cliente confirma resumo | F4 |
| **G2** | `modo_operacao = HUMANO` ou flag equivalente | Alinha a REQ-004 / FASE-criando-orcamento | — |
| **G3** | Mensagem ao cliente | "Recebi suas informações. Nossa equipe vai preparar o orçamento e retorna em breve." | — |

### Fase H — Painel e testes

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **H1** | Exibir `fase` na UI da conversa | REQ-010 — detalhe do atendimento | A2 |
| **H2** | Exibir campos capturados / pendentes | Lista `AtendimentoInfo` com status visual | C1 |
| **H3** | Roteiro de teste manual | Criar `artefatos/qa/roteiros_teste/RT-0XX-mvp-relogio-ponto.md` com jornada §3 | — |
| **H4** | Testes automatizados backend | `pytest` para `campos_pendentes()` e transição de fase (sem LLM real) | C1, E1 |

---

## 6. Mapa para o backlog existente

| Passo deste plano | Tarefa REQ-002 existente | Observação |
|-------------------|--------------------------|------------|
| A0 | — (débito técnico — rename Negociação→Atendimento incompleto) | Antecede A1; evitar conviver com nomes mistos antes da Fase B |
| A1–A3 | — (novo — derivado brainstorming) | Antecede T-05 |
| B1–B4, C1–C4 | **T-05** | Núcleo do motor de perguntas |
| D2–D4 | **T-06** (T-06.2, T-06.3) | Só subconjunto relógio |
| D1 | **T-03** | Pré-requisito para Esclarecendo sem CNPJ |
| F3 | **T-09** (versão mínima) | Só retomada, sem contador de retries |
| F4 | **T-08** (versão mínima) | Resumo simples, sem eco campo a campo |
| H3–H4 | **RT QA** | Novo roteiro |

**Não bloquear o MVP em:** T-04 (CNPJ), T-07 (validações avançadas), T-10 (inatividade), T-11 (WhatsApp).

**Pendência de alinhamento formal:** `REQ-002.1C` (Kika, v1.28, 04/07/2026) descreve a transição Esclarecendo→Finalizando como condicionada a modelo+quantidade **já confirmados** ainda em Esclarecendo. Este plano decidiu (2026-07-09) o oposto: transição imediata pela intenção (categoria 1), com todos os campos obrigatórios cobrados dentro de Finalizando. Precisa virar um ajuste em REQ-002.1C na próxima rodada com a Kika — não é só nomenclatura, é comportamento.

---

## 7. Critérios de pronto (Definition of Done)

- [ ] Jornada §3 executável no painel admin, turno a turno
- [ ] `fase` visível e correta após cada turno
- [ ] Campos pendentes / capturados visíveis no painel
- [ ] Software **não** perguntado se já informado em Esclarecendo
- [ ] Dúvida no meio de Finalizando não perde contexto da pergunta pendente
- [ ] Testes unitários do motor de campos passando
- [ ] Migration Alembic aplicada (`alembic upgrade head`)
- [ ] Nenhum DDL fora do Alembic (D02 implementador)

---

## 8. Riscos e decisões em aberto

| # | Tema | Opções | Recomendação provisória |
|---|------|--------|-------------------------|
| 1 | Onde gravar `tipo_produto` | `AtendimentoInfo` vs `ItemAtendimento` | `ItemAtendimento` (já modela produto+quantidade); `AtendimentoInfo` para software/faixa de funcionários |
| 2 | REQ-016 precisa revisão formal para `fase`? | Revisar REQ vs só implementar + DEC | Implementar + DEC referenciando catálogo; revisão REQ na rodada Kika |
| 3 | ~~Criar ficha `CAMPO-modelo-produto` no catálogo analista~~ | — | **Feito** — Kika já criou `CAMPO-modelo.md` e `CAMPO-faixa-funcionarios.md` (06/07/2026), ver §2 |
| 4 | Cliente pede orçamento sem nunca ter mencionado produto | Perguntar tipo / assumir relógio | Perguntar tipo (fora do MVP estrito) ou restringir testes a quem já mencionou relógio |
| 5 | PF vs PJ nesta fatia | Ignorar documento fiscal | **Ignorar** — alinhado ao escopo mínimo; PJ completo entra na próxima fatia |
| 6 | Modelo sem correspondência no catálogo | Texto livre + sinalizar vendedor (texto atual de `CAMPO-modelo.md`) vs. escalar para modo atendente | **Escalar para modo atendente** (`escalar_humano`/`ModoOperacao.HUMANO`) — decisão 2026-07-09; requer atualizar REQ-002.3B/`CAMPO-modelo.md` com a Kika, hoje eles preveem texto livre |
| 7 | Gatilho de transição Esclarecendo→Finalizando | Exigir modelo+quantidade confirmados antes (REQ-002.1C atual) vs. transitar já na intenção e coletar tudo em Finalizando | **Transitar já na intenção** — decisão 2026-07-09; requer atualizar REQ-002.1C com a Kika (ver §6) |
| 8 | ~~Drift de DDL manual fora do Alembic no banco local~~ | — | **Resolvido (2026-07-10)** — `Database._criar_tabelas()`/`create_all()` removido de `backend/database.py` (Alembic é a única fonte de DDL agora); migration `2026071002_limpeza_drift_ddl_manual.py` removeu as tabelas fantasmas `negociacoes`/`negociacao_infos` (0 linhas), renomeou as sequences esquecidas e corrigiu as 7 constraints com typo (`atendimentao`/`atendimentoes`). Verificado: `alembic upgrade head` limpo, `pytest` (41 passed, 1 falha pré-existente não relacionada), backend sobe e serve dados reais (`/health`, `/api/atendimentos/ativas`) |

---

## 9. Próximas fatias (após este MVP)

1. **+ CNPJ** — Finalizando para PJ (CAMPO-cnpj + REQ-001)
2. **+ Catraca** — novo produto + `CAMPO-software-acesso` (criar ficha)
3. **+ Inatividade** — FASE-encerrado-por-inatividade + PERG-016-009
4. **+ Endereço e contato** — campos REQ-002.3D/C restantes
5. **+ Múltiplos produtos no mesmo atendimento** — pré-requisito de schema (discussão 2026-07-11, ver `docs/dicionario_termos.md`): `AtendimentoInfo` precisa ganhar `item_atendimento_id` opcional (FK para `ItemAtendimento`) para separar info do atendimento como um todo de info específica de um produto (ex.: software de ponto por item); unique constraint vira `(atendimento_id, item_atendimento_id, chave)`
6. **WhatsApp** — T-11 quando painel estiver maduro

---

## 10. Referências

| Artefato | Caminho |
|----------|---------|
| Brainstorming | `docs/brainstorming_continuidade_2026-07.md` |
| Catálogo de conversação | `artefatos/analista_de_requisitos/catalogo_conversacao/` |
| Campo software de ponto | `artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-software-ponto.md` |
| Campo modelo | `artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-modelo.md` |
| Campo faixa de funcionários | `artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-faixa-funcionarios.md` |
| Campo quantidade (catraca, fora desta fatia) | `artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-quantidade.md` |
| Fase Esclarecendo | `artefatos/analista_de_requisitos/catalogo_conversacao/fases/FASE-esclarecendo.md` |
| Fase Finalizando | `artefatos/analista_de_requisitos/catalogo_conversacao/fases/FASE-finalizando.md` |
| REQ-002.1C (transição de fases) | `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` |
| Backlog REQ-002 | `artefatos/gerente_de_projetos/backlog_req002_tarefas.md` |
| Dicionário de termos | `docs/dicionario_termos.md` |
| Processador | `backend/services/processador.py` |
| Modelos | `backend/models.py` |

---

## Histórico de versões

| Versão | Data | Autor | Alteração |
|--------|------|-------|-----------|
| 1.0 | 2026-07-06 | Beto + Cascade | Plano MVP: relógio de ponto, Esclarecendo → Finalizando, modelo + quantidade + software |
| 1.1 | 2026-07-09 | Beto + Claude | Adicionado passo A0 (concluir renomeação Negociação→Atendimento, débito técnico) à Fase A, a partir de brainstorming de arquitetura com Claude Code. Renomeação produto/tipo_produto→modelo/produto e o motor de fases (padrão Estado/Pergunta) seguem em discussão — ver `docs/dicionario_termos.md` e histórico da conversa. |
| 1.2 | 2026-07-09 | Beto + Claude | Reconciliação com o pull da Kika (commit `c4cd9ef`, catálogo de conversação + REQ-002/014/016 atualizados): (1) substituído campo genérico "quantidade" por `CAMPO-faixa-funcionarios` (chave `faixa_funcionarios`), condicional a `software_controle_ponto="nenhum"` — `CAMPO-quantidade` é de catraca, fora desta fatia; (2) `CAMPO-modelo`/`CAMPO-faixa-funcionarios` já existem no catálogo (criados pela Kika 06/07), removida marcação de "ficha pendente"; (3) decidido que `modelo_produto` sem correspondência no catálogo escala para modo atendente (`escalar_humano`) em vez de aceitar texto livre — diverge do texto atual de `CAMPO-modelo.md`, pendente de ajuste com a Kika; (4) confirmado que a transição Esclarecendo→Finalizando é imediata pela intenção (categoria 1), com todos os campos obrigatórios cobrados em Finalizando — diverge do texto atual de REQ-002.1C, pendente de ajuste com a Kika; (5) roteiro §3 e fases B/C/E/F atualizados de acordo. |
| 1.3 | 2026-07-10 | Beto + Claude | Passo A0 implementado e concluído: migration `2026071001` renomeia `itens_negociacao`→`itens_atendimento` (tabela, PK, FKs, índices, sequence); `models.py`, comentários de `processador.py`, fallback do frontend e texto do REQ-004.4 corrigidos. Descoberto durante a implementação um drift de DDL manual fora do Alembic mais extenso (constraints com typo, tabelas fantasmas `negociacoes`/`negociacao_infos`, sequences não renomeadas), causa raiz em `Database._criar_tabelas()` — **resolvido na mesma data**: `create_all()` removido de `database.py`, migration `2026071002` limpa o drift. Risco #8 fechado. |
| 1.4 | 2026-07-11 | Beto + Claude | Discussão de arquitetura sobre `AtendimentoInfo` (EAV) antes da Fase A1: decidido manter o padrão chave-valor (encaixa bem em atributos esparsos/condicionais por produto, evita migration a cada `CAMPO-xxx` novo). Registrada limitação conhecida (FK só para `atendimento_id`, sem `item_atendimento_id`) e o plano de evolução para quando a fatia de múltiplos produtos chegar — adicionado como item 5 em §9. Detalhe completo em `docs/dicionario_termos.md`. |
| 1.5 | 2026-07-12 | Beto + Claude | Fase A concluída: **A1** enum `FaseAtendimento` em `models.py`; **A2** migration `2026071101` adiciona coluna `fase` em `atendimentos` (ENUM + índice + backfill); **A3** `services/atendimentos.py` cria atendimentos novos já com `fase=ESCLARECENDO`, testado ponta a ponta via API real; **A4** decisão registrada como DEC-006 em `decisoes_requisitos.md`. Achado adicional durante o A2: PKs de `atendimentos`/`atendimento_infos` ainda com nome antigo (`negociacoes_pkey`/`negociacao_infos_pkey`) — corrigido em migration `2026071102` (mesma categoria de drift do A0, sem typo desta vez). |
