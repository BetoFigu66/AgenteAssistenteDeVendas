# 📋 Análise de Gaps: Requisitos Formais vs Backlog

<!-- CLASSIFICACAO: HISTORICO -->

**Data da análise**: 22/04/2026  
**Analisado por**: Gerente de Projetos  
**Escopo**: Cruzamento dos 9 requisitos formais com o backlog atual

---

## 🎯 Resumo Executivo

| Status | Quantidade | Requisitos |
|--------|------------|------------|
| ✅ **Atendido** | 1 | REQ-001 |
| 🟡 **Parcialmente Atendido** | 2 | REQ-002, REQ-005 |
| 🔴 **Não Atendido** | 6 | REQ-003, REQ-004, REQ-006, REQ-007, REQ-008, REQ-009 |

**Cobertura do backlog**: 6/9 requisitos mencionados (67%)  
**Gaps críticos identificados**: 4

---

## 📊 Matriz de Cruzamento

### REQ-001: Integração com Receita Federal (CNPJ)
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Consulta CNPJ | ✅ | Sprint 1 - "Consulta de CNPJ" implementada |
| Armazenamento dados empresa | ✅ | Modelos criados, integração com contato |
| **Gap encontrado** | ⚠️ | Validação de formato (REQ-001.1, REQ-001.2) não explicitada como concluída |

**Veredito**: ✅ **ATENDIDO** (funcionalidade principal entregue)

---

### REQ-002: Fluxo Conversacional Guiado
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Tela de simulação de iteração | ✅ | Sprint 1 - Feito |
| Identificação de intenção | 🟡 | Existe classificador, mas não fluxo adaptativo completo |
| Perguntas dinâmicas | 🔴 | Não mencionado no backlog |
| Coleta de campos mínimos | 🔴 | Não mencionado explicitamente |
| Cadastro de produtos/tipos | 🟡 | Aparece no "Próximo Sprint", não no backlog total |

**Gaps identificados**:
1. **Falta no backlog**: Cadastro de produtos e tipos (fundamental para perguntas de especificação)
2. **Não mencionado**: Fluxo adaptativo com lógica de "próxima pergunta"
3. **Não mencionado**: Validação de respostas e esclarecimento pontual

**Veredito**: 🟡 **PARCIAL** (base existe, fluxo completo não)

---

### REQ-003: Respostas Automáticas com RAG
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Base de conhecimento | 🟡 | "Próximo Sprint" - "Carregar base de conhecimento (RAG)" |
| Respostas automáticas FAQ | 🔴 | Não mencionado explicitamente no backlog |
| Regras de negócio (prazo, compatibilidade) | 🔴 | Não mencionado |
| Auditoria de RAG | 🔴 | Não mencionado |

**Gaps identificados**:
1. **Só no Próximo Sprint**: Base de conhecimento RAG não está no backlog total pendente
2. **Falta no backlog**: Mecanismo de classificação FAQ vs qualificação
3. **Falta no backlog**: Validação de regras de negócio nas respostas

**Veredito**: 🔴 **NÃO ATENDIDO** (não garantido no escopo)

---

### REQ-004: Escalonamento para Humano
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Detecção de gatilhos | 🟡 | Backlog - "Deteção de mal humor" parcialmente cobre |
| Estado "em atendimento humano" | 🔴 | Não mencionado no backlog |
| Notificação ao humano | 🔴 | Não mencionado no backlog |
| Resumo da conversa | 🔴 | Não mencionado no backlog |
| Cockpit de conversas | 🟡 | "Próximo Sprint" - "página de acompanhamento (cockpit)" |

**Gaps identificados**:
1. **Incompleto**: Apenas "detecção de mal humor" mencionado, sem outros gatilhos (humanos, técnico, quantidade)
2. **Falta no backlog**: Persistência de estado de handoff
3. **Falta no backlog**: Notificação para Rita/atendente
4. **Falta no backlog**: Geração de resumo para humano

**Veredito**: 🔴 **NÃO ATENDIDO** (parcialmente coberto, faltam elementos críticos)

---

### REQ-005: Registro Completo de Interações
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Processamento de mensagens | ✅ | Sprint 1 - Workflow de triagem de reports |
| Histórico de conversas | 🟡 | "Cockpit" no Próximo Sprint parcialmente cobre |
| Auditoria de IA/RAG | 🔴 | Não mencionado no backlog |
| Consulta por cliente/período | 🔴 | Não mencionado no backlog |
| Registro de eventos de estado | 🔴 | Não mencionado explicitamente |

**Gaps identificados**:
1. **Parcial**: Sistema de reports existe, mas não histórico completo de conversas
2. **Falta no backlog**: Auditoria de respostas da IA (prompt, contexto, resposta)
3. **Falta no backlog**: Consulta/filtro do histórico

**Veredito**: 🟡 **PARCIAL** (base técnica existe, funcionalidades de auditoria não)

---

### REQ-006: Rastreamento de Orçamentos
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Modelo de orçamentos | 🔴 | Não mencionado no backlog |
| Status de orçamento | 🔴 | Não mencionado no backlog |
| Atualização manual | 🔴 | Não mencionado no backlog |
| Associação conversa-orçamento | 🔴 | Não mencionado no backlog |

**Gaps identificados**:
1. **❌ CRÍTICO**: Requisito REQ-006 inteiramente ausente do backlog
2. **Impacto**: REQ-009 (pós-venda) depende deste requisito
3. **Impacto**: Funil de vendas não rastreável

**Veredito**: 🔴 **NÃO ATENDIDO** (requisito esquecido no backlog)

---

