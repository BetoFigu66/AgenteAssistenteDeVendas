# Plano RAG Produtos v1

<!-- CLASSIFICACAO: HISTORICO -->

**Data:** 2026-04-30  
**Agente:** Arquiteto de Sistemas  
**Status:** Executado (rótulo "Proposta para discussão" desatualizado — o plano já está implementado e em uso; arquivo está em `planos_executados/`, corrigido em 2026-07-17)

## 1. Resumo do pedido

Temos informacoes iniciais para comecar a configurar a RAG do assistente inteligente de vendas da Inforrel. A base inicial sera composta por:

- `docs/FoldersProdutos`: textos extraidos de PDFs de folders de produtos baixados do site.
- `WebScrapping/result`: textos extraidos por web scraping do mesmo site, incluindo paginas de produtos, categorias, blog, servicos e institucionais.
- `docs/ConversasDoWhatsApp`: exemplos reais de conversas de vendas via WhatsApp.

As informacoes de produtos sao consideradas completas para esta primeira etapa. A equipe pretende obter mais exemplos de conversas para melhorar o comportamento do agente. Os arquivos dos tres diretorios estao em formato raw; se for necessario melhorar a formatacao antes da ingestao no RAG, criaremos scripts de pre-processamento. Tambem ha risco de duplicidade entre `docs/FoldersProdutos` e `WebScrapping/result`, pois ambos vieram do mesmo site/base publica.

## 2. Objetivo

Disponibilizar uma RAG inicial para que o agente inteligente de vendas responda perguntas de clientes sobre produtos, aplicacoes, caracteristicas, comparacoes e duvidas frequentes, sem inventar informacoes e respeitando as regras do projeto:

- responder em portugues brasileiro, com tom cordial e profissional;
- nao prometer prazo de entrega;
- nao inventar preco, desconto ou informacao tecnica ausente;
- orientar validacao tecnica quando envolver compatibilidade com sistemas de terceiros;
- escalar para humano quando a resposta nao for segura ou quando o cliente pedir atendimento humano.

## 3. Decisao tecnica de base

Usar a decisao ja registrada no ADR-004 da arquitetura POC:

- Postgres existente com `pgvector`;
- tabela unica `documentos_conhecimento`;
- embeddings OpenAI `text-embedding-3-small`;
- provider de embedding separado do provider de chat;
- LLM de chat atual mantida, inicialmente Groq;
- retrieval seletivo apenas em intencoes ligadas a produto, preco e fora de contexto.

Este plano detalha como sair dos arquivos raw atuais ate a integracao funcional com o fluxo de resposta.

## 4. Escopo da primeira versao

Entram na v1:

- Conteudo de produtos dos folders e do scraping.
- Perguntas frequentes de paginas de produtos, quando existirem no scraping.
- Conversas do WhatsApp como apoio para estilo de atendimento, dataset de avaliacao e extracao curada de perguntas e respostas.
- Metadados minimos por trecho: origem, arquivo, URL quando houver, titulo, tipo, categoria, produto provavel e hash de conteudo.
- Um pipeline idempotente de pre-processamento e ingestao.
- Busca semantica por trechos relevantes.
- Injecao controlada dos trechos no prompt de resposta.
- Exibicao, no painel interno, dos trechos da RAG usados na resposta.
- Testes manuais e automatizados com perguntas comuns de cliente.

Ficam fora da v1:

- Aprendizado automatico a partir de conversas novas.
- Treinamento/fine-tuning de modelo.
- Uso direto das conversas do WhatsApp como fonte factual de produto.
- Respostas automaticas sobre preco fechado, prazo de entrega ou condicoes comerciais nao documentadas.
- Cadastro pela interface de acompanhamento de novas perguntas e respostas humanas para alimentar a base de conhecimento; fica como evolucao planejada.

## 5. Papel de cada fonte

### 5.1 `docs/FoldersProdutos`

Fonte primaria para conhecimento de produto vindo de folders. Deve ser usada principalmente para caracteristicas, aplicacoes, beneficios e especificacoes descritas nos materiais oficiais.

Tratamento esperado:

- ignorar PDFs na ingestao inicial se o TXT correspondente ja existir;
- manter referencia ao PDF original no metadata quando possivel;
- dividir arquivos grandes em secoes menores;
- normalizar titulos e nomes de produtos.

### 5.2 `WebScrapping/result`

