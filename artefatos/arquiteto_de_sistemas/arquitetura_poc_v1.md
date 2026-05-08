# Arquitetura POC - Assistente de Vendas via WhatsApp com IA

**Versão**: 1.0  
**Data**: 2026-04-13  
**Status**: Esboço para validação  
**Moeda**: Valores em US$ (dólares americanos)

---

## 1. Objetivo do POC

Validar a viabilidade técnica de um assistente de vendas via WhatsApp com IA, com **custo mínimo** e **tempo reduzido** de desenvolvimento.

### Critérios de Sucesso do POC
- [ ] Receber mensagens do WhatsApp
- [ ] Responder automaticamente perguntas sobre valor, modelos, prazo, instalação
- [ ] Enviar catálogos quando solicitado
- [ ] Escalar para humano (Rita) quando necessário
- [ ] Funcionar de forma estável por 1 semana

---

## 2. Diagrama da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE                                  │
│                    (WhatsApp do cliente)                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   WHATSAPP BUSINESS API                         │
│                  (Twilio ou Evolution API)                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Webhook
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Webhook    │  │ Orquestrador│  │  Gerenciador de         │  │
│  │  Receiver   │─▶│ de Conversa │─▶│  Handoff                │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│                   ┌─────────────┐                                │
│                   │  Motor IA   │                                │
│                   │  (OpenAI)   │                                │
│                   └──────┬──────┘                                │
│                          │                                       │
│                          ▼                                       │
│                   ┌─────────────┐                                │
│                   │    RAG      │                                │
│                   │ (Simples)   │                                │
│                   └─────────────┘                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BANCO DE DADOS                             │
│                   (PostgreSQL 16)                               │
│  - Histórico de conversas                                       │
│  - Base de conhecimento (produtos, preços, FAQ)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes

### 3.1 WhatsApp Business API

**Opções avaliadas:**

| Opção | Prós | Contras | Custo |
|-------|------|---------|-------|
| **Twilio** | Fácil setup, boa documentação | Mais caro | ~$15/mês + $0.005/msg |
| **Evolution API** | Open source, sem custo de API | Requer servidor, menos estável | Apenas infra |
| **360dialog** | Oficial Meta, bom preço | Setup mais complexo | ~€49/mês |

**Decisão POC**: **Twilio Sandbox** (grátis para dev, boa documentação, setup rápido)

### 3.2 Backend (FastAPI)

```
src/
├── main.py              # Aplicação FastAPI
├── config.py            # Configurações
├── routers/
│   └── webhook.py       # Recebe mensagens do WhatsApp
├── services/
│   ├── whatsapp.py      # Envia mensagens
│   ├── orquestrador.py  # Lógica de conversa
│   ├── ia.py            # Integração OpenAI
│   └── rag.py           # Busca na base de conhecimento
├── models/
│   └── conversa.py      # Modelos de dados
└── data/
    ├── produtos.json    # Catálogo de produtos
    ├── precos.json      # Tabela de preços
    └── faq.json         # Perguntas frequentes
```

### 3.3 Motor de IA

**Modelo**: GPT-4o-mini (custo-benefício)

**Prompt base**:
```
Você é um assistente de vendas da [Empresa] especializado em catracas e relógios de ponto.

Seu papel:
- Responder dúvidas sobre produtos, preços, prazos e instalação
- Enviar catálogos quando solicitado
- Ser cordial e profissional
- Quando não souber ou for negociação de preço, escalar para humano

Produtos disponíveis:
[Injetado via RAG]

Regras:
- Nunca invente informações
- Preços têm margem de negociação (mencione que pode haver desconto para quantidades)
- Para instalação, informe que depende da região
```

### 3.4 RAG Simplificado (POC)

Para o POC, RAG será **baseado em arquivos JSON**, sem banco vetorial:

```json
// produtos.json
{
  "catracas": [
    {
      "modelo": "Catraca Pedestal",
      "descricao": "Catraca de acesso para academias e condomínios",
      "preco_base": 2500,
      "prazo_entrega": "5-10 dias úteis"
    }
  ],
  "relogios": [
    {
      "modelo": "Relógio Biométrico RB-100",
      "tecnologias": ["biometria", "cartão proximidade"],
      "preco_base": 1200,
      "prazo_entrega": "3-7 dias úteis"
    }
  ]
}
```

