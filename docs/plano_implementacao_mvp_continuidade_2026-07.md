# Plano de Implementação — MVP Continuidade (jul/2026)

<!-- CLASSIFICACAO: HISTORICO -->

**Versão:** 2.4  
**Data:** 2026-07-06 (atualizado 2026-07-15)  
**Autor:** Beto + Cascade + Claude  
**Status:** Implementado (Fases A-H concluídas) — verificação visual no navegador ainda pendente; alinhamento de REQs com a Kika (§8 item 7) concluído  
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

Nota: o desenho de classes evoluiu para o motor `Intenção×Fase→Ações` (`services/conversacao/motor.py`): `RegraIntencao` liga uma `Intencao` (ou `None` = wildcard) a uma `FaseAtendimento` (ou `None` = regra global) e a um builder de `GrupoAcoes`. O antigo padrão `EstadoAtendimento`/`Pergunta` discutido no brainstorming foi substituído por este modelo. Ver `docs/dicionario_termos.md` para detalhes.

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
| **B1** | ✅ Concluído (2026-07-12) — `catalogo_campos.py` | Criado `backend/services/conversacao/catalogo_campos.py` (novo pacote `services/conversacao/`, conforme diagrama §4): `CampoDef` (id_catalogo, chave, produtos_aplicáveis, pergunta, ordem, `aplicavel` callable) + `campos_do_produto()`. Desacoplado de ORM/SQLAlchemy de propósito — `aplicavel` recebe snapshot `chave→valor`, não objetos do banco | Catálogo analista |
| **B2** | ✅ Concluído (2026-07-12) — Mapear `CAMPO-software-ponto` | `CAMPO_SOFTWARE_PONTO` em `catalogo_campos.py`: chave `software_controle_ponto`, pergunta de `CAMPO-software-ponto.md`, aplicável a `relogio_ponto`. Testes em `tests/test_catalogo_campos.py` (5 casos, todos passando) | B1 |
| **B3** | ✅ Concluído (2026-07-12) — Mapear `CAMPO-modelo` | `CAMPO_MODELO` em `catalogo_campos.py`: chave `modelo_produto`, pergunta específica de relógio (cartográfico/eletrônico × cartão/barras/biometria/facial), `ordem=10`. Adicionado campo `destino` a `CampoDef` (`DESTINO_ITEM_ATENDIMENTO_PRODUTO_ID`) para deixar explícito que este campo resolve para `ItemAtendimento.produto_id`, não `AtendimentoInfo` — a resolução/validação (`escalar_humano` se sem correspondência) fica pra Fase F (F2), aqui é só a declaração | B1 |
| **B4** | ✅ Concluído (2026-07-12) — Mapear `CAMPO-faixa-funcionarios` | `CAMPO_FAIXA_FUNCIONARIOS` em `catalogo_campos.py`: chave `faixa_funcionarios`, `ordem=30`, `aplicavel` consulta `software_controle_ponto` no snapshot de valores (não pendência se ainda não respondido; aplicável só se `="nenhum"`, case/espaço-insensível) | B1, B2 |
| **B5** | ✅ Concluído (2026-07-12) — `MensagemId.PEDIR_MODELO`, `PEDIR_SOFTWARE_PONTO`, `PEDIR_FAIXA_FUNCIONARIOS` | Adicionados em `respostas/catalogo.py` (IDs 24-26, textos específicos de relógio de ponto — não reutilizam templates genéricos) | B1 |

**Fase B concluída.** Testes: `tests/test_catalogo_campos.py` (11 casos) + `tests/test_respostas_catalogo.py` (3 casos), todos passando.

**Nota:** `campos/CAMPO-quantidade.md` (também criado pela Kika) é de **controle de acesso/catraca** — fora desta fatia. Quando entrarmos em catraca (próxima fatia, §9), mapeia para a coluna real `ItemAtendimento.quantidade`, não para `AtendimentoInfo`.

### Fase C — Motor `campos_pendentes()`

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **C1** | ✅ Concluído (2026-07-12) — `campos_pendentes(atendimento) -> list[CampoDef]` | Criado `backend/services/conversacao/campos_pendentes.py`. Cruza `catalogo_campos.py` + `AtendimentoInfo` + `ItemAtendimento`; ignora preenchidos e não aplicáveis. Retorna `[]` se o tipo de produto ainda não foi identificado | B1 |
| **C2** | ✅ Concluído (2026-07-12) — `proxima_pergunta(atendimento) -> CampoDef \| None` | Primeiro de `campos_pendentes()` (já vem ordenado por `ordem`). **Não é uma regra de sequência obrigatória** — só decide o que perguntar quando nada veio na mensagem | C1 |
| **C3** | ✅ Concluído (2026-07-12) — Regra `nao_perguntar_de_novo` | Função pública `nao_perguntar_de_novo(campo, atendimento)`, nome espelhando o efeito do catálogo. Verifica `AtendimentoInfo` para campos com `destino` padrão, e `ItemAtendimento.produto_id` para `CAMPO_MODELO` (via `CampoDef.destino`) | C1 |
| **C4** | ✅ Concluído (2026-07-12) — Regras condicionais (aplicabilidade) | Já implementadas na Fase B (`CampoDef.se_aplica`, `_aplicavel_faixa_funcionarios`) — C1 só precisava plugar corretamente (`se_aplica(tipo_produto, valores)`) | C1 |