Fonte complementar e possivelmente mais detalhada. Inclui paginas de produto, categorias e paginas institucionais.

Tratamento esperado:

- priorizar arquivos `produtos_*.txt` e `categoria-de-produto_*.txt`;
- remover menus, cabecalhos repetidos, rodapes, contatos, navegacao e blocos genericos;
- aproveitar URLs existentes na primeira linha como fonte;
- deduplicar contra os folders.

### 5.3 `docs/ConversasDoWhatsApp`

Fonte de comportamento comercial e de perguntas reais, nao fonte factual primaria de produto.

Uso recomendado na v1:

- extrair exemplos de perguntas reais;
- montar dataset de avaliacao;
- identificar linguagem do cliente, objeções e pontos de decisao;
- apoiar prompts, tom de atendimento e regras de escalonamento;
- extrair pares pergunta/resposta quando houver resposta humana boa e reutilizavel;
- transformar esses pares em base curada de FAQ, depois de anonimizar e revisar.

Cuidados:

- nao indexar conversas cruas no RAG de produto nesta etapa;
- anonimizar antes de qualquer uso mais amplo;
- nao usar dados pessoais, enderecos, telefones ou nomes reais como contexto de resposta.
- separar claramente conhecimento factual de produto, FAQ curada e exemplos de estilo.

Evolucao desejada:

- permitir que, pela interface de acompanhamento, uma resposta humana dada a uma pergunta do cliente seja marcada como reutilizavel;
- salvar essa pergunta/resposta como candidata a FAQ;
- exigir revisao/aprovacao antes de entrar na base ativa da RAG.

## 6. Pipeline proposto

### Passo 1: Inventario das fontes

Criar um inventario automatico com:

- caminho do arquivo;
- tamanho;
- tipo de fonte: folder, scraping, conversa;
- URL extraida, quando existir;
- hash do conteudo bruto;
- data de processamento.

Saida sugerida: `backend/data/rag/inventario_fontes.json`.

Resultado em 2026-04-30:

- Script criado: `backend/scripts/inventariar_fontes_rag.py`.
- Inventario gerado: `backend/data/rag/inventario_fontes.json`.
- Total encontrado: 95 arquivos.
- Por fonte: 32 em `docs/FoldersProdutos`, 62 em `WebScrapping/result` e 1 em `docs/ConversasDoWhatsApp`.
- Por extensao: 82 arquivos `.txt` e 13 arquivos `.pdf`.
- Arquivos com URL extraida: 71.

### Passo 2: Pre-processamento dos arquivos raw

Criar scripts para transformar raw text em documentos limpos, antes da ingestao principal.

Regras iniciais:

- normalizar encoding para UTF-8;
- remover linhas vazias excessivas;
- remover menus e blocos repetidos do scraping;
- preservar titulos, subtitulos e perguntas frequentes;
- separar anexos e mensagens de sistema em conversas WhatsApp;
- gerar arquivo intermediario em JSONL.

Saida sugerida: `backend/data/rag/documentos_normalizados.jsonl`.

Resultado em 2026-04-30:

- Script criado: `backend/scripts/preprocessar_conhecimento_rag.py`.
- Documento normalizado gerado: `backend/data/rag/documentos_normalizados.jsonl`.
- Resumo gerado: `backend/data/rag/preprocessamento_resumo.json`.
- Total de fontes lidas do inventario: 95.
- Total de documentos normalizados: 82.
- PDFs ignorados nesta etapa: 13, pois a v1 usa os TXT ja extraidos.
- Por tipo de documento: 54 produtos, 6 indices de produto, 6 categorias de produto, 4 solucoes, 4 blogs, 7 institucionais e 1 conversa.
- Conversa do WhatsApp normalizada com telefone, endereco e anexos mascarados.

Formato sugerido por registro:

```json
{
  "id_fonte": "hash-ou-slug",
  "tipo": "produto",
  "titulo": "Catraca Biometrica Fit TOPDATA",
  "conteudo": "Texto limpo...",
  "metadata": {
    "origem": "webscraping",
    "arquivo": "WebScrapping/result/produtos_catraca-biometrica-fit-topdata.txt",
    "url": "https://inforrel.com.br/produtos/catraca-biometrica-fit-topdata/",
    "categoria": "Controle de Acessos",
    "produto_slug": "catraca-biometrica-fit-topdata"
  }
}
```

### Passo 3: Deduplicacao e consolidacao

Deduplicar em dois niveis:

- duplicidade exata: mesmo hash de conteudo normalizado;
- duplicidade aproximada: trechos muito parecidos entre folder e scraping.

Regra de precedencia proposta:

1. pagina de produto do scraping, quando tiver URL e FAQ;
2. folder TXT, quando trouxer especificacoes mais claras;
3. categoria ou pagina institucional apenas como complemento.

Em caso de conflito entre fontes, nao tentar resolver automaticamente na v1: marcar como `precisa_revisao=true` no metadata.

Resultado em 2026-04-30:

- Script criado: `backend/scripts/consolidar_conhecimento_rag.py`.
- Documento consolidado gerado: `backend/data/rag/documentos_consolidados.jsonl`.
- Resumo gerado: `backend/data/rag/consolidacao_resumo.json`.
- Entrada: 82 documentos normalizados.
- Saida: 80 documentos consolidados.
- Duplicatas exatas removidas: 2.
- Grupo de duplicata exata: 1.
- Pares similares mantidos para revisao: 1.
- O par similar identificado envolve dois folders de catraca de acesso/FIT; os dois foram mantidos e marcados como `precisa_revisao=true`, sem resolucao automatica.

### Passo 4: Chunking

Quebrar documentos em trechos pequenos e semanticamente coerentes.

Um chunk e um pedaco menor de um documento usado como unidade de busca da RAG. Em vez de mandar um folder inteiro para o modelo, o sistema divide o texto em blocos menores, gera um embedding para cada bloco e, quando o cliente pergunta algo, recupera apenas os blocos mais parecidos com a pergunta.

Exemplo simples:

- documento original: uma pagina inteira sobre "Catraca Biometrica Fit TOPDATA";
- chunk 1: descricao geral e aplicacao;
- chunk 2: formas de identificacao, biometria, QR Code, RFID e senha;
- chunk 3: dispositivo anti-panico;
- chunk 4: FAQ sobre funcionamento e tempo de liberacao.

Isso melhora a precisao porque a resposta usa o trecho certo, nao um texto enorme cheio de assuntos misturados.

Configuracao inicial sugerida:

- 500 a 900 tokens por chunk;
- overlap pequeno, em torno de 80 a 120 tokens;
- manter FAQ como chunks independentes por pergunta/resposta;
- manter metadados de produto/categoria em todos os chunks;
- nao misturar produtos diferentes no mesmo chunk.

Resultado em 2026-04-30:

- Script criado: `backend/scripts/gerar_chunks_rag.py`.
- Chunks gerados: `backend/data/rag/chunks_conhecimento.jsonl`.
- Resumo gerado: `backend/data/rag/chunking_resumo.json`.
- Entrada: 80 documentos consolidados.
- Saida: 198 chunks.
- Configuracao usada: alvo de 700 tokens, maximo de 900 tokens e overlap de 100 tokens.
- Chunks por tipo: 80 de conteudo geral e 118 de FAQ.
- Tamanho aproximado: minimo de 3 tokens, maximo de 758 tokens e media de 121,8 tokens.
- O par de documentos marcado como `precisa_revisao=true` no Passo 3 teve esse metadata preservado nos chunks.

### Passo 5: Banco e migrations

Implementar migration Alembic:

- habilitar extensao `vector`;
- criar enum/tipo controlado para `tipo` se fizer sentido;
- criar tabela `documentos_conhecimento`;
- criar indice vetorial;
- criar indices auxiliares por `tipo`, `titulo` e campos relevantes de `metadata`.

Campos minimos:

- `id`;
- `tipo`;
- `titulo`;
- `conteudo`;
- `metadata` JSONB;
- `conteudo_hash`;
- `embedding vector(1536)`;
- `ativo`;
- `created_at`;
- `updated_at`.

Resultado em 2026-04-30:

- `docker-compose.yml` atualizado para usar `pgvector/pgvector:pg16` no serviço `postgres`.
- Modelo SQLAlchemy criado: `DocumentoConhecimento` em `backend/models.py`.
- Tipo SQLAlchemy auxiliar criado: `Vector(1536)`.
- Migration criada: `backend/alembic/versions/2026043001_cria_documentos_conhecimento_pgvector.py`.
- Migration aplicada com sucesso: revision atual `2026043001 (head)`.
- Extensao confirmada no banco: `vector`.
- Tabela criada: `documentos_conhecimento`.
- Coluna vetorial confirmada: `embedding vector(1536)`.
- JSONB confirmado: coluna `metadata jsonb`.
- Indices criados: `ivfflat` com `vector_cosine_ops`, GIN em `metadata`, indices por `tipo/ativo`, `titulo`, `conteudo_hash`, `id_fonte` e `id_documento_origem`.
- Constraint unica criada: `id_externo`.

