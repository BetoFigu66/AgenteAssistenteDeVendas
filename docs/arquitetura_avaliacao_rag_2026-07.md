# Arquitetura e Avaliação do RAG — julho/2026

Documento de levantamento técnico do subsistema de RAG (Retrieval-Augmented Generation) do Agente Assistente de Vendas, com avaliação da estrutura atual e recomendações de melhoria. Não existia até agora um documento único de arquitetura do RAG — a informação estava espalhada entre `docs/comandos_uteis.md`, `docs/dicionario_termos.md` e `docs/plano_implementacao_requisitos_formais_2026-07.md`.

## 1. Visão geral

O sistema usa **duas camadas de recuperação de conhecimento**, consultadas em ordem de prioridade antes de qualquer geração livre por LLM:

```
Mensagem do usuário
       │
       ▼
1) Q&A curado (pares_qa)   ──► hit? responde verbatim (sem LLM)
       │ miss
       ▼
2) RAG vetorial (documentos_conhecimento) ──► hit? LLM gera resposta usando os trechos
       │ miss
       ▼
3) Fallback / template genérico / escalonamento humano
```

Essa hierarquia (Q&A > RAG > fluxo/qualificação > escalonamento) é o requisito formal **REQ-013** e está documentada em `docs/dicionario_termos.md`. A implementação vive em `backend/services/rag/` (`qa_service.py`, `retrieval.py`) e é orquestrada por `ProcessadorMensagem._responder_com_rag` em `services/processador.py`.

## 2. Camada 1 — Q&A curado (`pares_qa`)

Tabela `pares_qa` (`backend/models.py`): pergunta, resposta, `contexto` (catraca, relógio_ponto, facial, controle_acesso, bastão_ronda, geral), `tags`, `embedding` (opcional/nullable — *lazy embedding*), `pergunta_tsv` (full-text, gerado via trigger), `ativo`, `aprovado`.

`QAService.buscar()` (`services/rag/qa_service.py`) busca em **duas etapas, por custo**:

1. **Full-text nativo do Postgres** (`plainto_tsquery('portuguese_unaccent', ...)` sobre `pergunta_tsv`, GIN). Se algum resultado atinge o limiar (default 0.25), retorna **sem chamar a API de embeddings**.
2. **Embedding/cosseno**, só se a etapa 1 não encontrar nada. Mesmo operador `<=>` do pgvector, score = `1 - distância`, limiar default 0.80.

Quando há hit, a resposta do par é usada **literalmente**, sem passar pelo LLM (`template_usado="qa_pair"`). Gestão via `frontend/QABasePage.jsx` + router `backend/routers/pares_qa.py`: criação de rascunho sem embedding, aprovação gera o embedding, detecção de duplicata client-side (`GET /pares-qa/similares`), estatísticas de uso dos pares mais acessados.

Estado atual: **61 pares**, todos aprovados (seed em `backend/data/seed_pares_qa.json`).

## 3. Camada 2 — RAG vetorial (`documentos_conhecimento`)

Tabela `documentos_conhecimento`: `id_externo` (chave do chunk), `id_documento_origem` (agrupa chunks do mesmo doc), `tipo` (produto, faq, categoria_produto, institucional, solucao, blog, conversa), `titulo`, `conteudo`, `metadados` (JSONB), `conteudo_hash` (para upsert idempotente na ingestão), `embedding` (vector(1536), não-nulo), `ativo`.

`RetrievalService.buscar()` (`services/rag/retrieval.py`): embedding da query → distância cosseno (`<=>`) via pgvector → `ORDER BY distância LIMIT top_k` → filtra por `score >= score_minimo` **depois** de já ter limitado a top_k no SQL. Defaults: `top_k=4`, `score_minimo=0.70`. Filtra por `tipo` (produção usa `tipo=None`, sem restrição de categoria) e `ativo=True`. Não há reranking nem filtro por produto específico (só por categoria de chunk).

Quando há hit, os trechos recuperados são passados ao LLM para compor a resposta final (não são devolvidos crus ao usuário).

Estado atual: **198 chunks** ingeridos, a partir de 80 documentos consolidados (webscraping do site Inforrel, pastas de produto, 1 conversa de WhatsApp usada como exemplo). Predominam chunks do tipo `produto` (170/198).

## 4. Ingestão de conteúdo

Pipeline em 5 scripts (`backend/scripts/base_conhecimento/`), sequencial e batch (não há ingestão incremental automática/agendada):