**Nota de implementação (2026-07-12):** `campos_pendentes()` precisa saber o `tipo_produto` do atendimento pra decidir quais campos valem. Hoje isso só existe em `AtendimentoInfo` (chave `tipos_produto`, gravada por `processador.py::_atualizar_infos_atendimento` — lista separada por vírgula, MVP usa o primeiro valor) — `ItemAtendimento.tipo_produto_id` ainda não é populado em lugar nenhum do código (isso é o D2, que ainda não foi feito). Isolei essa leitura numa função interna (`_tipo_produto_atual`) pra trocar de fonte depois sem afetar o resto do módulo, quando/se a Fase D migrar isso pra `ItemAtendimento`. Testes em `tests/test_campos_pendentes.py` (10 casos, com stubs leves — não toca o banco).


### Fase D — Esclarecendo (responder sem qualificar)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **D1** | ✅ Concluído (2026-07-12) — Roteamento por categoria no processador | Novo método `_responder_categoria3()` (extraído de `_gerar_resposta_por_intencao`, mesmo comportamento) reutilizado em dois pontos novos de `_decidir_resposta`: status `NOVO` e `SEM_EMPRESA` agora respondem categoria 3 (`PERGUNTAR_PRODUTO`/`PERGUNTAR_PRECO`/`FORA_CONTEXTO`, via `_INTENCOES_RAG` — que já existia mas nunca tinha sido usado) via Q&A/RAG **antes** de cair no fallback genérico (`SAUDACAO_NOVO_CONTATO`/`PERGUNTAR_CNPJ`) | T-03 backlog REQ-002 |
| **D2** | ✅ Já coberto pela infraestrutura existente | `_atualizar_infos_atendimento()` já gravava `tipos_produto` em `AtendimentoInfo`; só faltava D1 chamar esse caminho pra telefones `NOVO` (via `_garantir_contato_e_atendimento_qualificacao`, que já existia) — confirmado funcionando ponta a ponta | A3 |
| **D3** | ✅ Concluído (2026-07-12) — Extração passiva de software | `_SOFTWARES_PONTO_CONHECIDOS` em `classificador.py` (Domínio, Alterdata, TOTVS, Senior, Secullum, Ahgora, RH Bravo) → novo campo `EntidadesExtraidas.software_ponto` → gravado em `AtendimentoInfo` com a chave de `CAMPO_SOFTWARE_PONTO` | B2 |
| **D4** | ✅ Concluído (2026-07-12) — Extração passiva de modelo/faixa de funcionários | `_TIPO_LEITOR_PALAVRAS` (biometria/facial/cartao/cartografico/eletronico) → `EntidadesExtraidas.tipo_leitor_mencionado`; `_REGEX_FUNCIONARIOS` → `EntidadesExtraidas.faixa_funcionarios`. **Nota:** `tipo_leitor_mencionado` é um sinal cru gravado numa chave provisória em `AtendimentoInfo` — não resolve para `ItemAtendimento.produto_id` ainda (isso é F2, quando o catálogo `Modelo` tiver dados reais) | — |

**Achados durante a implementação:**
- **Bug corrigido:** `classificador.py::classificar()` combina entidades da regra + LLM quando cai para o caminho da LLM, mas o merge não incluía os 3 campos novos (`software_ponto`, `tipo_leitor_mencionado`, `faixa_funcionarios`) — ficavam `None` mesmo quando a regra os havia extraído corretamente. Corrigido no mesmo commit.
- **Observação (não é bug, é limite de escopo):** o classificador por regras não tem regra própria para `PERGUNTAR_PRECO` (cai em `PEDIR_ORCAMENTO` via a palavra "preço") nem para `FORA_CONTEXTO` (só alcançável hoje via LLM) — então testes de ponta a ponta via API real para essas duas intenções dependem do LLM (Groq) responder de forma confiável, o que nem sempre aconteceu neste ambiente de dev durante os testes manuais. **D1/D2/D3/D4 foram verificados de forma determinística** — sem depender do classificador acertar — em `tests/test_processador_categoria3_pre_identificacao.py`, injetando um `ResultadoClassificacao` já pronto e chamando `_decidir_resposta()` direto contra o banco real.