**Busca**: Keyword matching simples + contexto injetado no prompt.

### 3.5 Lógica de Handoff

```python
ESCALAR_PARA_HUMANO = [
    "falar com humano",
    "falar com vendedor", 
    "negociar",
    "desconto",
    "problema",
    "reclamação",
    "não funciona",
    "compatibilidade",  # Rita mencionou que isso exige análise
]

def deve_escalar(mensagem: str, confianca_ia: float) -> bool:
    # Palavras-chave de escalonamento
    for palavra in ESCALAR_PARA_HUMANO:
        if palavra in mensagem.lower():
            return True
    
    # Baixa confiança da IA
    if confianca_ia < 0.7:
        return True
    
    return False
```

---

## 4. Stack Tecnológica

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| Backend | **FastAPI** | Preferência do dev, async, rápido |
| Banco | **PostgreSQL 16** | Robusto, suporta JSONB, padrão de mercado, roda em container |
| IA | **OpenAI GPT-4o-mini** | Custo-benefício, boa qualidade |
| WhatsApp | **Evolution API** ou **Twilio Sandbox** | Custo zero para POC |
| Hospedagem | **Local + ngrok** | Grátis, rápido para testar |
| Cache | **Não necessário** | Volume baixo (10-30/dia) |

WhatsApp:  A prinípio escolhido o **Twilio Sandbox**
---

## 5. Fluxo de Mensagem

```
1. Cliente envia mensagem no WhatsApp
         │
         ▼
2. Webhook recebe e salva no banco
         │
         ▼
3. Orquestrador analisa:
   ├── É saudação? → Responde com boas-vindas
   ├── Pede catálogo? → Envia PDF
   ├── Pergunta sobre produto? → Consulta RAG + IA
   └── Precisa de humano? → Notifica Rita
         │
         ▼
4. IA gera resposta com contexto do RAG
         │
         ▼
5. Verifica confiança:
   ├── Alta (>0.7) → Envia resposta
   └── Baixa (<0.7) → Escala para Rita (Ou sinaliza na interface de acompanhamento que a confiança está baixa na mensagem)
         │
         ▼
6. Resposta enviada via WhatsApp API
```

---

## 6. Estimativas

### Tempo de Desenvolvimento
| Componente | Horas |
|------------|-------|
| Setup WhatsApp API | 4-6h |
| Backend FastAPI (webhook, envio) | 6-8h |
| Integração OpenAI | 3-4h |
| RAG simples (JSON) | 3-4h |
| Lógica de handoff | 2-3h |
| Testes e ajustes | 4-6h |
| **Total** | **22-31h** |

### Custos Mensais (POC)
| Item | Custo |
|------|-------|
| OpenAI API (~1000 msgs/mês) | ~$5-10 |
| WhatsApp (Evolution/Twilio sandbox) | $0 |
| Hospedagem (local) | $0 |
| **Total** | **~$5-10/mês** |

---

## 7. Limitações Aceitas no POC

- [ ] Sem analytics/métricas
- [ ] Sem alta disponibilidade
- [ ] RAG simples (sem embeddings)
- [ ] Apenas um número WhatsApp
- [ ] Sem suporte a áudio/imagens do cliente

---

## 8. Decisões Arquiteturais (ADRs)

### ADR-001: SQLite vs PostgreSQL
**Decisão**: ~~SQLite para POC~~ **PostgreSQL 16 desde o início** (revisado em 2026-04)  
**Motivo original**: Simplicidade do SQLite  
**Motivo da revisão**: SQLite não suporta `ALTER TABLE` com FK (problema com batch mode do Alembic), além de não ter JSONB nativo. PostgreSQL rodando em container Docker resolve tudo com baixa complexidade adicional.  
**Status**: Implementado