### REQ-007: Análise de Sentimento
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Classificação sentimento | 🔴 | Não mencionado explicitamente |
| Detecção de mal humor | 🟡 | Backlog - "Deteção de mal humor do cliente" |
| Classificação de conversa crítica | 🔴 | Não mencionado no backlog |
| Integração com escalonamento | 🔴 | Não mencionado no backlog |

**Gaps identificados**:
1. **Parcial**: Apenas "mal humor" mencionado, não análise completa de sentimento
2. **Falta no backlog**: Classificação formal positivo/neutro/negativo
3. **Falta no backlog**: Flag de conversa crítica e persistência

**Veredito**: 🔴 **NÃO ATENDIDO** (parcial, incompleto)

---

### REQ-008: Integração WhatsApp via Twilio
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Webhook Twilio | 🔴 | Não mencionado no backlog |
| Envio de mensagens | 🔴 | Não mencionado no backlog |
| Idempotência | 🔴 | Não mencionado no backlog |
| Validação de assinatura | 🔴 | Não mencionado no backlog |
| Sandbox | 🔴 | Não mencionado no backlog |
| API oficial WhatsApp | 🟡 | Backlog - "Integração com WhatsApp Business API oficial" |

**Gaps identificados**:
1. **Atenção**: Backlog menciona "API oficial", não Twilio especificamente
2. **Falta no backlog**: Webhook, parsing, envio de mensagens
3. **Falta no backlog**: Idempotência e segurança
4. **Decisão pendente**: Twilio vs WhatsApp Business API direta

**Veredito**: 🔴 **NÃO ATENDIDO** (menção genérica no backlog, detalhes faltando)

---

### REQ-009: Tratamento de Reclamações Pós-venda
| Item | Status | Onde está coberto |
|------|--------|-------------------|
| Detecção de reclamação | 🔴 | Não mencionado no backlog |
| Busca de orçamento por telefone | 🔴 | Não mencionado (REQ-006 é pré-requisito) |
| Confirmação com cliente | 🔴 | Não mencionado no backlog |
| Escalonamento com contexto | 🔴 | Não mencionado no backlog |

**Gaps identificados**:
1. **❌ CRÍTICO**: REQ-009 inteiramente ausente do backlog
2. **Pré-requisito faltante**: REQ-006 (orçamentos) é necessário
3. **Impacto**: Pós-venda não coberto no escopo

**Veredito**: 🔴 **NÃO ATENDIDO** (requisito esquecido no backlog)

---

## 🚨 Gaps Críticos a Resolver

### 1. REQ-006 - Rastreamento de Orçamentos (ESQUECIDO)
- **Severidade**: 🔴 Alta
- **Impacto**: Bloca REQ-009, impede funil de vendas
- **Ação**: Adicionar ao backlog: "Implementar modelo e fluxo de orçamentos com status"

### 2. REQ-009 - Reclamações Pós-venda (ESQUECIDO)
- **Severidade**: 🔴 Alta
- **Impacto**: Nenhuma cobertura de pós-venda/suporte
- **Ação**: Adicionar ao backlog: "Fluxo de identificação e escalonamento de reclamações"

### 3. REQ-002 - Cadastro de Produtos (INCOMPLETO)
- **Severidade**: 🟡 Média
- **Impacto**: Fluxo conversacional não pode perguntar modelos/especificações
- **Ação**: Mover do "Próximo Sprint" para backlog com prioridade alta

### 4. REQ-003 - RAG Base de Conhecimento (SÓ NO PRÓXIMO SPRINT)
- **Severidade**: 🟡 Média
- **Impacto**: Respostas automáticas não garantidas no escopo total
- **Ação**: Confirmar se é feature obrigatória para MVP

---

## 📋 Recomendações para Ajuste do Backlog

### Adicionar ao Backlog Total Pendente:

```markdown
## 📋 Backlog Total Pendente (AJUSTADO)

Itens do escopo completo que ainda não foram iniciados:

1. **REQ-006** - Rastreamento de Orçamentos e Status de Conversão
2. **REQ-009** - Tratamento de Reclamações Pós-venda com Identificação de Pedido
3. **REQ-002.2** - Cadastro de Tipos de Produtos e Produtos (fundamental para fluxo)
4. **REQ-002.3** - Fluxo Conversacional Adaptativo (próxima pergunta dinâmica)
5. **REQ-003** - Respostas Automáticas com RAG (FAQ completo)
6. **REQ-004** - Escalonamento para Humano (handoff completo com notificação)
7. **REQ-007** - Análise de Sentimento e Classificação de Conversas Críticas
8. **REQ-008** - Integração WhatsApp via Twilio (webhook + envio)
9. Machine Learning para classificação automática de intenções
10. Sistema de notificações em tempo real (WebSocket/SSE)
11. Autenticação e autorização (JWT, roles admin/operador)
12. Deploy em produção com domínio Inforrel
13. Importação/exportação de dados (CSV, Excel)
14. Integração com ERPs
15. Multi-tenancy da aplicação (arquitetura SaaS)
```

---

## 📈 Priorização Sugerida para Sprint 2

Considerando gaps críticos e dependências:

| Prioridade | Item | Justificativa |
|------------|------|---------------|
| 🔴 Alta | Cadastro de Produtos | Pré-requisito para REQ-002 funcionar |
| 🔴 Alta | Rastreamento de Orçamentos | Habilita REQ-009, métricas de negócio |
| 🔴 Alta | Escalonamento Humano | Segurança, atendimento crítico |
| 🟡 Média | Base de Conhecimento RAG | Automação de respostas |
| 🟡 Média | Análise de Sentimento | Detecção precoce de problemas |
| 🟢 Baixa | Integração Twilio | Já existe simulação, menos urgente |

---

*Análise gerada automaticamente pelo Agente Gerente de Projetos*  
*Método: Cruzamento matricial de requisitos × backlog*