**Referência backlog:** T-03 (pré-identificação) — concluído nesta fatia (parte de D1).

### Fase E — Transição Esclarecendo → Finalizando

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **E1** | ✅ Concluído (2026-07-13) — Detectar intenção de orçamento | Novo método `_iniciar_ou_continuar_finalizando()`: `PEDIR_ORCAMENTO` muda `atendimento.fase` para `FINALIZANDO` **imediato** (idempotente — se já estiver lá, não repete), sem exigir modelo/software confirmados antes | Classificador |
| **E2** | ✅ Concluído (2026-07-13) — Mensagem de transição | Novo `MensagemId.INICIAR_FINALIZANDO` ("Ótimo! Vou precisar de algumas informações para montar o orçamento.") em `respostas/catalogo.py` — só entra na composição quando há campo pendente real (não quando o fallback é `PEDIR_TIPO_PRODUTO`, tipo de produto ainda desconhecido) | B5 |
| **E3** | ✅ Concluído (2026-07-13) — Reprocessar mensagem de transição contra Finalizando | Como `_atualizar_infos_atendimento` (D2/D3/D4) já roda **antes** de `_iniciar_ou_continuar_finalizando`, a mesma mensagem que disparou a transição já fica refletida em `campos_pendentes()` — ex.: "quero orçamento, já uso Domínio" captura software no mesmo turno e pula direto pra pergunta de modelo. Nova tabela `_MENSAGEM_ID_POR_CAMPO` faz a ponte `CampoDef.chave` (catalogo_campos.py) → `MensagemId` (respostas/catalogo.py) | C2, E1 |

**Nota de implementação:** `_gerar_resposta_por_intencao` precisou ganhar `db`/`atendimento` como parâmetros (antes não tinha acesso a nenhum dos dois) — atualizado nos 3 pontos de chamada. Testado ponta a ponta via API real (funcionou perfeitamente: telefone novo pedindo orçamento já entra em Finalizando e recebe a pergunta certa; mensagem composta com software captura no mesmo turno) e via `tests/test_processador_transicao_finalizando.py` (5 casos, incluindo idempotência da transição e a ponte campo→pergunta usando um `Produto`/`TipoProduto` de teste, já que o catálogo real ainda está vazio nesta base).

### Fase F — Finalizando (coleta ativa)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **F1** | ✅ Concluído (2026-07-13) — Loop de coleta no processador | Novo `_processar_finalizando()` intercepta **toda** mensagem em Finalizando (não mais roteado só por intenção): tenta modelo (F2), dúvida (F3) ou captura solta pra pendência atual (`_capturar_resposta_direta_pendente` — cobre "80" sem a palavra "funcionários", ou nome de software fora do catálogo conhecido), recalcula `campos_pendentes()` e pergunta o que falta | C2, C4, D4 |
| **F2** | ✅ Concluído (2026-07-13) — Validação mínima (modelo) | `_tentar_resolver_modelo()`: busca `Produto` real via `tipo_leitor_mencionado` (D4); sem correspondência após 2 tentativas → `atendimento.modo_operacao = HUMANO` (primeiro escalonamento automático do sistema — até aqui só existia troca manual via `PATCH /api/atendimentos/{id}/modo-operacao`). Faixa/software: aceitos como texto livre pela captura solta do F1 (sem validação de formato adicional nesta fatia) | — |
| **F3** | ✅ Concluído (2026-07-13) — Retomada após dúvida | `_retomar_apos_duvida()`: categoria 3 durante Finalizando responde via Q&A/RAG e reapresenta a pergunta pendente (`MensagemId.RETOMAR_PERGUNTA_PENDENTE`) — fase e progresso da coleta preservados | D1 |
| **F4** | ✅ Concluído (2026-07-13) — Resumo ao completar | `_gerar_resumo_finalizando()` + novo `MensagemId.RESUMO_FINALIZANDO` (transformer `montar_resumo_finalizando`): lista modelo/software/faixa (só o que se aplica) e pede confirmação | C1 |

