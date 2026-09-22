# Ideia: módulo de ajuda/documentação contextual (reaproveitável entre sistemas)

Data do brainstorming: 2026-07-16

## Origem

A Kika trabalhou numa empresa onde havia necessidade de "documentação" do sistema.
Em vez de manuais de usuário tradicionais, a ideia melhor seria um **help integrado
ao sistema, sensível ao contexto de tela** (o usuário pergunta ou recebe sugestões
relevantes pra onde ele está, não pra um manual genérico). Essa empresa pode chamar
a Kika de volta a qualquer momento pra esse tipo de trabalho.

A pergunta que motivou este documento: dá pra construir isso como um **módulo
independente**, integrado a este sistema (AgenteAssistenteDeVendas) mas desenhado
de forma que possa ser **reaproveitado em outros sistemas**, mudando só configuração
(contexto, perguntas, respostas)?

## Resposta curta

Sim, é tecnicamente viável — e boa parte da engenharia já existe neste projeto.
O risco não é de viabilidade, é de **generalização prematura**: abstrair "config
multi-sistema" antes de ter um segundo sistema real usando isso tende a gerar um
design errado, porque as suposições sobre o que precisa ser parametrizável são
chutes. Recomendação: construir primeiro para este sistema, mas isolado como módulo
próprio (namespace/tabelas/rotas dedicadas), pra que extrair depois seja
"copiar e desconfigurar", não reescrever.

## Por que a base técnica já existe aqui

Este projeto já resolve, para o domínio de vendas, exatamente o mesmo problema de
fundo que um "help contextual" precisa resolver: dado uma pergunta em linguagem
natural, encontrar a melhor resposta entre conteúdo curado e conteúdo geral.

- **`pares_qa`** (`backend/routers/pares_qa.py`, `services/rag/qa_service.py`):
  camada de perguntas/respostas curadas, com matching por similaridade antes de
  cair pro RAG genérico. Isso é literalmente o mecanismo de "FAQ" que um help
  contextual quer.
- **`documentos_conhecimento`** (pgvector) + `services/rag/retrieval.py`: busca
  vetorial sobre documentos — serviria para "documentação completa" quando não
  há um par Q&A específico pra pergunta.
- **`services/llm/factory.py`** / **`services/embeddings/factory.py`**: providers
  já são plugáveis (Groq/OpenAI hoje) — um módulo de ajuda reaproveitaria a mesma
  fábrica, sem acoplar a um provider específico.
- **`ParametrosPage`/`QABasePage`** no frontend: já existe o padrão de tela admin
  pra curar conteúdo (CRUD de pares Q&A) — o mesmo padrão serviria pra gerenciar
  conteúdo de ajuda por contexto.

Ou seja: o "motor de resposta" não precisa ser inventado. O que falta é a
**dimensão de contexto** (em qual tela/feature o usuário está agora) e um
**canal de UI genérico** (widget de ajuda) que qualquer tela possa embutir.

## Proposta de arquitetura (para este sistema, isolada como módulo)

### Backend

Novo pacote isolado, ex. `backend/services/ajuda/` + `backend/routers/ajuda.py`,
sem depender de nada do domínio de vendas (Atendimento, Empresa, etc.) — só reaproveita
os serviços genéricos de RAG/embeddings/LLM.

Tabelas novas (nomes ilustrativos):

- `ajuda_contextos`: catálogo dos "lugares" que podem pedir ajuda — chave (ex.
  `acompanhamento.lista`, `chat.aprovacao_mensagem`, `parametros.rag`), rótulo
  amigável, descrição. É o equivalente do que `catalogo_conversacao/FASE-xxx.md`
  é pro motor de fases: um catálogo de referência, não código.
- `ajuda_conteudos`: pares pergunta/resposta (ou "dica" sem pergunta, tipo tooltip
  proativo) vinculados a um `contexto_id` (FK, nullable = ajuda geral/global) +
  campos de manutenção (autor, ativo, prioridade).
- Reaproveita `documentos_conhecimento` (ou uma tabela irmã com a mesma estrutura,
  ex. `ajuda_documentos`) pra conteúdo mais longo tipo "como funciona X" que não
  cabe num par pergunta/resposta curto.

Endpoint principal: `POST /api/ajuda/perguntar` recebendo `{contexto, pergunta}`.
Pipeline de resposta (mesma lógica em camadas do processador de vendas):

1. Match contra `ajuda_conteudos` do `contexto` informado (score alto → resposta direta).
2. Se não achar, RAG sobre `ajuda_documentos` filtrado pelo `contexto` (ou sem filtro,
   se o contexto não tiver conteúdo próprio).
3. Fallback: resposta genérica ("não encontrei isso, quer abrir um chamado?").

Endpoint secundário (modo proativo, sem pergunta): `GET /api/ajuda/sugestoes?contexto=X`
retorna as N dicas mais relevantes pra tela atual, pra exibir sem o usuário precisar
digitar nada — isso é o diferencial real vs. um FAQ estático (o help "sabe" onde
o usuário está).

### Frontend

