"""
Agente Arquiteto de Sistemas
Responsavel por propor arquiteturas em diferentes niveis de maturidade do sistema.

A fonte da verdade da identidade e do prompt deste agente esta em:
    agentes/arquiteto_sistemas.md

E o indice de diretrizes operacionais (A01-A0N, com pointers para os .md tematicos) em:
    artefatos/arquiteto_de_sistemas/diretrizes.md
"""
from pathlib import Path

from .base_agente import BaseAgente


class ArquitetoSistemas(BaseAgente):
    """
    Arquiteto de Sistemas - Propõe arquiteturas para diferentes fases do projeto.
    
    Responsabilidades:
    - Arquitetura POC (baixo custo, validação)
    - Arquitetura Single-tenant (cliente único: Rita/Ivan)
    - Arquitetura Multi-tenant (escalável)
    - Decisões técnicas e trade-offs
    - Diagramas e documentação técnica
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Arquiteto de Sistemas",
            papel="Propor arquiteturas adequadas para cada fase do projeto",
            projeto_root=projeto_root
        )
        self.arquiteturas = {
            "poc": {
                "nome": "POC - Prova de Conceito",
                "objetivo": "Validar viabilidade técnica com custo mínimo",
                "caracteristicas": ["Simples", "Baixo custo", "Rápido deploy"]
            },
            "single_tenant": {
                "nome": "Single-Tenant - Cliente Único",
                "objetivo": "Atender Rita/Ivan com qualidade de produção",
                "caracteristicas": ["Estável", "Monitorado", "Customizável"]
            },
            "multi_tenant": {
                "nome": "Multi-Tenant - Escalável",
                "objetivo": "Atender múltiplos clientes de forma isolada",
                "caracteristicas": ["Escalável", "Isolamento", "Self-service"]
            }
        }
    
    PROMPT_MD = "agentes/arquiteto_sistemas.md"
    DIRETRIZES_MD = "artefatos/arquiteto_de_sistemas/diretrizes.md"

    def get_prompt_sistema(self) -> str:
        """
        Le o prompt de sistema concatenando:
          1. agentes/arquiteto_sistemas.md (identidade — fonte da verdade)
          2. artefatos/arquiteto_de_sistemas/diretrizes.md (indice A01-A0N)
        """
        prompt_path = Path(self.projeto_root) / self.PROMPT_MD
        if prompt_path.exists():
            identidade = prompt_path.read_text(encoding="utf-8")
        else:
            identidade = (
                "Voce e um Arquiteto de Sistemas senior do projeto Assistente de Vendas. "
                "Proponha arquiteturas adequadas para cada fase (POC, single-tenant, multi-tenant), "
                "documente decisoes (ADRs) e justifique trade-offs entre custo, complexidade e funcionalidade. "
                "(Prompt completo em agentes/arquiteto_sistemas.md nao encontrado.)"
            )

        diretrizes_path = Path(self.projeto_root) / self.DIRETRIZES_MD
        diretrizes = (
            diretrizes_path.read_text(encoding="utf-8")
            if diretrizes_path.exists()
            else "(nenhuma diretriz registrada ainda)"
        )
        return f"{identidade}\n\n---\n\n{diretrizes}"

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "arquiteturas": self.arquiteturas,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias()
        }
    
    def propor_arquitetura_poc(self):
        """Propõe arquitetura para POC."""
        conteudo = """# Arquitetura POC - Prova de Conceito

## Objetivo
Validar a viabilidade técnica com custo mínimo e tempo reduzido.

## Diagrama Simplificado
```
[WhatsApp Business]
        ↓
[Webhook - ngrok/localhost]
        ↓
[FastAPI - Local/Railway]
        ↓
[Groq API + Embeddings]
        ↓
[PostgreSQL local + pgvector]
```

## Stack Tecnológica

| Componente | Tecnologia | Custo |
|------------|------------|-------|
| Backend | FastAPI (Python) | Grátis |
| Banco de dados | PostgreSQL 16 + pgvector | Grátis |
| IA | Groq + OpenAI embeddings | ~$10-20/mês |
| WhatsApp | Twilio Sandbox | Grátis (dev) |
| Hospedagem | Local + ngrok | Grátis |

## Funcionalidades POC
- [x] Receber mensagens do WhatsApp
- [x] Processar com IA (Groq + embeddings)
- [x] Responder automaticamente
- [x] Fallback para humano (palavra-chave)
- [x] RAG leve via PostgreSQL/pgvector
- [ ] Sem painel web

## Limitações Aceitas
- Sem alta disponibilidade
- Sem monitoramento
- Conhecimento limitado com RAG leve
- Apenas um número WhatsApp
- Sem controle de acesso por login/senha

## Custos Mensais Estimados
- IA (Groq + embeddings): ~$10-20
- Twilio (produção): ~$15 + uso
- **Total POC**: ~$25-35/mês
"""
        return self.criar_artefato("arquitetura_poc.md", conteudo, tipo="arquitetura")

    def propor_arquitetura_single_tenant(self):
        """Propõe arquitetura para cliente único."""
        conteudo = """# Arquitetura Single-Tenant - Cliente Único (Rita/Ivan)

## Objetivo
Sistema de produção estável para atender um cliente com qualidade.