**Achados durante a implementação:**
- **Bug corrigido:** primeira versão da captura solta (F1) aceitava *qualquer* texto como resposta a `software_controle_ponto` sempre que a intenção não era saudação/confirmação/negação — em smoke test manual, a própria repetição "Quero orçamento" (intenção `pedir_orcamento` reconhecida) foi sequestrada como se fosse o nome do software. Corrigido: a captura solta só entra em jogo quando a intenção classificada é `DESCONHECIDO` (nenhuma regra bateu) — coberto por `test_f1_nao_sequestra_intencao_reconhecida_como_resposta`.
- **Bug corrigido:** `_atualizar_infos_atendimento` sempre sobrescrevia `tipos_produto` com o que a mensagem atual mencionasse — uma dúvida tangencial em Finalizando ("vocês têm catraca também?") trocava o tipo de produto do atendimento de `relogio_ponto` para `catraca` no meio da coleta, esvaziando `campos_pendentes()` (nenhum `CampoDef` cadastrado pra catraca) e pulando direto pro resumo vazio. Descoberto em smoke test manual (F3), não pego pelos testes determinísticos porque nenhum deles testava uma dúvida sobre um *produto diferente* do já capturado. Corrigido: `tipos_produto` só é gravado/atualizado enquanto `fase != FINALIZANDO` — uma vez em Finalizando, o tipo já está decidido. Coberto por `test_f3_duvida_sobre_outro_produto_nao_reescreve_tipos_produto`.
- **Limitação conhecida (não é bug, é falta de dado):** `Produto`/`TipoProduto` continuam sem nenhuma linha semeada neste ambiente — `_tentar_resolver_modelo()` está implementado corretamente para quando existir catálogo real, mas hoje **sempre** cai no caminho "sem correspondência" e, na prática, todo atendimento que chega a perguntar o modelo acaba escalando para atendimento humano após a 2ª tentativa. Confirmado ponta a ponta via smoke test (2 tentativas com "biométrico" → `modo_operacao = humano`). Semear o catálogo é pré-requisito de fato para usar o MVP em produção, fora do escopo deste plano.
- **Observação (ambiguidade pré-existente do classificador, não nova):** frases que respondem ao modelo mencionando a tecnologia (ex.: "seria biométrico") frequentemente também batem na regra de `PERGUNTAR_PRODUTO` (palavra "biométrico"), fazendo o turno cair no caminho de dúvida (F3) em vez de ser tratado como resposta direta. `_processar_finalizando` já tenta resolver modelo *antes* de decidir se é dúvida (a extração de `tipo_leitor_mencionado` independe da intenção classificada), então o valor não se perde — mas a resposta ao cliente mistura o texto de dúvida com a pergunta retomada, o que é um pouco estranho quando a intenção "certa" seria só confirmar o modelo. Ajustar a regra de `PERGUNTAR_PRODUTO` para não competir com respostas de modelo fica para uma iteração futura do classificador.

**Testado ponta a ponta via API real** (fluxo completo: orçamento → tentativa de modelo sem catálogo → 2ª tentativa escala pra humano; em atendimento separado com modelo simulado via dados de teste no catálogo — resumo final, dúvida com retomada, captura solta de "nenhum"/"80") e via `tests/test_processador_finalizando_coleta_ativa.py` (8 casos). Suíte completa: 96/96.

### Fase G — Criando Orçamento (handoff mínimo)

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **G1** | ✅ Concluído (2026-07-13) — Confirmação → `em_orcamentacao` | `_concluir_finalizando()`: só conclui se o `CONFIRMAR` for resposta a um resumo (F4) já apresentado numa mensagem anterior (marca `AtendimentoInfo` chave `resumo_finalizando_apresentado`) — ver achado abaixo | F4 |
| **G2** | ✅ Concluído (2026-07-13) — `modo_operacao = HUMANO` | Mesmo mecanismo do escalonamento do F2 (suprime resposta automática daqui em diante) | — |
| **G3** | ✅ Concluído (2026-07-13) — Mensagem ao cliente | Novo `MensagemId.ORCAMENTO_ENCAMINHADO`: "Recebi suas informações. Nossa equipe vai preparar o orçamento e retorna em breve." | — |

**Achados durante a implementação:**
- **Bug corrigido:** um "ok"/"sim" solto pode ser classificado como `CONFIRMAR` mesmo sendo a *primeira* mensagem a chegar depois de tudo capturado (`campos_pendentes()` vazio) — nesse caso o cliente nunca viu o resumo, então concluir o handoff ali seria errado (descoberto em smoke test manual: mandei "ok" como primeira mensagem pós-captura e o sistema já escalou pra humano sem nunca ter mostrado o resumo). Corrigido: `_gerar_resumo_finalizando()` marca `resumo_finalizando_apresentado` em `AtendimentoInfo`; `_concluir_finalizando()` só roda se essa marca já existir — ou seja, exige um turno de resumo antes de aceitar a confirmação. Coberto por `test_g1_primeira_mensagem_apos_tudo_capturado_nao_conclui_mesmo_se_confirmar`.
- **Refinamento do guard de `tipos_produto` (Fase F):** o guard "só grava enquanto `fase != FINALIZANDO`" (v2.1) foi trocado por "só grava se ainda não houver valor" — o guard por fase bloqueava também a gravação *legítima* da primeira vez que o cliente informa o tipo de produto depois de já estar em Finalizando (ex.: resposta ao fallback `PEDIR_TIPO_PRODUTO`), o que travaria a coleta pra sempre. Coberto por `test_tipo_produto_pode_ser_informado_apos_ja_estar_em_finalizando`. Combinado com um novo ramo em `_processar_finalizando`: `campos_pendentes()` vazio por "tipo de produto desconhecido" (não é "tudo capturado") agora reapresenta `PEDIR_TIPO_PRODUTO` em vez de ir pro resumo vazio — coberto por `test_g_confirmar_sem_tipo_produto_conhecido_nao_conclui`.

