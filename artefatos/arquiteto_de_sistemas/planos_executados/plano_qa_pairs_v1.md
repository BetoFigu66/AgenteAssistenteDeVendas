# Plano Q&A Pairs v1

**Data:** 2026-05-02  
**Agente:** Arquiteto de Sistemas  
**Status:** Em andamento — 8 de 9 passos concluídos (aguardando Passo 8: Frontend)
**Atualizado em:** 2026-05-10

## 1. Contexto e motivacao

O plano RAG Produtos v1 (`plano_rag_produtos_v1.md`) implementou busca semantica sobre chunks gerados a partir de webscraping e folders de produtos. Durante os primeiros testes de avaliacao, identificamos um problema estrutural que limita a qualidade das respostas:

- As queries dos usuarios sao **perguntas** em linguagem natural.
- Os chunks indexados sao **descricoes de produto** em prosa.
- Esse mismatch semantico entre pergunta e prosa resulta em scores baixos (tipicamente 0.55–0.65) mesmo para perguntas diretamente respondidas pelo conteudo.

A abordagem de pares Q&A resolve esse problema na raiz: ao indexar as **perguntas curadas** (nao as respostas nem o conteudo bruto), a comparacao passa a ser pergunta-do-usuario vs. pergunta-cadastrada — mesmo tipo semantico, scores tipicamente 0.80–0.95.

Vantagens adicionais:

- Qualidade controlada por humano, nao por pipeline automatico.
- Cada par cadastrado funciona imediatamente, sem re-ingestao de chunks.
- Operadores podem criar novos pares a partir de trechos de conversas reais.
- Debugabilidade alta: facil identificar qual par foi usado e quem o cadastrou.

## 2. Objetivo

Implementar uma camada de busca por pares Pergunta+Resposta curados, com as seguintes propriedades:

- Busca semantica usando pgvector sobre o campo `pergunta` dos pares.
- Prioridade sobre a busca por chunks de produto no fluxo do agente.
- Interface no painel interno para operadores cadastrarem, editarem e aprovarem pares.
- Script de seed com as perguntas mais frequentes do catalogo Inforrel para bootstrap rapido.
- Coexistencia com a RAG de chunks (fallback de cobertura ampla).

## 3. Decisao tecnica

### 3.1 Nova tabela `pares_qa` (nao reutilizar `documentos_conhecimento`)

A tabela `documentos_conhecimento` armazena `conteudo` como campo monolitico (pergunta + resposta fundidos). Para Q&A pairs precisamos:

- Separar `pergunta` e `resposta` em colunas proprias.
- Gerar o embedding **somente sobre o campo `pergunta`**, nao sobre a resposta.
- Expor CRUD dedicado no painel sem misturar com o gerenciamento de chunks.

Por isso, uma tabela separada e a escolha correta.

### 3.2 Embedding somente da pergunta

O campo `embedding` de cada par e gerado a partir do texto de `pergunta` unico. Isso maximiza a similaridade cossenal com queries de usuarios, que tambem sao perguntas.

### 3.3 Fluxo de busca em duas camadas

```
Query do usuario
    │
    ▼
[Camada 1] QAService.buscar(query, contexto?)
  → score >= 0.80 ?
    Sim → retorna resposta curada diretamente ao gerador
    Nao ↓

[Camada 2] RetrievalService.buscar(query, tipo='produto')
  → score >= RAG_SCORE_MINIMO (0.55 recomendado) ?
    Sim → gera resposta contextual com LLM + chunks
    Nao ↓

[Fallback] Template de escalonamento para humano
```

### 3.4 Campo `contexto` como string livre com valores convencionados

Nao usar enum no banco para permitir evolucao sem migration. O frontend oferece ssugestoes a partir de lista fixa, mas o campo aceita qualquer string.

Valores convencionados para Inforrel v1:

| Valor | Uso |
|-------|-----|
| `geral` | Empresa, contato, instalacao em geral |
| `catraca` | Catracas de acesso, modelos, aplicacoes |
| `relogio_ponto` | Relogios de ponto, integracao, funcionalidades |
| `controle_acesso` | Controle de acesso eletronico |
| `bastao_ronda` | Bastao de ronda TOPDATA |
| `facial` | Reconhecimento facial |
| `leitor_biometrico` | Leitores biometricos |
| `suporte` | Instalacao, integracao, compatibilidade tecnica |

## 4. Estrutura da tabela

```sql
CREATE TABLE pares_qa (
    id            SERIAL PRIMARY KEY,
    id_externo    VARCHAR(255) NOT NULL UNIQUE,   -- ex: "qa:catraca:abc123"
    pergunta      TEXT        NOT NULL,
    resposta      TEXT        NOT NULL,
    contexto      VARCHAR(100),                   -- valor convencionado ou livre
    tags          TEXT[],                         -- tags opcionais para refinamento
    embedding     vector(1536),                   -- embedding de `pergunta` apenas
    ativo         BOOLEAN     NOT NULL DEFAULT TRUE,
    aprovado      BOOLEAN     NOT NULL DEFAULT FALSE,
    criado_por    VARCHAR(100),
    criado_em     TIMESTAMP   NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pares_qa_contexto ON pares_qa(contexto) WHERE ativo = TRUE;
CREATE INDEX idx_pares_qa_aprovado ON pares_qa(aprovado)  WHERE ativo = TRUE;
```

O index vetorial (HNSW ou IVFFlat) sera adicionado via Alembic apos a ingestao do seed,
conforme padrao adotado em `documentos_conhecimento`.

## 5. Escopo da v1

### Entra na v1

- Modelo `ParQA` em `models.py` + migration Alembic.
- `QAService` com metodo `buscar(query, contexto, score_minimo)`.
- Script idempotente `scripts/ingerir_pares_qa.py` (aceita JSON).
- Arquivo de seed `data/seed_pares_qa.json` com ~25 pares iniciais da Inforrel.
- Endpoints CRUD `/api/pares-qa` (list, get, post, patch, delete-soft).
- Integracao no `processador.py` como camada prioritaria sobre chunks.
- Frontend: pagina "Base Q&A" no painel interno com lista, formulario e aprovacao.
- Script de teste CLI `scripts/buscar_qa.py` analogo ao `buscar_rag.py`.
- Config: `QA_SCORE_MINIMO` (default 0.80) e `QA_ENABLED` (default true) em `config.py`.

### Fica fora da v1

- Extracao automatica de pares Q&A a partir de conversas.
- Contexto de negociacao no processador para pre-filtrar buscas.
- Aprovacao com workflow (notificacao, historico de revisoes).
- Versioning de pares (historico de edicoes).
- Importacao em lote via CSV pelo frontend.

## 6. Passos de implementacao

### ✅ Passo 1: Modelo e migration

- Adicionar `ParQA` (SQLAlchemy ORM) em `models.py` com todos os campos da secao 4.
- Expor `to_dict()` e `from_dict()` no modelo.
- Criar migration Alembic: `python -m alembic revision --autogenerate -m "adiciona_pares_qa"`.
- Aplicar: `python -m alembic upgrade head`.

### ✅ Passo 2: QAService

Criar `backend/services/rag/qa_service.py`:

- Classe `QAService(embeddings, session_factory, score_minimo_padrao, top_k_padrao)`.
- Dataclass `ParRecuperado(id, id_externo, pergunta, resposta, contexto, tags, score, distancia)`.
- Metodo `async buscar(query, contexto=None, top_k=None, score_minimo=None, apenas_aprovados=True)`.
  - Gera embedding da query via `EmbeddingProvider.embed_um(query)`.
  - Consulta `pares_qa` por distancia cosseno (`<=>`) com `return_type=Float()`.
  - Filtra por `contexto` quando fornecido.
  - Filtra por `aprovado=True` quando `apenas_aprovados=True`.
  - Retorna lista de `ParRecuperado` com score >= limiar.