## Diagrama
```
[WhatsApp Business API]
        ↓
[API Gateway / Load Balancer]
        ↓
[FastAPI Backend]
    ├── [Orquestrador de Conversa]
    ├── [Motor de IA + RAG]
    └── [Gerenciador de Handoff]
        ↓
[PostgreSQL + pgvector]
        ↓
[Redis (cache/sessões)]
        ↓
[Painel Web (React/Vite)]
```

## Stack Tecnológica

| Componente | Tecnologia | Custo Estimado |
|------------|------------|----------------|
| Backend | FastAPI | - |
| Banco | PostgreSQL (Supabase/Railway) | $0-25/mês |
| Vetores | pgvector | Incluso |
| Cache | Redis (Upstash) | $0-10/mês |
| IA | Groq + OpenAI embeddings | $20-50/mês |
| WhatsApp | Twilio/360dialog | $15 + uso |
| Hospedagem | Railway/Render | $5-20/mês |
| Frontend | React + Vite | $0-20/mês |

## Funcionalidades
- [x] Receber/enviar mensagens WhatsApp
- [x] IA com RAG (base de conhecimento)
- [x] Classificação de intenção
- [x] Score de confiança
- [x] Handoff inteligente para humano
- [x] Painel para vendedor
- [x] Histórico de conversas
- [x] Métricas básicas

## Componentes Detalhados

### 1. Base de Conhecimento (RAG)
- Produtos (catracas, modelos, preços)
- FAQ técnico
- Políticas comerciais
- Embeddings com OpenAI

### 2. Orquestrador de Conversa
- Estado da conversa
- Contexto do cliente
- Regras de negócio

### 3. Motor de Decisão (Handoff)
- Cliente pediu humano
- Baixa confiança da IA
- Negociação de preço
- Reclamação/problema

## Estimativa de Tempo
**60-100 horas** de desenvolvimento

## Custos Mensais Estimados
- Infraestrutura: ~$50-100
- APIs (OpenAI + WhatsApp): ~$50-100
- **Total**: ~$100-200/mês
"""
        return self.criar_artefato("arquitetura_single_tenant.md", conteudo, tipo="arquitetura")

    def propor_arquitetura_multi_tenant(self):
        """Propõe arquitetura multi-tenant escalável."""
        conteudo = """# Arquitetura Multi-Tenant - Escalável

## Objetivo
Plataforma SaaS para atender múltiplos clientes com isolamento e escalabilidade.

## Diagrama
```
[Múltiplos WhatsApp Business]
            ↓
[API Gateway + Rate Limiting]
            ↓
[Load Balancer]
            ↓
[FastAPI Backend (múltiplas instâncias)]
    ├── [Tenant Router]
    ├── [Orquestrador de Conversa]
    ├── [Motor de IA + RAG por tenant]
    └── [Billing/Usage Tracking]
            ↓
[PostgreSQL (schemas por tenant)]
            ↓
[Redis Cluster]
            ↓
[Queue (RabbitMQ/SQS)]
            ↓
[Workers Assíncronos]
            ↓
[Painel Admin Multi-tenant]
```

## Stack Tecnológica

| Componente | Tecnologia | Observação |
|------------|------------|------------|
| Backend | FastAPI + Celery | Escalável |
| Banco | PostgreSQL (RDS/Supabase) | Schema por tenant |
| Vetores | pgvector / Pinecone | Isolamento |
| Cache | Redis Cluster | Sessões/cache |
| Queue | RabbitMQ / SQS | Processamento async |
| IA | Groq + OpenAI embeddings | Billing por tenant |
| WhatsApp | 360dialog / Meta direto | Multi-número |
| Hospedagem | AWS/GCP/Railway | Auto-scaling |
| Frontend | React + Vite | Multi-tenant |
| Auth | Auth0 / Supabase Auth | SSO ready |

## Funcionalidades Adicionais
- [x] Onboarding self-service
- [x] Billing e cobrança
- [x] Analytics por tenant
- [x] Customização de IA por cliente
- [x] API pública
- [x] Webhooks
- [x] White-label (opcional)
- [x] SLA e monitoramento

## Padrões de Isolamento
1. **Dados**: Schema por tenant no PostgreSQL
2. **Cache**: Prefixo de tenant no Redis
3. **Arquivos**: Bucket/pasta por tenant
4. **IA**: Contexto isolado por tenant

## Estimativa de Tempo
**200-400 horas** de desenvolvimento

## Custos Mensais Estimados (base)
- Infraestrutura: ~$200-500
- APIs: Proporcional ao uso
- **Break-even**: ~10-20 clientes pagantes
"""
        return self.criar_artefato("arquitetura_multi_tenant.md", conteudo, tipo="arquitetura")

    def criar_adr(self, titulo: str, contexto: str, decisao: str, consequencias: list):
        """Cria um Architecture Decision Record (ADR)."""
        from datetime import datetime
        
        conteudo = f"""# ADR: {titulo}

**Data**: {datetime.now().strftime('%Y-%m-%d')}
**Status**: Proposta

## Contexto
{contexto}

## Decisão
{decisao}

## Consequências

### Positivas
"""
        for cons in consequencias:
            if cons.get('tipo') == 'positiva':
                conteudo += f"- {cons.get('descricao')}\n"
        
        conteudo += "\n### Negativas\n"
        for cons in consequencias:
            if cons.get('tipo') == 'negativa':
                conteudo += f"- {cons.get('descricao')}\n"
        
        nome_arquivo = f"ADR_{titulo.replace(' ', '_')[:30]}.md"
        return self.criar_artefato(nome_arquivo, conteudo, tipo="adr")