### ADR-002: RAG com JSON vs Banco Vetorial
**Decisão**: ~~JSON com keyword matching~~ **Substituída pelo ADR-004** (revisado em 2026-04-29)
**Motivo original**: Catálogo pequeno (~20 produtos), não justificava complexidade
**Motivo da revisão**: Um dos objetivos do projeto é aquisição de conhecimento técnico. O custo financeiro de embeddings é desprezível (< $0,50/mês com OpenAI `text-embedding-3-small`) e o overhead de implementação é aceitável (~11h). Antecipar essa decisão evita refactor tardio do prompt/retrieval depois que o POC já estiver em produção.
**Status**: Substituído por ADR-004

### ADR-003: Evolution API vs Twilio
**Decisão**: Twilio Sandbox
**Motivo**: Custo zero para validação, boa documentação, setup rápido
**Data da decisão**: 2026-04-19
**Revisão**: Avaliar Twilio produção ou 360dialog quando sair do POC

### ADR-004: RAG com pgvector + OpenAI embeddings
**Decisão**: Implementar RAG com `pgvector` no Postgres existente, usando `text-embedding-3-small` da OpenAI (1536 dimensões) como provider de embeddings, mantendo o LLM de chat (Groq) inalterado.
**Data da decisão**: 2026-04-29
**Status**: Aprovado, aguardando implementação

#### Contexto
O ADR-002 previa "RAG simples sem embeddings". Ao avaliar o trade-off, ficou claro que:
- Custo financeiro: < $0,50/mês para o volume previsto (~1.000 mensagens/mês, catálogo de ~50 produtos).
- Custo de implementação: ~11h adicionais (vs. ~3-4h do RAG por keyword previsto originalmente).
- Risco de adiar: trocar a estratégia de retrieval depois que prompts e dados já estão em produção é caro, porque mexe simultaneamente em modelo de dados, prompts, avaliação e ingestão.
- Objetivo do projeto: aquisição de conhecimento técnico — embeddings é peça central do estado-da-arte em assistentes conversacionais.

#### Componentes da decisão
1. **Banco vetorial**: `pgvector` rodando no mesmo Postgres do projeto (imagem `pgvector/pgvector:pg16`). Sem nova infra.
2. **Modelo de embedding**: OpenAI `text-embedding-3-small`, 1536 dimensões. Justificativa: barato, estável, multilíngue (suporta PT-BR razoavelmente), padrão de mercado para didática.
3. **Provider separado do LLM de chat**: novo `EmbeddingProvider` (ABC) com `OpenAIEmbeddingProvider` concreto. Variáveis `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_API_KEY` independentes de `LLM_*`. Permite manter Groq para chat (rápido e barato) e OpenAI só para embedding.
4. **Modelo de dados**: tabela única `documentos_conhecimento` com `tipo` (enum: produto/faq/politica), `titulo`, `conteudo`, `metadata JSONB`, `embedding vector(1536)`. Índice `ivfflat` com `vector_cosine_ops`. Tabela única simplifica retrieval e ingestão; especialização por tipo fica em `metadata`.
5. **Conteúdo inicial**: apenas catálogo de produtos (linhas da tabela `produtos`). FAQ fica para iteração futura.
6. **Trigger do retrieval**: o `RetrievalService` é consultado apenas nas intenções `PERGUNTAR_PRODUTO`, `PERGUNTAR_PRECO` e `FORA_CONTEXTO`. Demais intenções continuam usando templates atuais.
7. **Integração**: `GeradorRespostas` recebe os trechos recuperados via parâmetro de contexto e injeta no prompt do LLM ("trechos do catálogo: ..."), sem alterar o `LLMProvider`.

#### Alternativas consideradas e descartadas
- **Embeddings locais (`sentence-transformers`)**: zero custo, mas ~500MB de dependências e 100-300ms/query no CPU. Atrasa o POC. Pode ser revisitado depois.
- **Cohere `embed-multilingual-v3`**: melhor qualidade em PT-BR, mas adiciona uma terceira conta/chave e custa mais. Para catálogo pequeno o ganho não compensa.
- **Tabelas separadas por tipo (produtos, faq, politicas)**: mais "limpo", mas multiplica retrieval logic e migrations. Tabela única + `tipo` cobre o POC e refatorar é trivial se precisar.
- **RAG sempre ativo (todos os turnos)**: mais flexível, mas aumenta custo de tokens e latência. Decidimos por trigger seletivo.

