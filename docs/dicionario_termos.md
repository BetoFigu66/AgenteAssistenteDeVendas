# Dicionário de Termos — Assistente de Vendas via WhatsApp com IA

**Versão:** 0.1
**Data:** 2026-07-09
**Autor:** Beto + Claude
**Status:** Rascunho — origem: brainstorming de arquitetura sobre `docs/plano_implementacao_mvp_continuidade_2026-07.md`
**Objetivo:** registrar o significado canônico de termos que já geraram ou podem gerar ambiguidade no projeto — entre código, artefatos de requisitos e documentação de negócio.

---

## Convenção de nomenclatura

Termos genéricos usados com mais de um sentido no projeto (ex.: "categoria", "score") **não devem ser citados sozinhos** fora de um contexto que já desambiguize:

- **Se o termo está aninhado a uma entidade/campo que já desambiguiza** (ex.: `Produto.categoria`, `ParRecuperado.score`), pode ficar curto — o nome do campo pode continuar sendo só `categoria` ou `score`, porque o contexto (a entidade) já resolve a ambiguidade.
- **Em texto solto/documentação/conversa**, sempre qualificar: "categoria de roteamento", "categoria de report", "categoria de produto", "categoria de diretriz", "categoria de requisito"; "score do RAG", "score do Q&A", "confiança do classificador".

Essa regra vale para qualquer termo futuro que se mostrar ambíguo — não é exclusiva de categoria/score.

---

## A) Entidades de domínio/negócio

### Atendimento
Unidade de negócio que agrupa mensagens, informações coletadas (`AtendimentoInfo`) e orçamentos (`Orcamento`) de uma mesma demanda de um contato. Tem numeração sequencial por contato (`numero_atendimento_cliente`) e `status` (`ativo`/`encerrado`). `backend/models.py:429` (classe `Atendimento`, tabela `atendimentos`).

**Nome anterior:** *Negociação* — renomeado (ver `artefatos/analista_de_requisitos/analise_renomeacao_negociacao_para_atendimento.md`). **Passo A0 do plano MVP concluído em 2026-07-10**: tabela `itens_negociacao` renomeada para `itens_atendimento` (migration `2026071001`, com PK/FKs/índices/sequence); comentários/logs remanescentes em `processador.py` corrigidos; fallback morto do frontend (`?? proc.negociacao_id_ativa`) removido; texto residual do REQ-004.4 corrigido.

**⚠️ Achado durante o A0, ainda em aberto:** o banco local tem drift de DDL manual fora do Alembic bem mais extenso do que só o `itens_negociacao` — constraints com nomes com typo (`atendimentao`/`atendimentoes`) em pelo menos 5 tabelas, tabelas fantasmas vazias (`negociacoes`, `negociacao_infos`) e sequences nunca renomeadas. Causa raiz: `backend/database.py::Database._criar_tabelas()` chama `Base.metadata.create_all()` em todo startup do backend, o que cria tabelas fantasmas sempre que um `__tablename__` muda e o app recarrega antes do `alembic upgrade head` rodar. Detalhe completo e decisão pendente em `docs/plano_implementacao_mvp_continuidade_2026-07.md` §8, item 8.

**Não confundir com:** "conversa" (termo coloquial usado em REQs e no componente `ConversaInfo.jsx`, sem entidade própria — mapeia para `Atendimento`); "atendimento humano" (ver entrada própria).

### Contato
Pessoa que troca mensagens pelo WhatsApp (telefone único), podendo estar vinculada a uma `Empresa`. `backend/models.py:346`. Diferente de `Pessoa` (PF) — ver abaixo.

### Empresa / Pessoa
- **Empresa** = pessoa jurídica (CNPJ, dados da Receita Federal). `backend/models.py:207`.
- **Pessoa** = pessoa física (CPF, verificação manual). `backend/models.py:383`.
- "PJ" = Empresa; "PF" = Pessoa (`TipoDocumento` enum, `models.py:375`).
- **Assimetria de modelagem a lembrar:** `Contato.empresa_id` existe (PJ liga direto no Contato); não existe `Contato.pessoa_id` — a ligação PF é feita via `Atendimento.pessoa_id` (`models.py:440`).

### Produto / Modelo / Tipo de Produto — ✅ renomeação implementada em 2026-07-16 (decisão tomada em 2026-07-09)

Hierarquia de granularidade, nomenclatura atual do código:

| Termo (atual no código) | Termo antigo (antes da renomeação) | Definição |
|---|---|---|
| **`Produto`** / tabela `produtos` | `TipoProduto` / tabela `tipos_produto` | Categoria genérica do catálogo (ex.: "Catraca", "Relógio de Ponto"). |
| **`Modelo`** / tabela `modelos` | `Produto` / tabela `produtos` | Item específico e precificável do catálogo (código, descrição, preço), FK obrigatória para a categoria (`Produto`, coluna `produto_id`). |
| **tipo_leitor** | *(novo — não existe ainda)* | Atributo do catálogo (inclinação registrada no brainstorming: atributo do `Modelo`, não preferência solta do cliente) que descreve a tecnologia de leitura (biométrico/facial/cartão). Substitui o enum solto `modelo ∈ {biométrico, facial, cartão}` citado no plano de MVP, que colidia em nome com a entidade `Modelo`. Continua não implementado — só o rename das duas entidades foi feito. |

Migration: `backend/alembic/versions/2026071602_renomeia_produto_tipoproduto_para_modelo_produto.py`. `ItemAtendimento` tinha as duas colunas lado a lado (`tipo_produto_id`/`produto_id`) e ambas trocaram de papel: hoje `ItemAtendimento.produto_id` é a categoria e `ItemAtendimento.modelo_id` é o SKU resolvido (antes era o inverso, com `tipo_produto_id`/`produto_id`). `ItemOrcamento.produto_id` também virou `ItemOrcamento.modelo_id`.

**Regra combinada 2026-07-09:** o motor de coleta nunca grava texto livre para modelo/produto — sempre resolve para uma FK real; texto é só para exibição/descrição ao cliente.

