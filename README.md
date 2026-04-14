# Assistente de Vendas via WhatsApp com IA

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
| Requisitos formais | 🔜 Pendente |
| Histórias de usuário | 🔜 Pendente |
| Desenvolvimento | 🔜 Não iniciado |

## 🎯 Objetivo

Criar um assistente inteligente que:
- Responde automaticamente quando possível
- Escala para humano quando necessário
- Qualifica leads
- Tira dúvidas técnicas sobre produtos

## 📁 Estrutura do Projeto

```
AgenteAssistenteDeVendas/
├── agentes/                    # Agentes de IA para desenvolvimento
│   ├── analista_requisitos.py
│   ├── auxiliar_negocios.py
│   ├── arquiteto_sistemas.py
│   ├── planejador_negocios.py
│   ├── diretor_geral.py
│   ├── orquestrador.py
│   └── base_agente.py
├── artefatos/
│   ├── analista_de_requisitos/
│   │   ├── questionario_rita_v1.md    # Questionário enviado à Rita
│   │   ├── respostas_rita_v1.md       # ✅ Respostas completas
│   │   └── RespostasRapidasWhatsApp.txt # Material para RAG
│   └── arquiteto_de_sistemas/
│       └── arquitetura_poc_v1.md      # ✅ Arquitetura aprovada
├── docs/
│   ├── IdeiaInicialChatGPT.md         # Ideia inicial
│   ├── prompts_agentes.md             # Prompts para usar com IA
│   └── timesheet.md                   # Registro de horas
├── historico/
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

### 5. Diretor Geral
- Coordena todos os agentes
- Acompanha pendências
- Gera relatórios de status
- Registra atas de reuniões

## 🚀 Como Usar

```python
from agentes import OrquestradorAgentes

# Inicializa o sistema
orquestrador = OrquestradorAgentes()

# Lista agentes disponíveis
agentes = orquestrador.listar_agentes()

# Inicializa projeto com pendências
status = orquestrador.inicializar_projeto()

# Acessa agente específico
analista = orquestrador.obter_agente("analista")
prompt = analista.get_prompt_sistema()

# Gera relatório de status
orquestrador.gerar_relatorio_completo()
```

## 📋 Fluxo de Trabalho

1. **Brainstorm** com Analista de Requisitos
2. **Definição de MVP** com Auxiliar de Negócios
3. **Arquitetura** com Arquiteto de Sistemas
4. **Estratégia Comercial** com Planejador de Negócios
5. **Acompanhamento** com Diretor Geral

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
