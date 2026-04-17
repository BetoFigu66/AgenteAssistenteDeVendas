# REQ-005: Registro Completo de Interações e Histórico de Conversas

**Versão**: 1.0  
**Data**: 2026-04-15  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-005  
**Tipo**: Funcional  
**Categoria**: Auditoria / Observabilidade / Dados  
**Solicitante**: Requisito definido por Beto + necessidade operacional da Rita  

---

## 2. Descrição

O sistema deve registrar todas as interações com clientes via WhatsApp, mantendo histórico completo e auditável, incluindo:

- Mensagens recebidas do cliente
- Mensagens enviadas pelo sistema (IA/RAG)
- Mensagens enviadas por humano (no POC, fora do sistema; registrar quando possível)
- Eventos internos relevantes (ex: escalonamento, mudança de estado, erros)

O objetivo é permitir rastreabilidade, revisão de conversas críticas e melhoria contínua do atendimento.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Conversas ficam dispersas no WhatsApp e não viram base de aprendizado
- Falta histórico consolidado para auditoria e para entender o que deu certo/errado

**Benefício Esperado**:
- Auditoria e rastreabilidade de decisões do sistema
- Base para melhoria de prompts, RAG e gatilhos de escalonamento
- Suporte a relatórios e dashboard em versões futuras

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-005.1**: O sistema deve registrar todas as mensagens recebidas (cliente → sistema) com timestamp

- [ ] **REQ-005.2**: O sistema deve registrar todas as mensagens enviadas automaticamente (sistema → cliente) com:
  - Conteúdo enviado
  - Timestamp
  - Identificador do mecanismo (ex: “RAG”, “Fluxo Qualificação”, “Mensagem de transição”) quando aplicável

- [ ] **REQ-005.3**: O sistema deve registrar eventos de estado da conversa:
  - Conversa iniciada
  - Qualificação em andamento
  - Escalonamento acionado
  - “Em atendimento humano”
  - Finalização (quando aplicável)

- [ ] **REQ-005.4**: O sistema deve registrar, quando ocorrer:
  - Motivos de escalonamento e resumo (ver REQ-004)
  - Erros relevantes (ex: falha de consulta em API, falha de envio no WhatsApp)

- [ ] **REQ-005.5**: O sistema deve permitir consulta do histórico por:
  - Número/identificação do cliente
  - Data/período
  - Status (ex: críticas/escalonadas)

### 4.2 Auditoria de Respostas da IA

- [ ] **REQ-005.6**: Para cada resposta automática baseada em IA/RAG, o sistema deve registrar:
  - Pergunta original
  - Contexto recuperado do RAG (trechos/dados utilizados)
  - Prompt/contexto enviado ao modelo (pode ser versão resumida/normalizada)
  - Resposta final enviada ao cliente

### 4.3 Regras de Negócio

- [ ] **REQ-005.7**: Os registros devem ser imutáveis do ponto de vista do operador (sem edição manual); correções devem ser registradas como novos eventos

- [ ] **REQ-005.8**: O sistema deve evitar registrar dados sensíveis além do necessário; caso registre, deve ser para fins operacionais e auditáveis

### 4.4 Requisitos Não-Funcionais

- [ ] **REQ-005.9**: O registro deve ocorrer de forma confiável: se uma mensagem foi processada, deve existir registro
- [ ] **REQ-005.10**: Consultas do histórico devem responder em < 2 segundos para o volume do POC

---

## 5. Modelo de Dados (alto nível)

### 5.1 Entidades mínimas

- **Conversa**
  - `conversa_id`
  - `cliente_id` (telefone)
  - `canal` (whatsapp)
  - `status` (normal, qualificação, escalonada, em_atendimento_humano)
  - `criada_em`, `atualizada_em`

- **Mensagem/Evento**
  - `evento_id`
  - `conversa_id`
  - `tipo` (mensagem_cliente, mensagem_sistema, evento_sistema, erro)
  - `conteudo`
  - `timestamp`
  - `metadata` (json)

### 5.2 Metadados recomendados
- `origem` (cliente/sistema/humano)
- `intent` detectada (quando aplicável)
- `tags` (ex: “catalogo”, “preco”, “prazo”, “reclamacao”)
- `ai_model` (quando aplicável)

---

## 6. Limitações Aceitas no POC

- [ ] Registro de mensagens do humano (Rita) pode não ser completo se ela responder diretamente no WhatsApp sem passar pelo sistema
- [ ] Sem dashboard de visualização (consulta pode ser via endpoint/admin simples)

---

## 7. Dependências

### 7.1 Dependências Técnicas
- Banco de dados (SQLite no POC)
- Camada de persistência para conversas/eventos

### 7.2 Dependências de Negócio
- Definir quais campos são considerados sensíveis e devem ser evitados/mascarados

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| Crescimento do volume de dados | Baixa (POC) | Baixo | Rotina de retenção/compactação (futuro) |
| Falha de registro em exceções | Média | Alto | Registrar antes/depois de enviar e usar fila simples (futuro) |
| Excesso de dados sensíveis armazenados | Média | Médio | Revisar campos e mascarar dados |

---

## 9. Estimativas

| Atividade | Horas |
|-----------|-------|
| Definir modelo de dados e eventos mínimos | 3h |
| Implementar persistência de conversas e eventos | 5h |
| Implementar logs/auditoria de IA/RAG | 4h |
| Implementar consulta simples por cliente/período/status | 4h |
| Testes e validação com conversas reais | 4h |
| **Total** | **20h** |

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 15/04/2026 | 1.0 | Criação inicial do requisito | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
