# REQ-005: Registro Completo de Interações e Histórico de Conversas

**Versão**: 1.6  
**Data**: 2026-05-06  
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
- Suporte a relatórios em versões futuras (o painel do REQ-010 já cobre consulta básica no POC)

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-005.1 — Registro de mensagens recebidas**: O sistema deve registrar todas as mensagens recebidas (cliente → sistema) com timestamp

- [ ] **REQ-005.2 — Registro de mensagens enviadas automaticamente**: O sistema deve registrar todas as mensagens enviadas automaticamente (sistema → cliente) com:
  - Conteúdo enviado
  - Timestamp
  - Identificador do mecanismo (ex: “RAG”, “Fluxo Qualificação”, “Mensagem de transição”) quando aplicável

- [ ] **REQ-005.3 — Registro de eventos de estado da conversa**: O sistema deve registrar cada **transição de estado** de uma conversa como um evento auditavel.

  **Estados possíveis**:
  - `Conversa iniciada` — primeira mensagem recebida abre uma nova conversa
  - `Qualificação em andamento` — sistema identificou intenção de orçamento e iniciou coleta de dados (REQ-002)
  - `Escalonamento acionado` — algum gatilho do REQ-004.1 disparou o handoff
  - `Em atendimento humano` — estado persistente ativado (REQ-004.4); respostas automáticas suspensas (REQ-004.10)
  - `Finalização` — conversa encerrada

  **Cada evento de transição deve registrar**:
  - Tipo do evento (estado novo)
  - Estado anterior
  - Timestamp
  - Ator que disparou a transição (`sistema`, `cliente` ou identificação do humano, ex: `Rita`)
  - Motivo, quando aplicável (ex: para `Escalonamento acionado`, qual gatilho do REQ-004 foi atendido)

  **Transições válidas** (o sistema deve impedir transições fora desta sequência):
  - `Conversa iniciada` → `Qualificação em andamento` ou `Escalonamento acionado` ou `Finalização`
  - `Qualificação em andamento` → `Escalonamento acionado` ou `Finalização`
  - `Escalonamento acionado` → `Em atendimento humano`
  - `Em atendimento humano` → `Finalização`

  **Gatilhos de `Finalização`** (ao menos um dos seguintes):
  - Humano (Rita) sinaliza encerramento da conversa **explicitamente** pelo painel administrativo (REQ-010)
  - Cliente abandona a conversa por período prolongado (conforme REQ-002.22)

  **Observação sobre orçamento enviado**: a marcação de um orçamento como `enviado` (REQ-006.8) **não encerra a conversa por si só**. A conversa pode continuar ativa enquanto o cliente fizer perguntas, negociar ou pedir esclarecimentos sobre o orçamento. A transição para `Finalização` exige sempre uma das duas ações acima (encerramento manual pela Rita ou abandono por inatividade).

  **Consulta em tempo real**: o estado atual de cada conversa deve ser consultável pelos demais módulos (REQ-002, REQ-003) para decidir se podem responder automaticamente, alinhado ao REQ-004.4.

- [ ] **REQ-005.4 — Registro de eventos de escalonamento e erros**: O sistema deve registrar, quando ocorrer:
  - Motivos de escalonamento e resumo (ver REQ-004)
  - Erros relevantes (ex: falha de consulta em API, falha de envio no WhatsApp)

- [ ] **REQ-005.5 — Consulta do histórico**: O sistema deve permitir consulta do histórico por:
  - Número/identificação do cliente
  - Data/período
  - Status (ex: críticas/escalonadas)

### 4.2 Auditoria de Respostas da IA

- [ ] **REQ-005.6 — Auditoria de respostas da IA/RAG**: Para cada resposta automática baseada em IA/RAG, o sistema deve registrar:
  - Pergunta original
  - Contexto recuperado do RAG (trechos/dados utilizados)
  - Prompt/contexto enviado ao modelo (pode ser versão resumida/normalizada)
  - Resposta final enviada ao cliente