- Factory `get_qa_service()` com `lru_cache(maxsize=1)`.
- Exportar de `services/rag/__init__.py`.

### ✅ Passo 3: Script de ingestao

Criar `backend/scripts/ingerir_pares_qa.py`:

- Le `backend/data/seed_pares_qa.json` (ou arquivo passado via `--arquivo`).
- Para cada par: calcula hash da pergunta para `id_externo` se nao informado.
- Gera embedding da `pergunta` via `EmbeddingProvider`.
- Insert/update idempotente por `id_externo` (mesmo padrao do `ingerir_conhecimento_rag.py`).
- Flags: `--dry-run`, `--aprovar-automaticamente`, `--arquivo`.
- Loga estatisticas: inseridos, atualizados, ignorados.

### ✅ Passo 4: Arquivo de seed

Criar `backend/data/seed_pares_qa.json` com ~25 pares cobrindo as perguntas mais frequentes do catalogo Inforrel. Exemplos (nao exaustivo):

```json
[
  {
    "id_externo": "qa:relogio_ponto:001",
    "contexto": "relogio_ponto",
    "pergunta": "Qual relogio de ponto serve para restaurante com 25 funcionarios?",
    "resposta": "Para um restaurante com ate 25 funcionarios, recomendamos o Henry Inner Face IV ou o Henry Supra Face, que suportam reconhecimento facial em ambientes com variacao de luminosidade e sao ideais para areas de cozinha. Para validar o modelo exato e as condicoes de instalacao, nosso tecnico pode avaliar o local. Posso agendar uma visita?"
  },
  {
    "id_externo": "qa:catraca:001",
    "contexto": "catraca",
    "pergunta": "Qual catraca funciona com biometria e cartao ao mesmo tempo?",
    "resposta": "As catracas da linha Intelbrás e da Comelit suportam multi-tecnologia: biometria digital, cartao RFID e senha no mesmo equipamento. A escolha do modelo depende do fluxo de pessoas e do ambiente. Posso detalhar as especificacoes tecnicas de cada opcao."
  },
  {
    "id_externo": "qa:bastao_ronda:001",
    "contexto": "bastao_ronda",
    "pergunta": "Como fiscalizar se os vigilantes estao fazendo a ronda?",
    "resposta": "O Bastao de Ronda TOPDATA resolve isso. O vigilante toca o bastao nos iButtons instalados nos pontos de ronda e o sistema registra horario e local de cada toque. O software gera relatorios completos do percurso. Posso enviar mais detalhes sobre instalacao e custo?"
  }
]
```

O arquivo completo com todos os pares sera criado no Passo 4 da implementacao.

### ✅ Passo 5: Endpoints CRUD