**Testado ponta a ponta via API real** (fluxo completo: orçamento com software junto → modelo simulado via dado de teste no catálogo → "ok" mostra resumo sem concluir → "sim" conclui, fase vira `em_orcamentacao` e `modo_operacao` vira `humano`) e via `tests/test_processador_finalizando_handoff.py` (5 casos). Suíte completa: 101/101.

### Fase H — Painel e testes

| # | Entrega | Detalhe | Depende de |
|---|---------|---------|------------|
| **H1** | ✅ Concluído (2026-07-13) — Exibir `fase` na UI da conversa | `Atendimento.to_dict()` (bug: coluna existia desde A2 mas nunca era serializada) + endpoints `/api/atendimentos/ativas` e `/api/conversa/{telefone}` passaram a incluir `fase`; badge colorido (`rotuloFase`/`classesFase` em `utils/atendimento.js`) em 3 pontos da UI: `ConversaInfo` (faixa do chat), lista e detalhe de `AcompanhamentoPage`, e `AtendimentoDetalhes` (modal) | A2 |
| **H2** | ✅ Concluído (2026-07-13) — Exibir campos capturados / pendentes | Tabela "Informações coletadas" (`AtendimentoDetalhes.jsx`) ganhou rótulos amigáveis por chave (`LABELS_INFO`) e pill de status visual (verde "Capturado" / amarelo "Pendente") no lugar do texto `sim`/`não` | C1 |
| **H3** | ✅ Concluído (2026-07-13) — Roteiro de teste manual | `artefatos/qa/roteiros_teste/RT-012-jornada-mvp-relogio-ponto.md` — jornada completa §3 + variantes (composta, dúvida mid-coleta) + os dois caminhos do modelo (catálogo semeado vs. escalonamento, já que `produtos`/`tipos_produto` estão vazios neste ambiente) + conferência visual do H1/H2 | — |
| **H4** | ✅ Concluído — Testes automatizados backend | Já satisfeito como subproduto das Fases B-G, sem trabalho adicional necessário: `test_catalogo_campos.py` + `test_campos_pendentes.py` (21 casos, `campos_pendentes()`/aplicabilidade), `test_processador_transicao_finalizando.py` (5 casos, esclarecendo→finalizando) + `test_processador_finalizando_handoff.py` (5 casos, finalizando→em_orcamentacao) — cobrem as 3 fases do ciclo de vida sem depender de LLM real (injetam `ResultadoClassificacao` pronto) | C1, E1 |

**Achados durante a implementação:**
- **Bug corrigido:** `Atendimento.to_dict()` nunca serializava `fase` — a coluna existe desde a Fase A (2026-07-12), mas ninguém tinha notado que o dicionário usado pelas 3 rotas de API relevantes (`/api/atendimentos/{id}`, `/api/atendimentos/ativas`, `/api/conversa/{telefone}`) simplesmente não a incluía. Sem esse fix, H1 não teria dado onde exibir. Coberto por `test_atendimento_to_dict.py` (novo).
- **Observação (não é bug, limitação de ambiente):** como `produtos`/`tipos_produto` seguem sem dados semeados (mesma observação já registrada nas Fases F/G), o roteiro de QA (H3) documenta os dois caminhos possíveis para a resolução de modelo — feliz (catálogo semeado manualmente) e o caminho real de hoje (escalonamento após 2 tentativas) — em vez de assumir só o cenário ideal do §3.
- **Não verificado em navegador real:** as mudanças de frontend foram verificadas via `npm run build` (compila sem erros) e via `curl` direto contra as APIs (confirmando que `fase` chega corretamente nos 3 endpoints, com dados reais do ambiente). Não há ferramenta de automação de navegador disponível nesta sessão, e o container de frontend em execução (`agenteassistentedevendas-frontend-1`) serve um bundle estático via nginx, aparentemente exposto publicamente via túnel Cloudflare (`app.auxvendas.com`) — não reconstruí/reiniciei esse container para não afetar um serviço possivelmente ao vivo. **Recomendo verificar visualmente no navegador (`npm run dev` local, ou rebuild do container) antes de considerar H1/H2 prontos para uso real.**

**Suíte completa: 102/102.**

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

~~**Pendência de alinhamento formal (RESOLVIDA 2026-07-14):**~~ `REQ-002.1C` foi reescrito na v1.33 (14/07/2026) para refletir a transição imediata pela intenção + tipo de produto, sem exigir modelo/quantidade antes. Decisão registrada como DEC-007 em `decisoes_requisitos.md`. Também formalizada a transição bidirecional Finalizando⇄Esclarecendo para dúvidas (cat. 3) e o tratamento de mensagem composta (intenção + dúvida).