### 4.3 Regras de Negócio

- [ ] **REQ-005.7 — Imutabilidade dos registros**: Os registros devem ser imutáveis do ponto de vista do operador (sem edição manual); correções devem ser registradas como novos eventos

- [ ] **REQ-005.8 — Tratamento de dados sensíveis**: O sistema deve evitar registrar e **processar** dados sensíveis além do necessário para a operação comercial.

  **Dados de negócio** (não considerados sensíveis para este sistema — podem ser registrados, indexados e usados normalmente):
  - CNPJ, razão social, nome fantasia
  - Telefone do cliente (chave da conversa)
  - Endereço de entrega/instalação (comercial)
  - E-mail de contato comercial
  - Quantidade de equipamentos / faixa de funcionários
  - Conteúdo das mensagens trocadas (REQ-005.1 e REQ-005.2)

  **Dados sensíveis** (o sistema **não** deve solicitar ativamente, extrair, indexar nem usar em respostas automáticas):
  - CPF e demais documentos de pessoa física (RG, CNH, título de eleitor)
  - Nome completo e endereço residencial de pessoa física
  - Data de nascimento
  - Dados bancários e de pagamento (cartão, conta, PIX, senhas, tokens)
  - Categorias especiais (saúde, religião, orientação política/sexual, biometria, etc.)

  **Tratamento de dados sensíveis em mensagens recebidas**:
  - Se o cliente enviar espontaneamente um dado sensível dentro de uma mensagem, o conteúdo bruto da mensagem pode ficar registrado no histórico (REQ-005.1), pois o registro é auditoria operacional
  - O sistema **não deve** extrair, indexar nem utilizar esses dados em respostas automáticas (REQ-002 / REQ-003)
  - Quando detectar dado sensível em mensagem recebida, o sistema pode acionar escalonamento (REQ-004) caso o atendimento exija tratamento humano específico

### 4.4 Requisitos Não-Funcionais

- [ ] **REQ-005.9 — Confiabilidade do registro**: O registro deve ocorrer de forma confiável: se uma mensagem foi processada, deve existir registro
- [ ] **REQ-005.10 — Desempenho das consultas**: Consultas do histórico devem responder em < 2 segundos para o volume do POC

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
- [ ] Sem relatórios analíticos (gráficos, métricas agregadas, exportações). A consulta básica do histórico é atendida pelo painel administrativo do REQ-010 (telas de histórico de conversas e detalhes do orçamento)

---

## 7. Dependências

### 7.1 Dependências Técnicas
- Banco de dados (PostgreSQL no POC)
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
| 06/05/2026 | 1.1 | REQ-005.3 reescrito com lista de campos por evento, transições válidas, gatilhos de `Finalização` e consulta em tempo real do estado atual | Kika |
| 06/05/2026 | 1.2 | REQ-005.8 reescrito com definição explícita de dados de negócio vs. dados sensíveis e regras de tratamento quando aparecerem em mensagens recebidas | Kika |
| 06/05/2026 | 1.3 | Adição de títulos descritivos a todos os requisitos do documento | Kika |
| 11/05/2026 | 1.4 | REQ-005.3: substituição de "timeout a definir" por referência ao REQ-002.22 (Tratamento de abandono de conversa pelo cliente) | Kika |
| 12/05/2026 | 1.5 | Atualização das menções a "dashboard" para referenciar o REQ-010 (Painel Administrativo POC), distinguindo consulta básica (já coberta) de relatórios analíticos (futuros) | Kika |
| 12/05/2026 | 1.6 | REQ-005.3: refinamento dos gatilhos de `Finalização` — encerramento manual da Rita pelo painel (REQ-010) ou abandono por inatividade (REQ-002.22); esclarecido que a marcação de orçamento como `enviado` (REQ-006.8) não encerra a conversa por si só | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