Adicionar em `main.py` (ou router dedicado `routers/pares_qa.py`):

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/pares-qa` | Lista pares (query params: contexto, ativo, aprovado, page, limit) |
| GET | `/api/pares-qa/{id}` | Retorna um par pelo id |
| POST | `/api/pares-qa` | Cria novo par (gera embedding automaticamente) |
| PATCH | `/api/pares-qa/{id}` | Atualiza par (re-gera embedding se pergunta mudou) |
| DELETE | `/api/pares-qa/{id}` | Soft delete (ativo = false) |
| POST | `/api/pares-qa/{id}/aprovar` | Marca par como aprovado |

O POST e o PATCH devem gerar/re-gerar o embedding da `pergunta` automaticamente.

### ✅ Passo 6: Integracao no processador

Alterar `backend/services/processador.py`:

- Injetar `QAService` no construtor de `ProcessadorMensagem` (analogo ao `RetrievalService`).
- Novo metodo `async _buscar_resposta_qa(query) -> ParRecuperado | None`.
- Em `_responder_com_rag`:
  1. Chamar `_buscar_resposta_qa(query)` primeiro.
  2. Se hit: usar `par.resposta` como contexto principal, gerar resposta personalizada com LLM.
  3. Se nao hit: chamar `_buscar_trechos_rag(query)` como antes.
- Registrar em `ProcessamentoMensagem.rag_trechos` qual par Q&A foi usado (prefixar com `qa:`).

### ✅ Passo 7: Script de teste CLI

Criar `backend/scripts/buscar_qa.py`:

- Analogo ao `buscar_rag.py`.
- Aceita `--contexto`, `--score-minimo`, `--apenas-aprovados`, `--json`.
- Exibe: score, distancia, contexto, pergunta, preview da resposta.

### 🔲 Passo 8: Frontend — pagina Base Q&A  ← PENDENTE

Criar componente `frontend/src/components/QABasePage.jsx`:

- Lista paginada de pares com colunas: contexto, pergunta (truncada), aprovado, acoes.
- Filtros: contexto, status (ativo/inativo), aprovado/pendente.
- Modal de criacao/edicao com campos: contexto (select com sugestoes), pergunta (textarea),
  resposta (textarea), tags (input chips).
- Botao "Aprovar" inline na lista.
- Adicionar rota `/qa-base` no `App.jsx`.
- Adicionar item no menu de navegacao.

### ✅ Passo 9: Configuracoes

Adicionar em `backend/config.py` e `backend/.env.example`:

```env
QA_ENABLED=true
QA_SCORE_MINIMO=0.80
QA_TOP_K=3
QA_APENAS_APROVADOS=true
```

## 7. Ordem de implementacao recomendada

1. Passo 1 — Modelo e migration (pre-requisito de tudo).
2. Passo 9 — Configuracoes em `config.py`.
3. Passo 2 — QAService.
4. Passo 3 + 4 — Script de ingestao + seed inicial.
5. Passo 7 — Script CLI de teste (validar busca antes de integrar).
6. Passo 6 — Integracao no processador.
7. Passo 5 — Endpoints CRUD.
8. Passo 8 — Frontend.

## 8. Metricas de avaliacao

Usar as mesmas perguntas do `plano_rag_produtos_v1.md` (secao de avaliacao) mais:

- % de perguntas com Q&A hit (score >= 0.80).
- Score medio dos hits Q&A vs. hits de chunks.
- % de respostas que o operador marcaria como "aceitavel".
- Tempo ate primeira resposta aceitavel (benchmark: < 2 dias apos seed).

## 9. Riscos e mitigacoes

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Seed inicial com respostas erradas | Respostas incorretas desde o inicio | Flag `aprovado=false` por padrao; ativar apenas apos revisao humana |
| Cobertura baixa nas primeiras semanas | Muitos fallbacks para chunks | Priorizar seed com as 20 perguntas mais frequentes historicamente |
| Pares duplicados ou conflitantes | Respostas inconsistentes | `id_externo` unico + revisao de similaridade entre pares no script de ingestao |
| Score 0.80 muito alto para algumas perguntas | Miss em perguntas validas | Controle dinamico via endpoint `/api/config/rag` (ja implementado) |
| Operadores cadastrando respostas com informacoes comerciais incorretas | Promessas indevidas ao cliente | Campo `aprovado`: so respostas revisadas chegam ao agente |

## 10. Evolucoes planejadas (v2)

- **Extracao de pares de conversas**: botao no painel de chat para o operador criar um par Q&A
  a partir de uma mensagem real e uma resposta humana aprovada.
- **Contexto de negociacao**: detectar automaticamente o topico dominante da negociacao
  (catraca, relogio_ponto, etc.) e pre-filtrar a busca Q&A por esse contexto, aumentando
  a precisao sem diminuir o limiar de score.
- **Feedback loop**: operador avalia respostas do agente diretamente no painel e a avaliacao
  negativa aciona sugestao de novo par Q&A.
- **Importacao CSV**: upload em lote de pares no frontend.
