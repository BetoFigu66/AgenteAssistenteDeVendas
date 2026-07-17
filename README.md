# Assistente de Vendas via WhatsApp com IA

<!-- CLASSIFICACAO: SISTEMA-CAIXAPRETA -->

Sistema de automação de atendimento via WhatsApp usando IA para empresas que fazem vendas pelo canal.

## 👥 Equipe

| Nome | Papel | Observações |
|------|-------|-------------|
| **Beto** | Líder técnico / Desenvolvedor | Coordenação geral |
| **Kika** | Desenvolvedora / Analista de Testes e Requisitos | Experiência com BD, já trabalhou com a Rita |

## 📊 Status do Projeto

| Item | Status |
|------|--------|
| Questionário de requisitos | ✅ Completo |
| Respostas rápidas (RAG) | ✅ Coletadas |
| Arquitetura POC | ✅ Aprovada |
| Backend (FastAPI + SQLAlchemy) | ✅ Implementado |
| Frontend (React + Vite) | ✅ Implementado |
| CI/CD (GitHub Actions) | ✅ Configurado |
| Requisitos formais | 🟡 Em elaboração (16 REQs criados em `artefatos/requisitos_formais/`, várias já implementadas) |
| Histórias de usuário | 🔜 Pendente |

## 🎯 Objetivo

Criar um assistente inteligente que:
- Responde automaticamente quando possível
- Escala para humano quando necessário
- Qualifica leads
- Tira dúvidas técnicas sobre produtos

## 📁 Estrutura do Projeto

```
AgenteAssistenteDeVendas/
├── backend/                    # API FastAPI + SQLAlchemy
│   ├── main.py                 # Endpoints da API
│   ├── models.py               # Modelos SQLAlchemy
│   ├── database.py             # Conexão com banco
│   ├── config.py               # Configurações
│   ├── alembic/                # Migrations do banco
│   ├── requirements.txt        # Dependências Python
│   └── README.md               # 📖 Instruções do backend
├── frontend/                   # React + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/         # Componentes React
│   │   ├── services/           # Serviços de API
│   │   ├── App.jsx             # Componente principal
│   │   └── main.jsx            # Entry point
│   ├── package.json            # Dependências Node.js
│   ├── Dockerfile              # Build de produção
│   └── README.md               # 📖 Instruções do frontend
├── agentes/                    # Agentes de IA para desenvolvimento
│   ├── analista_requisitos.py
│   ├── auxiliar_negocios.py
│   ├── arquiteto_sistemas.py
│   ├── planejador_negocios.py
│   ├── gerente_de_projetos.py
│   ├── qa_engineer.py          # ✨ Novo: Qualidade
│   └── base_agente.py
├── artefatos/
│   ├── analista_de_requisitos/
│   │   ├── questionario_rita_v1.md
│   │   ├── respostas_rita_v1.md
│   │   └── RespostasRapidasWhatsApp.txt
│   └── arquiteto_de_sistemas/
│       ├── arquitetura_poc_v1.md
│       ├── politica_branches.md       # ✨ Novo: Git workflow
│       └── processo_disponibilizacao_versoes.md
├── AnotacoesPessoais/          # 📝 Área pessoal dos colaboradores (não versionada - ver README interno)
├── .github/
│   └── workflows/
│       └── build-and-push.yml  # CI/CD para Docker
├── docker-compose.yml          # Orquestração de containers
├── Dockerfile                  # Build do backend
└── README.md
```

## 🤖 Agentes Disponíveis

### 1. Analista de Requisitos
- Conduz brainstorms
- Documenta requisitos funcionais e não-funcionais
- Cria histórias de usuário

### 2. Auxiliar de Desenvolvimento de Negócios
- Transforma ideias em produtos
- Define MVP e roadmap
- Analisa clientes e mercado

### 3. Arquiteto de Sistemas
- **POC**: Arquitetura de baixo custo para validação
- **Single-Tenant**: Produção para cliente único (Rita/Ivan)
- **Multi-Tenant**: Escalável para múltiplos clientes

### 4. Planejador de Negócios
- Estratégias de precificação
- Planos de marketing
- Análise de concorrência
- Projeções financeiras

### 5. Gerente de Projetos
- Coordena todos os agentes
- Acompanha pendências
- Gera relatórios de status
- Registra atas de reuniões

### 6. QA Engineer ✨
- Revisa documentação e código
- Define cobertura de testes
- Valida fluxo de branches e PRs
- Sugere melhorias de processo