Um componente reutilizável, ex. `<AjudaContextual contexto="acompanhamento.lista" />`,
plugado uma vez em cada tela/seção que quiser oferecer ajuda — um botão flutuante
(?) que abre um painel lateral. O componente só precisa saber a string de contexto;
toda a lógica de busca fica no backend. Isso mantém o acoplamento tela→ajuda em
uma linha por tela.

Naming do contexto: usar convenção hierárquica (`tela.subarea`, ex.
`acompanhamento.lista`, `acompanhamento.detalhe.aprovacao`) — dá pra ter conteúdo
específico ou herdar do nível mais genérico se não houver match específico
(mesma ideia de fallback em cascata que o RAG já usa pra score mínimo).

### Autoria de conteúdo (pensando na Kika)

Se quem vai manter o conteúdo é alguém como a Kika — perfil de analista/documentação,
não necessariamente dev —, a tela de gestão precisa ser tão simples quanto
`QABasePage` hoje: formulário de contexto + pergunta + resposta, sem precisar
mexer em código ou banco diretamente. Vale considerar também importação via
planilha/CSV pra carga inicial em massa (comparável ao que já foi cogitado nas
notas de RAG por pastas de produto, ver `planejamento_rag_folders_produtos.md`).

## O que precisa ficar genérico desde já vs. o que pode esperar

**Genérico desde já (baixo custo, evita retrabalho):**
- Módulo em namespace próprio (`services/ajuda/`, `routers/ajuda.py`, prefixo de
  tabela `ajuda_*`) sem imports do domínio de vendas.
- Motor de resposta (curado → RAG → fallback) parametrizado por `contexto`, não
  por regra de negócio do Inforrel.
- Componente de frontend que só recebe uma string de contexto como prop.

**Pode esperar um segundo sistema real para desenhar (evitar chute):**
- Empacotar como biblioteca/pacote instalável separado do monorepo.
- Multi-tenant de verdade (vários "sistemas host" no mesmo banco/API) — mesma
  cautela já registrada em memória sobre customização multi-tenant do produto
  principal: não vale generalizar sem um segundo cliente real puxando os requisitos.
- Formato de "config" externa (YAML/JSON de contextos) — enquanto só há um
  sistema consumidor, tabela no banco + tela admin já resolve; formalizar um
  schema de config exportável só quando houver de fato um segundo sistema pra
  importar isso.

## Riscos / trade-offs

- **Generalização prematura** (o risco principal, já mencionado): construir a
  "camada de config multi-sistema" agora, sem um segundo caso de uso real, tende
  a errar o que precisa ser parametrizável.
- **Conteúdo desatualizado**: ajuda contextual atrelada a telas específicas apodrece
  rápido se a tela mudar e ninguém atualizar o conteúdo — precisa de dono definido
  (aqui entra o papel da Kika) e idealmente um alerta/checklist de "toda mudança de
  tela relevante revisa a ajuda associada".
- **Custo/latência de LLM**: se o "assistente" for conversacional (LLM respondendo
  livre) em vez de só retrieval de conteúdo curado, isso adiciona custo e latência
  por interação — para ajuda contextual, muitas vezes um FAQ bem curado + busca
  simples já resolve 80% dos casos sem precisar de LLM generativo, só embeddings
  pra matching. Vale decidir isso cedo: "assistente que responde livremente" vs.
  "motor de busca contextual sobre conteúdo curado" são escopos bem diferentes.
- **Confiabilidade da detecção de contexto**: se o contexto for inferido automaticamente
  (ex. pela rota atual) em vez de declarado explicitamente por cada tela, corre risco
  de ficar impreciso conforme o frontend evolui. Mais simples e robusto: cada tela
  declara explicitamente sua string de contexto (como no exemplo do componente acima).

## Perguntas em aberto (pra alinhar antes de implementar)

1. O objetivo é um **assistente conversacional** (o usuário conversa livremente
   e o LLM responde) ou uma **busca contextual sobre conteúdo curado** (mais
   parecido com FAQ inteligente)? Isso muda bastante o escopo e o custo.
2. Quem vai efetivamente manter o conteúdo ao longo do tempo — a Kika, se voltar?
   Isso define o quanto a tela de autoria precisa ser "à prova de não-dev".
3. Faz sentido validar a ideia primeiro com um MVP pequeno (2-3 telas deste próprio
   sistema com ajuda contextual) antes de pensar em reaproveitamento pra outro
   sistema?

## Próximos passos sugeridos (se decidir avançar)

1. Escolher 2-3 telas deste sistema como piloto (candidatas óbvias: `AcompanhamentoPage`,
   fluxo de aprovação/rejeição de mensagem em `ChatArea`, `ParametrosPage`).
2. Modelar `ajuda_contextos` / `ajuda_conteudos` via Alembic, isolado do domínio de vendas.
3. Endpoint `POST /api/ajuda/perguntar` reaproveitando `services/rag`/`services/llm`
   existentes (sem tocar no pipeline de vendas).
4. Componente `<AjudaContextual>` + 1 tela admin simples pra cadastrar conteúdo.
5. Só depois disso funcionando, revisitar a questão de reaproveitar em outro sistema.