### Passo 6: Provider de embeddings

Criar modulo `backend/services/embeddings/` com:

- `EmbeddingProvider` abstrato;
- `OpenAIEmbeddingProvider`;
- factory baseada em configuracao;
- variaveis `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_API_KEY`.

Adicionar dependencias necessarias em `backend/requirements.txt`.

Resultado em 2026-04-30:

- Modulo criado: `backend/services/embeddings/`.
- Interface abstrata `EmbeddingProvider` com `EmbeddingResponse` em `backend/services/embeddings/base.py`. Contrato principal: `embed(textos: list[str]) -> EmbeddingResponse` e atalho `embed_um(texto)`; propriedades `nome`, `modelo` e `dimensoes`.
- Implementacao `OpenAIEmbeddingProvider` em `backend/services/embeddings/openai_provider.py` usando `AsyncOpenAI`, com ordenacao dos vetores pelo `index` da resposta, sanitizacao de texto vazio e ajuste de `dimensoes` caso o modelo retorne tamanho diferente do esperado.
- Factory `get_embedding_provider()` em `backend/services/embeddings/factory.py`, com cache singleton e suporte inicial a `openai` (placeholder para `ollama`).
- `backend/config.py` estendido com `EMBEDDING_PROVIDER` (default `openai`), `EMBEDDING_MODEL` (default `text-embedding-3-small`) e `EMBEDDING_API_KEY`.
- `backend/.env.example` atualizado com a nova secao `Embeddings / RAG`.
- `backend/requirements.txt` passou a incluir `openai==1.55.3`.
- Dimensao padrao do `text-embedding-3-small` permanece 1536, alinhada com a coluna `embedding vector(1536)` criada no Passo 5.

### Passo 7: Script de ingestao

Criar script idempotente, por exemplo:

- `backend/scripts/preprocessar_conhecimento.py`;
- `backend/scripts/ingerir_conhecimento.py`.

Comportamento esperado:

- ler JSONL normalizado;
- gerar chunks;
- calcular hash por chunk;
- pular chunks ja ingeridos;
- atualizar chunks quando o hash mudar;
- gerar embeddings em lote;
- registrar estatisticas finais: documentos lidos, chunks gerados, chunks novos, chunks atualizados, chunks ignorados.

Resultado em 2026-04-30:

- Observacao: o pre-processamento ja foi feito nos Passos 2 a 4 por `backend/scripts/preprocessar_conhecimento_rag.py`, `consolidar_conhecimento_rag.py` e `gerar_chunks_rag.py`. O Passo 7 se resumiu ao script idempotente de ingestao.
- Script criado: `backend/scripts/ingerir_conhecimento_rag.py`.
- Entrada padrao: `backend/data/rag/chunks_conhecimento.jsonl`. Resumo gerado em `backend/data/rag/ingestao_resumo.json`.
- Chave de idempotencia: `id_chunk` mapeado para `documentos_conhecimento.id_externo`.
- Decisao por chunk: insere se novo, atualiza se `conteudo_hash` mudou ou se estava inativo, ignora se hash bate e registro esta ativo.
- Chunks presentes no banco mas ausentes da entrada sao marcados como `ativo=False` por padrao (soft-delete); desligavel via `--nao-desativar-removidos`.
- Embeddings gerados apenas para chunks novos ou atualizados, via `get_embedding_provider()`, em lotes de `--lote` (padrao 64), registrando `tokens_input`, `lotes_embeddings` e `embeddings_gerados`.
- Suporta `--dry-run` (nao chama o provider nem grava no banco) para validar o plano de ingestao.
- Resumo inclui: `total_lidos`, `duplicados_na_entrada`, `novos`, `atualizados`, `ignorados`, `desativados`, `reativados`, `embeddings_gerados`, `lotes_embeddings`, `tokens_input`, `provider`, `modelo`, `dimensoes`, `duracao_segundos`, `inicio`, `fim`.
- Ajuste auxiliar: `backend/models.py` ganhou `bind_processor` e `result_processor` no tipo `Vector`, convertendo `list[float]` no formato textual aceito pelo pgvector (`"[v1,v2,...]"`) e de volta ao ler; habilita SQLAlchemy a persistir e ler `embedding` transparentemente.