## � Planejamento e documentação de agentes

Arquivos-chave para orientar a evolução dos agentes e facilitar pesquisas futuras:

- `AGENTS.md` — regras do projeto, seleção de agentes e convenções de uso.
- `docs/prompts_agentes.md` — prompts e papéis base para cada agente.
- `agentes/analista_requisitos.md` — fonte da verdade do agente Analista de Requisitos.
- `agentes/plano_evolucao.md` — plano de evolução para o Gerente de Projetos e reportes de sprint.
- `artefatos/gerente_de_projetos/` — templates de report, YAMLs de sprint e relatórios gerados.
- `artefatos/arquiteto_de_sistemas/planos_executados/` — planos estratégicos de RAG e QA e estudos de execução.
- `artefatos/arquiteto_de_sistemas/analise_agentes_vs_skills_vs_harness.md` — comparação de abordagens de agente/skill/harness.
- `AnotacoesPessoais/Beto/pendencia_01.txt` — análise pessoal sobre agentes e migração para formato Codex/skills.
- `AnotacoesPessoais/Beto/planejamento_rag_folders_produtos.md` — planejamento de RAG para dúvidas de produtos.
- `AnotacoesPessoais/files_to_review.yml` — arquivo de revisão que contém observações e itens pendentes de agentes.

> Dica: para encontrar rapidamente o material relacionado a agentes, use `git grep -n "agente"`, `git grep -n "plano"` ou pesquise por `AGENTS.md`.

## �🚀 Como Executar

### Opção 1: Docker (Recomendado)

```bash
# Subir backend + frontend
docker-compose up

# Acessar:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Swagger: http://localhost:8000/docs
```

📖 Instruções detalhadas: [backend/README.md](backend/README.md)

### Opção 2: Desenvolvimento Local

**Backend (Python):**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

**Frontend (Node.js):**
```bash
cd frontend
npm install
npm run dev
```

📖 Instruções detalhadas: [frontend/README.md](frontend/README.md)

### Tecnologias

| Camada | Tecnologia |
|--------|------------|
| **Backend** | FastAPI, SQLAlchemy, Alembic, PostgreSQL 16 |
| **Frontend** | React 18, Vite, TailwindCSS, Lucide |
| **Infra** | Docker, GitHub Actions, ghcr.io |

## 📋 Fluxo de Trabalho

1. **Brainstorm** com Analista de Requisitos
2. **Definição de MVP** com Auxiliar de Negócios
3. **Arquitetura** com Arquiteto de Sistemas
4. **Estratégia Comercial** com Planejador de Negócios
5. **Qualidade** com QA Engineer
6. **Acompanhamento** com Gerente de Projetos

📖 Política de branches: [artefatos/arquiteto_de_sistemas/politica_branches.md](artefatos/arquiteto_de_sistemas/politica_branches.md)

## 📝 Artefatos Gerados

Cada agente gera artefatos em sua pasta específica:
- Requisitos e histórias de usuário
- Definições de MVP e roadmaps
- Documentos de arquitetura (ADRs)
- Modelos de precificação
- Relatórios de status e atas

## 🔗 Cliente Inicial

| Item | Detalhe |
|------|--------|
| **Contato** | Rita (vendas) / Ivan (técnico) |
| **Empresa** | Inforrel |
| **Negócio** | Venda de catracas e relógios de ponto |
| **Fabricantes** | Topdata, Control ID |
| **Canal** | WhatsApp Business (3 números, 3 vendedores) |
| **ERP** | Supersoft |

### Principais Requisitos Identificados

1. **Integração Receita Federal** - buscar dados por CNPJ (prioridade #1 da Rita)
2. **Fluxo conversacional guiado** - coleta estruturada de dados
3. **Dashboard de acompanhamento** - visualizar conversas críticas
4. **Análise de sentimento** - identificar clientes insatisfeitos
5. **Human Takeover** - escalar para humano quando necessário

### Regras de Negócio Críticas

- ❌ **NUNCA prometer prazo** de entrega
- ⚠️ Sempre validar compatibilidade de sistema
- 🚨 Escalar para humano quando cliente pedir

## 📊 Fases do Projeto

| Fase | Objetivo | Estimativa |
|------|----------|------------|
| POC | Validar viabilidade | 15-25h |
| Single-Tenant | Produção para Rita/Ivan | 60-100h |
| Multi-Tenant | Escalar para mais clientes | 200-400h |