---

## 7. Critérios de pronto (Definition of Done)

- [ ] Jornada §3 executável no painel admin, turno a turno (backend pronto — verificação visual no navegador ainda pendente, ver achados da Fase H)
- [x] `fase` visível e correta após cada turno (backend + UI — 3 pontos do painel)
- [x] Campos pendentes / capturados visíveis no painel (tabela com status visual)
- [x] Software **não** perguntado se já informado em Esclarecendo
- [x] Dúvida no meio de Finalizando não perde contexto da pergunta pendente (F3)
- [x] Testes unitários do motor de campos passando (102/102)
- [x] Migration Alembic aplicada (`alembic upgrade head`)
- [x] Nenhum DDL fora do Alembic (D02 implementador)

---

## 8. Riscos e decisões em aberto

| # | Tema | Opções | Recomendação provisória |
|---|------|--------|-------------------------|
| 1 | Onde gravar `tipo_produto` | `AtendimentoInfo` vs `ItemAtendimento` | `ItemAtendimento` (já modela produto+quantidade); `AtendimentoInfo` para software/faixa de funcionários |
| 2 | REQ-016 precisa revisão formal para `fase`? | Revisar REQ vs só implementar + DEC | Implementar + DEC referenciando catálogo; revisão REQ na rodada Kika |
| 3 | ~~Criar ficha `CAMPO-modelo-produto` no catálogo analista~~ | — | **Feito** — Kika já criou `CAMPO-modelo.md` e `CAMPO-faixa-funcionarios.md` (06/07/2026), ver §2 |
| 4 | Cliente pede orçamento sem nunca ter mencionado produto | Perguntar tipo / assumir relógio | Perguntar tipo (fora do MVP estrito) ou restringir testes a quem já mencionou relógio |
| 5 | PF vs PJ nesta fatia | Ignorar documento fiscal | **Ignorar** — alinhado ao escopo mínimo; PJ completo entra na próxima fatia |
| 6 | Modelo sem correspondência no catálogo | Texto livre + sinalizar vendedor (texto atual de `CAMPO-modelo.md`) vs. escalar para modo atendente | **Escalar para modo atendente** (`escalar_humano`/`ModoOperacao.HUMANO`) — decisão 2026-07-09, **implementado** (F2). Pendência restante: atualizar REQ-002.3B/`CAMPO-modelo.md` com a Kika (ainda preveem texto livre) |
| 7 | ~~Gatilho de transição Esclarecendo→Finalizando~~ | — | **Resolvido (2026-07-14)** — REQ-002.1C reescrito (v1.33): transição imediata pela intenção + tipo de produto, sem gate de campos. DEC-007 registrada. Também formalizada transição bidirecional Finalizando⇄Esclarecendo para dúvidas |
| 8 | ~~Drift de DDL manual fora do Alembic no banco local~~ | — | **Resolvido (2026-07-10)** — `Database._criar_tabelas()`/`create_all()` removido de `backend/database.py` (Alembic é a única fonte de DDL agora); migration `2026071002_limpeza_drift_ddl_manual.py` removeu as tabelas fantasmas `negociacoes`/`negociacao_infos` (0 linhas), renomeou as sequences esquecidas e corrigiu as 7 constraints com typo (`atendimentao`/`atendimentoes`). Verificado: `alembic upgrade head` limpo, `pytest` (41 passed, 1 falha pré-existente não relacionada), backend sobe e serve dados reais (`/health`, `/api/atendimentos/ativas`) |

---

## 9. Próximas fatias (após este MVP)