#### Consequências
- **Positivas**: aprendizado real do stack vetorial; ganho de qualidade em perguntas semânticas; mesma estratégia escala para FAQ e políticas no futuro sem refactor.
- **Negativas**: +1 dependência externa (OpenAI), +1 chave de API para gerenciar, ~11h adicionais no esforço do POC.
- **Mitigações**: `EmbeddingProvider` é ABC, então trocar OpenAI por local depois é uma classe nova; ingestão é idempotente, então re-rodar quando o catálogo mudar é seguro.

#### Critérios de revisão
Revisitar este ADR quando:
- Catálogo passar de ~500 produtos (avaliar se `ivfflat` ainda é suficiente ou migrar para `hnsw`).
- Custo mensal de embeddings ultrapassar $20 (avaliar embedding local).
- Latência do retrieval passar de 300ms (otimizar índice ou cache).

#### Tarefas que este ADR habilita (não faz parte da decisão)
- Migration Alembic com `CREATE EXTENSION vector` e tabela `documentos_conhecimento`.
- Implementação de `EmbeddingProvider` + `OpenAIEmbeddingProvider`.
- Implementação de `RetrievalService.buscar(query, top_k, tipo)`.
- Script CLI `backend/scripts/ingerir_conhecimento.py` (idempotente, batch).
- Integração no `GeradorRespostas` para as 3 intenções listadas.
- Atualização da seção 6 (estimativas) e seção 7 (limitações) deste documento ao concluir a implementação.

---

## 9. Próximos Passos

1. [ ] Validar arquitetura com o time
2. [ ] Configurar ambiente de desenvolvimento
3. [ ] Setup da API do WhatsApp escolhida
4. [ ] Criar estrutura base do FastAPI
5. [ ] Montar base de conhecimento (JSON) com catálogos da Rita
6. [ ] Implementar fluxo básico de mensagem
7. [ ] Testar com mensagens reais

---

## 10. Processo de Liberação de Versão (POC)

**Responsável pela validação**: Kika (Analista de Requisitos)

**Fluxo**:
1. Desenvolvedor conclui implementação
2. Kika valida contra critérios de aceite dos requisitos
3. Se aprovado → versão liberada
4. Se reprovado → retorna para correção com feedback

**Justificativa**: Kika já define os critérios de aceite, então faz sentido ela validar se foram atendidos durante o POC.

### 10.1 Disponibilização de Versões

| Etapa | Validador | Método | Motivo |
|-------|-----------|--------|--------|
| Validação interna | Kika | Docker (`docker-compose up`) | Ambiente isolado, reproduzível |
| Validação com cliente | Rita | GitHub Codespaces | Zero setup, acesso via browser |

**Documento detalhado**: [processo_disponibilizacao_versoes.md](processo_disponibilizacao_versoes.md)

---

## 11. Pendências Pós-POC

| Item | Descrição | Prioridade |
|------|-----------|------------|
| Desmembramento do Agente QA | Revisar e dividir o agente QA Engineer em agentes especializados: QA de Produto, Tech Writer e DevOps/SRE | Média |
| Branches QA e Homolog | Criar branches `qa` e `homolog` e configurar deploys automáticos | Alta |
| Aprovações obrigatórias em PRs | Configurar aprovações obrigatórias para PRs em todas as branches | Média |
| ~~Alembic + SQLAlchemy para MySQL/PostgreSQL~~ | ✅ Feito: migrado para PostgreSQL 16 | - |

---

## 12. Perguntas em Aberto

1. **WhatsApp**: Rita usa WhatsApp Business ou pessoal? Tem API configurada?
2. **Catálogos**: Em que formato estão? (PDF, imagens, texto?)
3. **Hospedagem**: Pode rodar local inicialmente ou precisa de servidor?
4. **Notificação**: Como Rita prefere ser notificada do handoff?