1. `inventariar_fontes_rag.py` — varre `docs/FoldersProdutos`, `WebScrapping/result`, `docs/ConversasDoWhatsApp`.
2. `preprocessar_conhecimento_rag.py` — normaliza para JSONL.
3. `consolidar_conhecimento_rag.py` — deduplica por similaridade textual (limiar 0.82).
4. `gerar_chunks_rag.py` — chunking (~700 tokens alvo, 900 máx, 100 de overlap).
5. `ingerir_conhecimento_rag.py` — upsert por `conteudo_hash`, gera embeddings em lote.

Provedor de embeddings: `EMBEDDING_PROVIDER=openai`, modelo `text-embedding-3-small` (1536 dims) — é o único provedor implementado (`ollama` está com `NotImplementedError` no factory).

## 5. Configuração e ajuste em runtime

Defaults em `backend/config.py`:

| Parâmetro | Default |
|---|---|
| `RAG_ENABLED` | `True` |
| `RAG_TOP_K` | `4` |
| `RAG_SCORE_MINIMO` | `0.70` |
| `QA_ENABLED` | `True` |
| `QA_TOP_K` | `3` |
| `QA_SCORE_MINIMO` | `0.80` |
| `QA_SCORE_MINIMO_FULLTEXT` | `0.25` |

Todos ajustáveis **sem restart** via `PATCH /api/config/rag` (persistido em `parametros` + histórico em `historico_configuracao`, com validação atômica de todos os campos antes de aplicar qualquer um) e via `PATCH /api/parametros/{nome}` genérico. Há também `POST /api/config/rag/reset` e `GET /api/config/historico`.

## 6. Auditoria

Cada resposta gerada grava em `ProcessamentoMensagem`: `rag_utilizada` (bool), `rag_score_maximo`, `rag_trechos` (JSONB com id, tipo, título/pergunta, score, distância, url por trecho — incluindo trechos do tipo `qa_pair`). Exposto na UI em `ProcessamentoDetalhes.jsx` ("Raciocínio do Cérebro"). A query `GET /api/pares-qa/estatisticas-uso` explora esse mesmo campo para achar os pares mais usados nos últimos N dias.

## 7. Avaliação — pontos fortes

- **Hierarquia Q&A → RAG → fallback bem implementada e testada** (`test_processador_responder_com_rag.py`), com economia de custo real: full-text antes de embedding no QA, e resposta verbatim sem LLM quando há par curado — reduz tokens de LLM e risco de alucinação nas perguntas mais frequentes.
- **Configuração 100% runtime-tunável com histórico e atomicidade** — permite calibrar thresholds sem deploy, e há trilha de auditoria de quem mudou o quê.
- **Auditoria completa por mensagem** (`rag_trechos`, `rag_score_maximo`) — essencial para debugar "por que o bot respondeu X", já citado como prioridade no CLAUDE.md do projeto.
- **Lazy embedding em `pares_qa`** — evita gastar chamadas de embedding em rascunhos não aprovados.
- **Interface de curadoria (`QABasePage`)** com detecção de duplicata antes de criar par novo, e painel de pares mais usados — reduz duplicação orgânica da base.
- **Cobertura de testes automatizados** razoável no caminho principal (retrieval, QA router, decisão de resposta no processador).
- **Índices vetoriais HNSW** já criados tanto em `documentos_conhecimento` quanto em `pares_qa` (migrations recentes), o que evita scan sequencial conforme a base cresce.

## 8. Avaliação — pontos fracos e riscos

