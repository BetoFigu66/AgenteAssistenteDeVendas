# 📊 Relatório de Sprint 1

**Período**: 12/04/2026 → 26/04/2026  
**Gerado em**: 25/04/2026 07:50  
**Duração**: 14 dias

---

## 🎯 Visão Geral do Sprint

Primeiro Sprint do projeto Assistente de Vendas Inforrel:
    - Definir os requisitos funcionais e não funcionais
    - Validar a base técnica (PostgreSQL + Alembic + Docker + FastAPI + React + TailwindCSS + groq (LLM_PROVIDER) + llama-3.1-8b-instant (LLM_MODEL))
    - Implementar interface para testes de interação com o assistente
    - Implementar fluxo de qualidade para processamento de mensagens (triagem de reports). 

---

## ✅ Feito neste Sprint (Done)

### 1. Levantamento dos requisitos
**Responsável**: Kika

### 2. Migração SQLite → PostgreSQL + Sistema de Migrations
**Responsável**: Beto  
Banco de dados criado no SQLite e migrado para PostgreSQL 16 rodando em Docker. Implementado sistema completo de migrations Alembic com ENUMs nativos do Postgres. 

### 3. Tela de simulação de iteração dos clientes
**Responsável**: Beto
Sistema pede dados para identificar o contato e a empresa.

### 4. Consulta de CNPJ
**Responsável**: Beto
Sistema consulta o CNPJ na Receita Federal e retorna os dados da empresa, armazendndo no banco de dados e associando ao contato.
Requisito atendido:  REQ-001: Integração com Receita Federal (CNPJ)

### 5. Workflow de Triagem de Reports de Problema
**Responsável**: Beto  
Sistema completo de captura, categorização, severidade para resolução de problemas em processamentos de mensagens do WhatsApp.


---

## 🎯 Próximo Sprint (Planejado)

Itens priorizados para as próximas 2 semanas (23/04/2026 → 06/05/2026), considerando análise de gaps:

1. **Cadastro de tipos de produtos e produtos** (REQ-002) - Fundamental para fluxo conversacional perguntar modelos
2. **Escalonamento para humano completo** (REQ-004) - Estado "em atendimento humano", notificação, resumo
3. **Base de conhecimento RAG** (REQ-003) - Respostas automáticas FAQ com catálogos
4. **Análise de sentimento e detecção de mal humor** (REQ-007) - Classificação de conversas críticas
5. **Melhorar fluxo de correção de problemas** - Ações a partir de reports de triagem
6. **Página cockpit de acompanhamento de conversas** - Visualização operacional


---

## 📋 Backlog Total Pendente (ATUALIZADO)

Itens do escopo completo que ainda não foram iniciados, organizados por requisito formal:

### REQ-002: Fluxo Conversacional Guiado
1. Fluxo adaptativo com lógica de "próxima pergunta dinâmica"
2. Validação de respostas e esclarecimento pontual
3. Cadastro de tipos de produtos e produtos (movido para Sprint 2)

### REQ-003: Respostas Automáticas com RAG
4. Base de conhecimento RAG completa (FAQ, catálogos, tabelas de preço)
5. Classificação automática FAQ vs qualificação
6. Validação de regras de negócio nas respostas (prazo, compatibilidade)
7. Auditoria de RAG (pergunta, contexto, resposta)

### REQ-004: Escalonamento para Humano
8. Estado "em atendimento humano" persistente
9. Notificação ao atendente (Rita) via WhatsApp
10. Geração de resumo da conversa para humano
11. Gatilhos: cliente pede humano, quantidade >=4, controle de acesso

### REQ-005: Registro de Interações
12. Consulta/filtro de histórico por cliente/período/status
13. Auditoria completa de IA/RAG (prompt, contexto, resposta)
14. Registro de eventos de estado da conversa

### REQ-006: Rastreamento de Orçamentos ⭐ NOVO
15. Modelo de orçamentos com status (rascunho, enviado, convertido, perdido)
16. Associação conversa-orçamento-cliente
17. Atualização manual de status com anotação de motivo
18. Consulta e filtro de orçamentos

### REQ-007: Análise de Sentimento
19. Classificação formal: positivo/neutro/negativo
20. Flag de conversa crítica e persistência
21. Integração com escalonamento

### REQ-008: Integração WhatsApp
22. Webhook Twilio para recebimento de mensagens
23. Envio de mensagens via Twilio API
24. Idempotência (deduplicação de mensagens)
25. Validação de assinatura Twilio
26. Sandbox para testes

### REQ-009: Tratamento de Reclamações Pós-venda ⭐ NOVO
27. Detecção de reclamação (atraso, defeito, suporte)
28. Busca de orçamento por telefone/CNPJ
29. Confirmação com cliente antes de escalar
30. Escalonamento com contexto completo

### Infraestrutura e Futuro
31. Machine Learning para classificação automática de intenções
32. Sistema de notificações em tempo real (WebSocket/SSE)
33. Autenticação e autorização (JWT, roles admin/operador)
34. Deploy em produção com domínio Inforrel
35. Importação/exportação de dados (CSV, Excel)
36. Integração com ERPs
37. Multi-tenancy da aplicação (arquitetura SaaS)

---

## 📊 Análise de Cobertura de Requisitos

**Resultado da análise de gaps**: 1/9 requisitos atendidos, 2 parciais, 6 não atendidos

| Requisito | Status | % Coberto | Gap Principal |
|-----------|--------|-----------|---------------|
| REQ-001: CNPJ | ✅ Atendido | 90% | Validação de formato |
| REQ-002: Fluxo | 🟡 Parcial | 40% | Cadastro produtos, perguntas dinâmicas |
| REQ-003: RAG | 🔴 Não atendido | 10% | Base conhecimento não garantida no escopo |
| REQ-004: Handoff | 🔴 Não atendido | 20% | Notificação, estado, resumo |
| REQ-005: Histórico | 🟡 Parcial | 50% | Auditoria IA, consultas |
| REQ-006: Orçamentos | 🔴 Não atendido | 0% | **ESQUECIDO no backlog** |
| REQ-007: Sentimento | 🔴 Não atendido | 30% | Classificação formal, flag crítica |
| REQ-008: WhatsApp | 🔴 Não atendido | 20% | Webhook, envio, idempotência |
| REQ-009: Pós-venda | 🔴 Não atendido | 0% | **ESQUECIDO no backlog** |

**Requisitos esquecidos no backlog original**: REQ-006 e REQ-009  
**Artefato de análise**: `analise_gaps_requisitos_backlog.md`

---

## 🚨 Bloqueios e Riscos

- 🔴 **Provedor LLM para produção**: Groq (atual) tem rate limits; OpenAI custo elevado. Decisão pendente antes de deploy.
- 🟡 **Container Docker em produção**: Configuração de volumes persistentes para PostgreSQL e backups.

---


*Relatório gerado pelo Agente Gerente de Projetos*  
*Template: Sprint Report v1.0*