1. **+ CNPJ** — Finalizando para PJ (CAMPO-cnpj + REQ-001)
2. **+ Catraca** — novo produto + `CAMPO-software-acesso` (criar ficha)
3. **+ Inatividade** — FASE-encerrado-por-inatividade + PERG-016-009 + PERG-016-009B (confirmação de interesses anteriores, criada 2026-07-15)
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
| 1.6 | 2026-07-12 | Beto + Claude | Início da Fase B: **B1** criado `backend/services/conversacao/catalogo_campos.py` (novo pacote, `CampoDef` + `campos_do_produto()`, desacoplado de ORM); **B2** `CAMPO-software-ponto` mapeado (`CAMPO_SOFTWARE_PONTO`). Testes em `tests/test_catalogo_campos.py` (5 casos). |
| 1.7 | 2026-07-12 | Beto + Claude | Fase B concluída: **B3** `CAMPO_MODELO` mapeado (chave `modelo_produto`, `ordem=10`), com novo campo `CampoDef.destino` explicitando que resolve para `ItemAtendimento.produto_id` (não `AtendimentoInfo`) — resolução/escalonamento fica pra F2; **B4** `CAMPO_FAIXA_FUNCIONARIOS` mapeado (chave `faixa_funcionarios`, `ordem=30`), `aplicavel` consulta `software_controle_ponto` no snapshot (dependência de aplicabilidade); **B5** `MensagemId.PEDIR_MODELO`/`PEDIR_SOFTWARE_PONTO`/`PEDIR_FAIXA_FUNCIONARIOS` (IDs 24-26) em `respostas/catalogo.py`. Testes: 11 casos em `test_catalogo_campos.py` + 3 em `test_respostas_catalogo.py` (novo), todos passando. |
| 1.8 | 2026-07-12 | Beto + Claude | Fase C concluída: criado `backend/services/conversacao/campos_pendentes.py` com `campos_pendentes()` (C1), `proxima_pergunta()` (C2), `nao_perguntar_de_novo()` (C3) — C4 já vinha pronto da Fase B, só precisava ser plugado corretamente. Decisão registrada: `tipo_produto` do atendimento é lido de `AtendimentoInfo` (chave `tipos_produto`), não de `ItemAtendimento.tipo_produto_id` — porque nada no código ainda popula essa FK (isso é o D2, pendente); leitura isolada numa função interna pra trocar depois sem afetar o resto do módulo. Testes em `test_campos_pendentes.py` (10 casos, com stubs leves, sem tocar o banco). Também corrigido nesta sessão (fora do escopo da Fase C, a pedido do Beto): bug pré-existente em `classificador.py::_limpar_nome` que descartava conectores de sobrenome ("da"/"de"/"do") por causa de `_STOPWORDS_NOME` — removida a filtragem de stopwords nessa função (lista mantida intacta); suíte completa 100% verde pela primeira vez (66/66). |
| 1.9 | 2026-07-12 | Beto + Claude | Fase D concluída — primeira vez que o motor de fases toca o `processador.py` de verdade: **D1** extraído `_responder_categoria3()` e plugado em `_decidir_resposta` pros status `NOVO`/`SEM_EMPRESA` (finalmente usa `_INTENCOES_RAG`, que existia mas nunca tinha sido chamado); **D2** confirmado que a infraestrutura existente já cobria o registro passivo de `tipos_produto`, só faltava D1 acionar esse caminho pra telefones novos; **D3** `_SOFTWARES_PONTO_CONHECIDOS` + `EntidadesExtraidas.software_ponto`; **D4** `_TIPO_LEITOR_PALAVRAS`/`_REGEX_FUNCIONARIOS` + `tipo_leitor_mencionado`/`faixa_funcionarios` (tipo_leitor grava em chave provisória — resolução pra `Modelo` real fica pra F2). Corrigido no caminho: bug no merge regra+LLM de `classificar()` que descartava os 3 campos novos quando caía pro fallback LLM. Testado ponta a ponta via API real (funcionou perfeitamente para `PERGUNTAR_PRODUTO`, que tem regra determinística) e via `tests/test_processador_categoria3_pre_identificacao.py` (6 casos, injeta classificação pronta pra não depender do LLM/regras acertarem — `PERGUNTAR_PRECO` e `FORA_CONTEXTO` não têm regra própria hoje, só LLM, que nem sempre respondeu de forma confiável neste ambiente). Suíte completa: 83/83. |
| 2.0 | 2026-07-13 | Beto + Claude | Fase E concluída: **E1** `atendimento.fase` agora muda de verdade para `finalizando` ao detectar `PEDIR_ORCAMENTO` (idempotente); **E2** novo template `INICIAR_FINALIZANDO`; **E3** a mesma mensagem que dispara a transição já é refletida em `campos_pendentes()` (D2/D3/D4 rodam antes), com nova tabela `_MENSAGEM_ID_POR_CAMPO` ligando o catálogo declarativo (Fase B) aos templates de pergunta (B5). `_gerar_resposta_por_intencao` ganhou `db`/`atendimento` como parâmetros. Testado ponta a ponta via API real (telefone novo → orçamento → já entra em Finalizando com a pergunta certa; mensagem composta com software captura no mesmo turno) e via `tests/test_processador_transicao_finalizando.py` (5 casos). Suíte completa: 88/88. |
| 2.1 | 2026-07-13 | Beto + Claude | Fase F concluída (última fase de lógica de conversação antes do handoff G/painel H): **F1** novo `_processar_finalizando()` intercepta toda mensagem em Finalizando (rotear só por intenção não bastava — respostas que citam tecnologia, ex.: "biométrico", batem em regra de dúvida); **F2** `_tentar_resolver_modelo()` busca `Produto` real via `tipo_leitor_mencionado`, sem correspondência após 2 tentativas escala `modo_operacao = HUMANO` (primeiro escalonamento automático do sistema — até então só existia troca manual via API); **F3** `_retomar_apos_duvida()` responde dúvida + reapresenta pendência (`RETOMAR_PERGUNTA_PENDENTE`); **F4** `_gerar_resumo_finalizando()` + `RESUMO_FINALIZANDO`. Dois bugs pegos e corrigidos durante smoke test manual (não pelos testes determinísticos, que não cobriam esses cenários específicos): captura solta sequestrando intenções já reconhecidas como se fossem resposta (restringida a `DESCONHECIDO`), e dúvida sobre outro produto reescrevendo `tipos_produto` e esvaziando `campos_pendentes()` (travado: só grava enquanto `fase != FINALIZANDO`). `Produto`/`TipoProduto` seguem sem dados semeados neste ambiente — na prática, toda resolução de modelo escala pra humano após a 2ª tentativa (esperado, documentado, não é bug). Testado ponta a ponta via API real (2 fluxos completos) e via `tests/test_processador_finalizando_coleta_ativa.py` (8 casos). Suíte completa: 96/96. |
| 2.2 | 2026-07-13 | Beto + Claude | Fase G concluída — fecha a lógica de conversação do MVP (só resta H, painel/QA): **G1** `_concluir_finalizando()` transita `fase` para `em_orcamentacao` quando o cliente confirma o resumo (F4); **G2** reaproveita `modo_operacao = HUMANO` (mesmo mecanismo do escalonamento do F2) pra suprimir resposta automática dali em diante; **G3** novo `MensagemId.ORCAMENTO_ENCAMINHADO`. Bug pego em smoke test manual (não pelos testes determinísticos, que evitavam sem querer o cenário): um "ok"/"sim" solto pode vir classificado `CONFIRMAR` mesmo sendo a *primeira* mensagem depois de tudo capturado — nesse caso o cliente nunca viu o resumo, então não é confirmação dele; corrigido exigindo que o resumo já tenha sido apresentado (nova chave `resumo_finalizando_apresentado` em `AtendimentoInfo`) antes de aceitar um `CONFIRMAR` como handoff. Aproveitado pra corrigir também um efeito colateral do guard de `tipos_produto` da Fase F: ele bloqueava a gravação legítima do tipo de produto quando informado só depois de já estar em Finalizando (ex.: resposta ao fallback `PEDIR_TIPO_PRODUTO`) — trocado de "só grava se `fase != FINALIZANDO`" para "só grava se ainda não houver valor". Testado ponta a ponta via API real (fluxo completo: resumo → confirmação → handoff, com verificação de que a primeira mensagem "solta" não conclui sozinha) e via `tests/test_processador_finalizando_handoff.py` (5 casos). Suíte completa: 101/101. |
| 2.3 | 2026-07-13 | Beto + Claude | **Fase H concluída — plano de MVP Continuidade fechado (Fases A-H, todas ✅).** **H1** `fase` passou a ser serializada em `Atendimento.to_dict()` (bug: existia desde a Fase A mas nunca era exposta pela API) e exibida como badge colorido em 3 pontos do painel (`ConversaInfo`, `AcompanhamentoPage`, `AtendimentoDetalhes`), via novo par `rotuloFase`/`classesFase` em `utils/atendimento.js`; **H2** tabela "Informações coletadas" ganhou rótulos amigáveis e pill de status (verde/amarelo) no lugar de `sim`/`não`; **H3** roteiro `RT-012-jornada-mvp-relogio-ponto.md` (jornada completa + variantes + os dois caminhos de resolução de modelo, dado que o catálogo segue sem seed); **H4** já estava satisfeito como subproduto das Fases B-G (36 testes cobrindo `campos_pendentes()` e as 3 transições de fase). Frontend verificado via `npm run build` (sem erros) e via API real (`curl` confirmando `fase` nos 3 endpoints) — não verificado em navegador (sem ferramenta de automação disponível nesta sessão) nem reconstruído o container de frontend em execução, que parece exposto publicamente via túnel Cloudflare; recomendo verificação visual antes de dar por definitivamente pronto. Suíte completa: 102/102. |
| 2.4 | 2026-07-15 | Cascade + Kika | Revisão pós-MVP: (1) pendência de alinhamento REQ-002.1C **resolvida** — v1.33 reflete transição imediata + bidirecional Finalizando⇄Esclarecendo + mensagem composta (DEC-007); (2) §8 itens 6 e 7 atualizados (6: implementado F2, pendência só documental; 7: fechado); (3) nota de arquitetura §4 atualizada (motor `Intenção×Fase→Ações` em `motor.py` substituiu o padrão Estado/Pergunta); (4) §9 item 3 atualizado com PERG-016-009B (confirmação de interesses anteriores após reengajamento, criada na mesma data). |