1. **Sem reranking** — a ordenação final depende só de similaridade de embedding bruta. Para uma base pequena (198 chunks) isso é aceitável, mas à medida que o catálogo crescer, top-k=4 sem reranking tende a trazer chunks redundantes do mesmo documento em vez de diversidade de fontes.
2. **Corte de score aplicado depois do `LIMIT top_k`, não antes** — se os 4 documentos mais próximos tiverem score baixo mas ainda acima do threshold, você nunca vê um 5º documento potencialmente mais relevante para um aspecto diferente da pergunta; e se nenhum dos 4 bater o threshold, a busca falha mesmo que exista um bom candidato fora do top_k (pouco provável com top_k pequeno, mas é uma limitação estrutural do desenho atual, que só busca `buscar_candidatos()` sem esse corte para fins de diagnóstico, não em produção).
3. **Sem filtro por produto específico, só por categoria (`tipo`)** — numa base com múltiplas linhas de produto (catraca, ponto, facial), a busca vetorial pode misturar contexto de produtos diferentes na mesma resposta se as perguntas do usuário forem genéricas. Não há uso do produto já identificado na conversa (se o `Atendimento` já sabe que é sobre catraca X) para restringir a busca.
4. **Ingestão é 100% batch/manual, sem processo incremental** — qualquer atualização no site ou nos PDFs de produto exige rodar manualmente os 5 scripts. Não há job agendado nem trigger de "conteúdo mudou, reingerir". Para um catálogo que muda com frequência (preços, specs), isso é risco de desatualização silenciosa da base.
5. **Base de conhecimento ainda pequena e concentrada** — 198 chunks, 80% do tipo `produto`, majoritariamente vindos de webscraping (62 de 80 documentos). Pouca cobertura de FAQ estruturado, institucional ou de objeções comerciais reais (só 1 conversa de WhatsApp usada como fonte). Isso limita o RAG a responder bem sobre especificações de produto, mas pouco sobre nuances de negociação/objeção — que hoje dependem mais dos 61 pares de Q&A curados manualmente.
6. **`QAService` sem testes unitários dedicados** (existe para `RetrievalService`, mas não equivalente para o QA) — a lógica de duas camadas (full-text → embedding) é a parte mais particular do sistema e a que mais se beneficiaria de testes diretos de limiar/precedência.
7. **Zona cinza de "pedir desambiguação" carregada mas não usada** — os parâmetros `qa_embedding_desambigua_min`/`qa_fulltext_desambigua_min` já existem no `ParametroService`, mas o código de `QAService.buscar()` ainda não implementa a lógica de "quase bateu, pergunta para confirmar" — é um meio-caminho andado que vale terminar ou remover a configuração morta.
8. **Nenhuma métrica de qualidade de recuperação além do score bruto** — não há avaliação amostral (ex.: golden set de perguntas com resposta esperada) para medir precisão/recall do RAG e do QA ao longo do tempo, nem alerta quando `rag_utilizada=False` com frequência anormal (sinal de gap de conteúdo).
9. **Plano de implementação desatualizado em relação ao código** — `docs/plano_implementacao_requisitos_formais_2026-07.md` ainda lista como pendentes itens da Fase 3/7/9 que já foram entregues (índice vetorial, exposição de `rag_trechos` na UI, config unificado `qa_enabled`). Vale uma passada de atualização do plano para não gerar retrabalho ou decisões baseadas em informação velha.

## 9. Recomendações priorizadas

**Curto prazo (baixo esforço, alto retorno):**
- Atualizar `docs/plano_implementacao_requisitos_formais_2026-07.md` marcando os itens já entregues (evita retrabalho e decisões baseadas em premissas erradas).
- Adicionar testes unitários para `QAService` equivalentes aos de `RetrievalService`, cobrindo a precedência full-text→embedding e os limiares.
- Decidir e resolver a "zona cinza" de desambiguação: implementar a pergunta de confirmação ou remover os parâmetros não usados.

**Médio prazo:**
- Restringir a busca vetorial por produto/categoria já identificado na conversa (usar o `Atendimento`/entidades extraídas pelo classificador para filtrar `tipo`/produto), reduzindo mistura de contexto entre linhas de produto.
- Expandir a base de conhecimento além de webscraping: incorporar mais conversas reais de WhatsApp (anonimizadas) e FAQs estruturados, para melhorar cobertura de objeções e perguntas comerciais, não só especificações técnicas.
- Criar um pequeno "golden set" de perguntas reais com resposta esperada, rodado periodicamente (script, não precisa ser CI), para medir precisão/recall do RAG e do QA e detectar regressão de qualidade quando thresholds mudam.

**Longo prazo:**
- Automatizar a reingestão (job agendado ou trigger) quando o conteúdo fonte (site, PDFs) mudar, em vez de depender de execução manual dos 5 scripts.
- Avaliar reranking leve (ex.: reordenar top-N por um segundo critério, como recência do documento ou correspondência de categoria) quando a base crescer além da escala atual (~200 chunks), já que reranking traz pouco ganho hoje mas passa a importar com um catálogo maior.
- Monitorar taxa de `rag_utilizada=False`/escalonamento por falta de base como sinal proativo de gap de conteúdo, alimentando o backlog de ingestão.