### Passo 8: RetrievalService

Criar `backend/services/rag/retrieval.py` com metodo principal:

```python
buscar(query: str, top_k: int = 4, tipo: str | None = "produto") -> list[DocumentoRecuperado]
```

Responsabilidades:

- gerar embedding da pergunta;
- consultar `documentos_conhecimento` por similaridade;
- aplicar filtros por tipo e ativo;
- retornar conteudo, score e metadata;
- impor limiar minimo de confianca;
- registrar logs para debug.

Resultado em 2026-04-30:

- Modulo criado: `backend/services/rag/`.
- `DocumentoRecuperado` (dataclass) e `RetrievalService` em `backend/services/rag/retrieval.py`. Campos expostos: `id`, `id_externo`, `id_documento_origem`, `tipo`, `titulo`, `conteudo`, `score`, `distancia`, `metadados`.
- Metodo principal: `async buscar(query, top_k=None, tipo="produto", tipos=None, score_minimo=None, apenas_ativos=True) -> list[DocumentoRecuperado]`. Passar `tipo=None` desliga o filtro por tipo; `tipos` (lista) tem precedencia sobre `tipo`.
- Geracao de embedding da pergunta via `EmbeddingProvider.embed_um()`.
- Consulta usa operador de distancia cosseno do pgvector (`<=>`) via `DocumentoConhecimento.embedding.op("<=>")(bindparam)`, com `bindparam` tipado como `Vector(dim)` reaproveitando o `bind_processor` do modelo.
- Filtros aplicados: `ativo=True` (por padrao), `tipo` unico ou `tipos in (...)`.
- Score calculado como `1 - distancia`; limiar minimo aplicado apos o `ORDER BY distancia` + `LIMIT top_k`.
- Logs em nivel DEBUG com resumo da chamada (quantidades, score minimo efetivo) e top 3 melhores titulos.
- Factory `get_retrieval_service()` com `lru_cache(maxsize=1)`, criando o `Engine` SQLAlchemy a partir de `settings.DATABASE_URL` e consumindo o singleton de embeddings.
- Configuracoes adicionadas em `backend/config.py` e `backend/.env.example`: `RAG_ENABLED` (true), `RAG_TOP_K` (4), `RAG_SCORE_MINIMO` (0.70), `RAG_SUGERIR_PRODUTOS` (false) e `RAG_EXIBIR_FONTES_PAINEL` (true). As duas ultimas serao consumidas no Passo 9.
- CLI de teste criado: `backend/scripts/buscar_rag.py`. Aceita `--top-k`, `--tipo`, `--tipos`, `--score-minimo` e `--json`, exibindo score, distancia, titulo, URL (quando existir em metadata) e trecho resumido.

### Passo 9: Integracao com o agente de vendas

Alterar o fluxo do `ProcessadorMensagem` e do `GeradorRespostas`:

- acionar RAG para `PERGUNTAR_PRODUTO`, `PERGUNTAR_PRECO` e `FORA_CONTEXTO`;
- passar trechos recuperados para o gerador;
- orientar o prompt a responder apenas com base nos trechos;
- se a busca vier vazia ou fraca, responder com fallback seguro e oferecer atendimento humano;
- para perguntas de preco, usar sempre resposta padrao de encaminhamento para humano/orcamento, mesmo que a RAG encontre trechos relacionados;
- permitir sugestao de produtos, mas controlada por configuracao;
- registrar quais trechos da RAG foram usados para permitir auditoria e exibicao no painel interno;
- manter templates atuais para saudacao, CNPJ, orcamento, reclamacao e escalonamento.

Prompt deve reforcar:

- "Use somente os trechos do catalogo abaixo";
- "Se a informacao nao estiver nos trechos, diga que vai encaminhar para validacao";
- "Nao invente preco, prazo, compatibilidade ou disponibilidade";
- "Resposta curta para WhatsApp".

Configuracoes propostas:

- `RAG_ENABLED=true`;
- `RAG_SUGERIR_PRODUTOS=false` por padrao no inicio, ativavel quando os testes estiverem confiaveis;
- `RAG_EXIBIR_FONTES_PAINEL=true`;
- `RAG_TOP_K=4`;
- `RAG_SCORE_MINIMO=0.70`.