**⚠️ Ponto pendente de análise (anotado por pedido do Beto, retomar depois):** hoje `EntidadesExtraidas.tipos_produto` (`backend/services/classificador.py:61`) é uma lista de **strings livres** extraídas por regex/LLM (ex. `"catraca"`, `"relogio_ponto"`), gravada solta em `AtendimentoInfo` (`backend/services/processador.py:1010-1011`) — **sem FK** para a tabela de categoria. Ou seja, mesmo depois da renomeação, essa extração passiva continuará desacoplada do catálogo real até ser tratada. O próprio plano de MVP já reconhece esse gap (decisão #1, §8: "Onde gravar `tipo_produto`: `AtendimentoInfo` vs `ItemAtendimento`").

**Modelo conceitual concorrente a observar:** o brainstorming de continuidade (`docs/brainstorming_continuidade_2026-07.md:219-220`) já desenhava uma classe `TipoProduto` com `atributos_obrigatorios: list[AtributoDef]` — mesmo nome que era usado no banco antes da renomeação, mas com propósito diferente (catálogo de regras de atributos obrigatórios por categoria, não uma linha simples de lookup). Ainda não reavaliado se esse conceito do brainstorming vira parte do `Produto` (categoria) atual ou de outra entidade.

### Categoria (de produto)
Campo `Modelo.categoria: Optional[str]` (`backend/models.py`, era `Produto.categoria` antes da renomeação) — string livre e opcional, usada sobretudo em metadados de chunks RAG. É **um** dos cinco sentidos de "categoria" no projeto — ver seção B para a lista completa e a convenção de nomenclatura.

### Orçamento / ItemOrcamento / ItemAtendimento
- **Orçamento** (`backend/models.py:513`) — proposta formal enviada ao cliente, com `StatusOrcamento` (em_elaboracao → pendente_aprovacao → enviado_cliente → aprovado/reprovado/expirado).
- **ItemOrcamento** (`models.py`) — linha de um orçamento já fechado, com `Modelo` (`modelo_id`) definido e preço.
- **ItemAtendimento** (`models.py`, tabela `itens_atendimento` desde o A0) — intenção de compra ainda em qualificação: começa só com a categoria (`produto_id`) e evolui para um `Modelo` real (`modelo_id`) quando o cliente escolhe.

### AtendimentoInfo — padrão chave-valor (EAV) para atributos dinâmicos

**Discussão de arquitetura em 2026-07-11**, antes de iniciar o passo A1.

**O que é:** `backend/models.py:792` (tabela `atendimento_infos`) — modelo **EAV** (Entity-Attribute-Value): `chave` (string) + `valor` (texto livre) + `pendente` (bool) + `origem` (user/inferido/sistema/atendente), com FK só para `atendimento_id` e unique constraint em `(atendimento_id, chave)`. É o destino de todo `registrar_informacao` do catálogo de conversação — cada `CAMPO-xxx` (`CAMPO-software-ponto`, `CAMPO-faixa-funcionarios` etc.) vira uma linha aqui, identificada pela chave técnica (ver mapeamento campo-catálogo ↔ chave técnica na entrada "Campo" acima).

**Decisão (2026-07-11): manter — não remover.** É o mecanismo certo para atributos esparsos e condicionais por produto/cliente (ex.: software de controle de ponto só existe para relógio de ponto; `faixa_funcionarios` só existe se não há software). A alternativa (uma coluna fixa por atributo em `Atendimento`) exigiria uma migration a cada `CAMPO-xxx` novo que a Kika criar no catálogo — quebraria exatamente a velocidade de iteração que o catálogo de conversação foi desenhado para dar a ela. Uma alternativa de JSONB solto em `Atendimento` foi considerada e descartada: perderia o `pendente`/`origem` por atributo (teria que aninhar isso dentro do JSON) sem ganhar nada que o modelo atual não resolva.

**⚠️ Limitação conhecida, registrada para o futuro:** hoje `AtendimentoInfo` só referencia `atendimento_id` — não existe FK para `ItemAtendimento`. A unique constraint em `(atendimento_id, chave)` significa **um valor por chave por atendimento**. Isso é suficiente enquanto o MVP for "um produto por atendimento" (escopo atual), mas alguns atributos (ex.: `software_controle_ponto`) são conceitualmente atributos **do item** (daquele produto específico), não do atendimento como um todo. Quando a fatia de **múltiplos produtos no mesmo atendimento** for implementada (§9 do plano de MVP), essa constraint colidiria se dois itens diferentes do mesmo atendimento precisarem de valores diferentes para a mesma chave (ex.: dois relógios de ponto de modelos diferentes, cada um com seu próprio software).

**Plano futuro (não implementar agora):** quando essa fatia chegar, adicionar uma coluna `item_atendimento_id` **opcional** (nullable) em `AtendimentoInfo`, com FK para `ItemAtendimento`:
- Info realmente do atendimento como um todo (ex.: contato para envio do orçamento, endereço de entrega) continua com `item_atendimento_id = NULL`.
- Info específica de um produto (ex.: software de controle de ponto daquele relógio específico) passa a referenciar o item.
- A unique constraint precisaria virar `(atendimento_id, item_atendimento_id, chave)` (com `item_atendimento_id` podendo ser NULL nos casos atendimento-scoped — cuidado: `UNIQUE` em Postgres trata múltiplos `NULL` como distintos entre si, então isso funciona sem gambiarra adicional).
- Este ponto está relacionado ao gap já registrado logo acima ("Produto / Modelo / Tipo de Produto" — `tipo_produto` sem FK): ambos apontam para a mesma direção arquitetural — dados de qualificação deveriam, quando fizer sentido, se ancorar no `ItemAtendimento` (o produto concreto sendo negociado), não só soltos no atendimento.

---

## B) Conceitos de conversação/fluxo

### Categoria — ⚠️ termo com 5 sentidos peer no projeto (nunca usar sozinho — ver convenção no topo)

| Sentido | Onde | Nome qualificado a usar |
|---|---|---|
| Bucket 1-4 de roteamento de mensagem (REQ-002.1) | `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md:52-61` — ainda **não implementado como campo no código**, só inferido via `Intencao` | **categoria de roteamento** |
| Categoria de um bug/problema reportado | `CategoriaReport` enum, `backend/models.py:935` (classificacao/fluxo/template/resposta_inadequada/dados/llm/outro) | **categoria de report** |
| Campo livre no catálogo de produto | `Produto.categoria` (ver seção A) | **categoria de produto** (o campo em si pode continuar chamado só `categoria`, já está no contexto de `Produto`/`Modelo`) |
| Classificação de uma diretriz do meta-projeto de agentes | `AGENTS.md`, `artefatos/<agente>/diretrizes.md` | **categoria de diretriz** |
| Classificação de um requisito formal | REQs (`artefatos/requisitos_formais/*.md`) | **categoria de requisito** |

**Estado atual (2026-07-09):** a categoria de roteamento é o único sentido ainda sem implementação — está em desenho no brainstorming do motor de fases (padrão Estado/Pergunta). Decisão em andamento: **formalizar** como valor derivado/auditável (não necessariamente um enum que decide o roteamento antecipadamente — ver nota de design na conversa/plano) em vez de deixar implícito.

### Fase (do atendimento)
Eixo ortogonal a `status` (ativo/encerrado) que descreve o estágio da jornada conversacional: Esclarecendo → Finalizando → Criando Orçamento (+ variantes de encerramento). Documentado extensivamente em `artefatos/analista_de_requisitos/catalogo_conversacao/fases/` e no plano de MVP.

**⚠️ Ainda não existe como coluna no schema** (`Atendimento` só tem `status`) — é tratado como corrente na documentação de negócio, mas é aspiracional até a Fase A do plano de MVP ser implementada. Ver também `artefatos/analista_de_requisitos/catalogo_conversacao/README.md:42` — o próprio catálogo já avisa "não confundir com `status`".

### Situação (do atendimento)
Termo usado no catálogo de conversação (`catalogo_conversacao/README.md:43`, fichas `FASE-xxx.md`) como **sinônimo de `status`** no código. O catálogo reserva "situação" para linguagem de negócio e "status" para o campo técnico — os dois convivem, não são conceitos diferentes.

### Qualificação
"Pergunta de qualificação" / "Resposta de qualificação" — termos formais do REQ-002 (§4.4 Terminologia) para a pergunta que o sistema faz para coletar um dado do orçamento, e a resposta do cliente a ela. O catálogo de conversação usa o termo equivalente **"pergunta de coleta"** (`catalogo_conversacao/README.md:45`) — mesmo conceito, nome diferente entre a camada formal (REQ) e a camada operacional (catálogo). Padronizar eventualmente, sem urgência.

### Identificação
Dois processos distintos que compartilham o substantivo:
1. **Identificação do remetente** — descobrir, a partir do telefone, quais `Contato`/`Empresa` estão associados (`StatusIdentificacao` enum: `NOVO`/`UNICO`/`MULTIPLO`/`SEM_EMPRESA`, `backend/services/identificador.py:22`).
2. **Identificação fiscal/documental** — validar CNPJ/CPF (REQ-001/REQ-015).

O contexto normalmente desambigua, mas ao escrever documentação nova, prefira "identificação do remetente" ou "identificação fiscal" explicitamente.

### Escalonamento / Atendimento humano / Modo humano
Processo de transferir a conversa para um vendedor humano (REQ-004, "Human Takeover"). Implementado como `ModoOperacao.HUMANO` (`backend/models.py:92`) — nome escolhido deliberadamente (decisão D6 em `analise_renomeacao_negociacao_para_atendimento.md`) para não colidir com a entidade `Atendimento`. **Mas o texto do REQ-004.4 ainda mistura os dois** ("estado 'em modo humano'... indicando se ela está em **atendimento humano**") — revisar texto do REQ quando for mexer nessa área.

Sinônimos usados no REQ-004: "handoff", "handover", "takeover".

### Vocabulário formal do catálogo de conversação
Definido em `artefatos/analista_de_requisitos/catalogo_conversacao/README.md:36-70` — usar exatamente estes termos ao descrever o motor de fases:
- **Efeito** — o que o sistema faz após resposta do cliente/evento: `ir_para_fase`, `encerrar_atendimento`, `criar_novo_atendimento`, `registrar_informacao`, `nao_perguntar_de_novo`, `consultar_base`, `escalar_humano`, `notificar_vendedor`, `fazer_pergunta`, `reabrir_atendimento`, `retomar_qualificacao`, `confirmar_dados`. (Mapeia diretamente para as classes `Ação` do padrão Estado/Pergunta em desenho.)
- **Disparo** — evento que faz o sistema enviar pergunta ou mudar de fase (distinto de gatilho técnico como timer/webhook).
- **Interesse** — produto/modelo/tema mencionado informalmente pelo cliente em Esclarecendo, antes de virar campo validado.
- **Informação necessária** — sinônimo formal de `CAMPO-xxx` (dado que o orçamento exige).
- **Campo** — cuidado: `CAMPO-xxx` (ficha do catálogo) nem sempre bate 1:1 com a chave técnica gravada em `AtendimentoInfo.chave` (ex.: `CAMPO-software-ponto` → chave `software_controle_ponto`). Manter uma tabela de mapeamento campo-catálogo ↔ chave técnica ao formalizar o catálogo de campos em código (Fase B do plano de MVP).

---

## C) Conceitos de IA/RAG

### Par Q&A (`ParQA`)
Par pergunta+resposta curado manualmente, com precedência sobre o RAG genérico (REQ-013: hierarquia é 1º Q&A curada, 2º RAG por documentos, 3º qualificação/fluxo, 4º escalonamento). `backend/models.py:665`, `backend/services/rag/qa_service.py:34`. Nomenclatura consistente entre modelo, serviço e REQ — sem ambiguidade.

### Chunk / Documento / Trecho
Três nomes para a mesma unidade de conteúdo indexado (linha de `documentos_conhecimento`), em estágios diferentes: **"documento"**/**"chunk"** na ingestão e no modelo de dados (`DocumentoConhecimento`, `models.py:613`); **"trecho"** na recuperação e na auditoria exibida ao processador (`DocumentoRecuperado`, `retrieval.py:34`; campo `rag_trechos` em `ProcessamentoMensagem`). Sem convenção explícita hoje de qual usar onde — sugestão: "documento" para o registro persistido, "trecho" para o resultado de busca.

### Score — ⚠️ mesma lógica de qualificação que "categoria" (ver convenção no topo)

Se aninhado a uma entidade/campo (ex.: `ParRecuperado.score`), pode ficar curto. Em documentação/conversa solta, sempre qualificar: **"score do RAG"**, **"score do Q&A"**.

**Alerta técnico (não é só nomenclatura):** dentro do próprio `ParRecuperado.score` (`backend/services/rag/qa_service.py`), o valor tem **semântica numérica diferente** conforme a camada de busca: full-text (`_buscar_por_fulltext`, linhas ~264-283) usa `rank_float` (métrica de `ts_rank`, sem teto de 1.0 garantido); busca semântica usa `1 - distância_cosseno` (sempre ~[0,1]). Isso importa para quem for calibrar `qa_score_minimo_fulltext` vs `qa_score_minimo` (REQ-014) — os dois thresholds não são diretamente comparáveis.

### Confiança (`confianca`, `confianca_nivel`)
Confiança do **classificador de intenção** (`NivelConfianca`: alta/media/baixa, thresholds `classificador_conf_alta_min`/`classificador_conf_baixa_max`, REQ-002.1A) — conceito irmão, mas **não sinônimo**, de "score do RAG/Q&A": ambos medem "o quão bem o sistema entende/recupera algo", mas em subsistemas independentes com thresholds calibrados separadamente (REQ-014).

### Intenção (`Intencao`) × categoria de roteamento
`Intencao` (`backend/services/classificador.py:32`, 15 valores) é o rótulo granular que o código de fato usa para rotear. "Categoria de roteamento" (REQ-002.1, 1-4) é um agrupamento de mais alto nível ainda não implementado — ver seção B.

---

## D) Papéis/artefatos do meta-projeto de agentes (cuidado para não confundir com termos de produto)

- **Template** — 3 sentidos que colidem: (1) template de **mensagem** ao cliente (`respostas/templates.py`, campo `template_usado`); (2) `CategoriaReport.TEMPLATE` (bug de "texto/tom da resposta"); (3) template de **documentação** do próprio catálogo (`catalogo_conversacao/templates/*.md`). Ao escrever, qualificar: "template de mensagem" vs "template de documentação".
- **Diretriz** — regra numerada (D01, D02...) do meta-projeto de agentes (`AGENTS.md`, `artefatos/<agente>/diretrizes.md`). Não confundir com "regra de negócio" do produto.
- **Artefato** — qualquer documento produzido por um agente do meta-projeto (`AGENTS.md`). Nome genérico, baixo risco real de confusão, mas onipresente.
- **`[implementador]`, `[analista]`, `[gerente]` etc.** — prefixos de papel de agente (`AGENTS.md`), citados às vezes dentro de REQs/catálogo — são papéis do processo de desenvolvimento, não entidades do sistema em produção.

---

## Pendências deste dicionário

- [ ] Fechar a análise do ponto "tipo_produto sem FK" (seção A) — retomar quando o Beto sinalizar. Continua em aberto mesmo após a renomeação de 2026-07-16: `EntidadesExtraidas.tipos_produto` continua sendo strings livres sem FK, é um assunto separado.
- [x] Atualizar todas as entradas de "Produto"/"Modelo"/"TipoProduto" — renomeação implementada em 2026-07-16 (migration `2026071602`).
- [ ] Decidir e registrar aqui o desenho final de "categoria de roteamento" quando o padrão Estado/Pergunta for formalizado.
- [ ] Validar com a Kika os termos formais do REQ-002 (§4.4) vs. os termos operacionais do catálogo de conversação (ex.: "pergunta de qualificação" vs. "pergunta de coleta").
