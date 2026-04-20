# Arquitetura POC - Assistente de Vendas WhatsApp

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
│                   (SQLite / PostgreSQL)                         │
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
| Banco | **SQLite** | Simples, sem servidor, suficiente para POC |
| IA | **OpenAI GPT-4o-mini** | Custo-benefício, boa qualidade |
| WhatsApp | **Evolution API** ou **Twilio Sandbox** | Custo zero para POC |
| Hospedagem | **Local + ngrok** | Grátis, rápido para testar |
| Cache | **Não necessário** | Volume baixo (10-30/dia) |

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
   └── Baixa (<0.7) → Escala para Rita
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

- [ ] Sem painel web para Rita (usa WhatsApp direto)
- [ ] Sem analytics/métricas
- [ ] Sem alta disponibilidade
- [ ] RAG simples (sem embeddings)
- [ ] Apenas um número WhatsApp
- [ ] Sem suporte a áudio/imagens do cliente

---

## 8. Decisões Arquiteturais (ADRs)

### ADR-001: SQLite vs PostgreSQL
**Decisão**: SQLite para POC  
**Motivo**: Simplicidade, sem necessidade de servidor separado  
**Revisão**: Migrar para PostgreSQL na versão single-tenant

### ADR-002: RAG com JSON vs Banco Vetorial
**Decisão**: JSON com keyword matching  
**Motivo**: Catálogo pequeno (~20 produtos), não justifica complexidade  
**Revisão**: Implementar pgvector quando base crescer

### ADR-003: Evolution API vs Twilio
**Decisão**: Twilio Sandbox  
**Motivo**: Custo zero para validação, boa documentação, setup rápido  
**Data da decisão**: 2026-04-19  
**Revisão**: Avaliar Twilio produção ou 360dialog quando sair do POC

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
| Alembic + SQLAlchemy para MySQL/PostgreSQL | Migrar de SQLite para banco de produção | Alta |

---

## 12. Perguntas em Aberto

1. **WhatsApp**: Rita usa WhatsApp Business ou pessoal? Tem API configurada?
2. **Catálogos**: Em que formato estão? (PDF, imagens, texto?)
3. **Hospedagem**: Pode rodar local inicialmente ou precisa de servidor?
4. **Notificação**: Como Rita prefere ser notificada do handoff?