Quando `RAG_SUGERIR_PRODUTOS=true`, o agente pode sugerir opcoes com linguagem cautelosa, por exemplo: "Pelo que voce descreveu, uma opcao que pode fazer sentido e... Posso encaminhar para um vendedor confirmar a melhor configuracao." Quando estiver `false`, o agente deve apenas explicar opcoes e coletar dados para o vendedor.

Resultado em 2026-04-30:

- Banco: migration `backend/alembic/versions/2026043002_adiciona_rag_em_processamentos.py` adiciona em `processamentos_mensagem` as colunas `rag_utilizada` (bool), `rag_trechos` (JSONB) e `rag_score_maximo` (Numeric(5,4)).
- Modelo: `ProcessamentoMensagem` ganhou os campos correspondentes e `to_dict()` foi estendido para expor os novos dados no endpoint `/api/processamentos/{id}` (ja consumido pelo painel).
- Templates: adicionado `PRODUTO_SEM_CONTEXTO` em `backend/services/respostas/templates.py` como fallback seguro quando a RAG vem vazia ou fraca.
- `GeradorRespostas` agora tem `gerar_com_rag(pergunta_cliente, trechos, permitir_sugestao_produto, template_fallback, template_fallback_nome)`. Monta prompt restritivo com os trechos numerados (titulo + conteudo + URL quando houver) e reforca as regras obrigatorias pedidas no plano: usar apenas os trechos, nao inventar preco/prazo/compatibilidade/disponibilidade, encaminhar para humano quando faltar contexto, resposta curta para WhatsApp e no maximo 1 emoji. A regra de sugestao alterna entre `_REGRA_SUGESTAO_ON` e `_REGRA_SUGESTAO_OFF` conforme `RAG_SUGERIR_PRODUTOS`.
- `RespostaGerada` ganhou `rag_utilizada`, `trechos_rag` e `rag_score_maximo`; `gerar_com_rag` preenche esses campos mesmo nos caminhos de fallback (sem trechos, sem LLM ou LLM vazia/erro), garantindo auditoria consistente.
- `ProcessadorMensagem`:
  - aceita `retrieval: RetrievalService | None` opcional no construtor e, quando omitido e `settings.RAG_ENABLED`, tenta obter via `get_retrieval_service()`, caindo graciosamente (log warning) se a chave de embeddings nao estiver configurada;
  - `PERGUNTAR_PRODUTO` e `FORA_CONTEXTO` passam por `_responder_com_rag(...)`, que delega a `GeradorRespostas.gerar_com_rag(...)` com `RAG_SUGERIR_PRODUTOS` e fallback dedicado por intencao (`PRODUTO_SEM_CONTEXTO` ou `FORA_CONTEXTO`);
  - `PERGUNTAR_PRECO` mantem o template `PRECO_NAO_NEGOCIADO`, mas ainda dispara `_buscar_trechos_rag(...)` e usa o helper `_anexar_trechos_para_auditoria(...)` para registrar quais trechos a RAG retornou, sem alterar o texto enviado ao cliente;
  - `_buscar_trechos_rag` busca com `tipo=None` (nao filtra por tipo nesta v1, ja que os chunks sao majoritariamente `produto` e FAQ) e tolera RAG desativada ou falha externa retornando lista vazia;
  - `_criar_processamento` persiste `rag_utilizada`, `rag_trechos` (ou `None` quando vazio) e `rag_score_maximo` arredondado para 4 casas.
- Configuracoes `RAG_ENABLED`, `RAG_TOP_K`, `RAG_SCORE_MINIMO`, `RAG_SUGERIR_PRODUTOS` e `RAG_EXIBIR_FONTES_PAINEL` ja estavam em `backend/config.py` e `backend/.env.example` desde o Passo 8; `RAG_SUGERIR_PRODUTOS` passou a ser consumido no prompt restritivo e `RAG_EXIBIR_FONTES_PAINEL` ficara como chave de apresentacao no painel (proximo passo cliente).
- Sem mudanca em `main.py`: o lifespan continua instanciando `ProcessadorMensagem(llm=llm)` e o `RetrievalService` e obtido lazy.

### Passo 10: Avaliacao

Montar uma bateria de perguntas a partir das conversas e de casos esperados:

- "Qual relogio de ponto serve para restaurante com 25 funcionarios?"
- "Catraca biometrica funciona com cartao tambem?"
- "O leitor facial e melhor que biometria para cozinha?"
- "Tem controle de acesso por QR Code?"
- "Quanto custa?"
- "Instala em Sao Paulo?"
- "Integra com meu software?"

Para cada pergunta, avaliar:

- se recuperou o produto correto;
- se a resposta ficou curta e clara;
- se nao inventou dado ausente;
- se escalou quando deveria;
- se citou necessidade de validacao tecnica quando aplicavel.

## 7. Ordem recomendada de implementacao

1. Confirmar este plano e ajustar escopo da v1.
2. Criar scripts de inventario e pre-processamento.
3. Rodar pre-processamento e revisar amostras manualmente.
4. Definir metadados finais e regras de deduplicacao.
5. Criar migration `pgvector` e tabela `documentos_conhecimento`.
6. Criar provider de embeddings.
7. Criar script idempotente de ingestao.
8. Criar `RetrievalService`.
9. Integrar RAG ao gerador de respostas.
10. Criar testes unitarios para chunking, deduplicacao e retrieval.
11. Rodar avaliacao com perguntas reais/simuladas.
12. Ajustar prompts, limiar de confianca e tamanho dos chunks.

## 8. Riscos e mitigacoes

| Risco | Impacto | Mitigacao |
|------|---------|-----------|
| Duplicidade entre folder e scraping | Respostas repetitivas ou contraditorias | Deduplicacao por hash e similaridade; precedencia por fonte |
| Texto raw com menu/rodape | Chunks ruins e respostas poluidas | Pre-processamento com filtros por padrao |
| Conversas com dados pessoais | Vazamento de informacao sensivel | Nao indexar conversas cruas; anonimizar para avaliacao |
| FAQ criada a partir de conversa ruim | Resposta reutilizada com erro comercial | Curadoria humana antes de ativar pergunta/resposta |
| RAG recuperar trecho irrelevante | Resposta errada com aparencia segura | Limiar de score, top_k baixo, fallback humano |
| LLM inventar alem do contexto | Risco comercial e tecnico | Prompt restritivo e testes com perguntas sem resposta |
| Falta de preco/prazo nos documentos | Cliente pode insistir | Resposta padrao: encaminhar para vendedor humano/orcamento |
| Dependencia da OpenAI para embeddings | Mais uma chave externa | Provider abstrato; possibilidade futura de embeddings locais |

## 9. Criterios de pronto da v1

- Pipeline de pre-processamento gera JSONL limpo e revisavel.
- Ingestao pode ser reexecutada sem duplicar registros.
- Banco possui chunks com embeddings e metadados rastreaveis.
- Busca retorna trechos relevantes para perguntas simples de produto.
- Agente responde perguntas de produto usando RAG.
- Sugestao de produtos existe, mas pode ser ligada/desligada por configuracao.
- Perguntas de preco seguem resposta padrao de humano/orcamento.
- Painel interno consegue exibir os trechos usados pela RAG.
- Agente nao inventa preco, prazo, disponibilidade ou compatibilidade.
- Quando nao houver contexto suficiente, agente oferece escalonamento humano.
- Existe conjunto inicial de perguntas de avaliacao baseado nas conversas.
- Conversas do WhatsApp sao anonimizadas antes de gerar exemplos de estilo ou FAQ curada.

## 10. Perguntas para discussao

1. Na v1, devemos indexar apenas paginas `produtos_*.txt` e folders, ou tambem categorias, servicos e blog?
   - Status: em aberto; discutir melhor antes de decidir.
2. O agente pode sugerir um produto mais adequado com base no perfil do cliente, ou deve apenas explicar opcoes e pedir que o vendedor confirme?
   - Decisao: pode sugerir produtos, mas a sugestao deve ficar sujeita a ativacao/desativacao por configuracao.
3. Devemos manter uma resposta padrao para perguntas de preco sempre escalando para humano/orcamento?
   - Decisao: sim.
4. Queremos exibir no painel interno quais trechos da RAG foram usados para gerar a resposta?
   - Decisao: sim.
5. As conversas do WhatsApp devem virar apenas base de avaliacao por enquanto, ou tambem uma base separada de "estilo de atendimento" apos anonimização?
   - Decisao: usar, se possivel, para definir estilo e tambem para alimentar uma base curada de perguntas e respostas. Futuramente, a interface de acompanhamento deve permitir adicionar uma resposta humana a uma pergunta para alimentar a base de conhecimento.
