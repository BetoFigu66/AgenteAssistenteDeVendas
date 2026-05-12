# REQ-007: Análise de Sentimento e Classificação de Conversas Críticas

**Versão**: 1.3  
**Data**: 2026-04-16  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-007  
**Tipo**: Funcional  
**Categoria**: Qualidade de Atendimento / Monitoramento  
**Solicitante**: Requisito definido por Beto (conversas críticas) + necessidade operacional da Rita  

---

## 2. Descrição

O sistema deve analisar o conteúdo das mensagens ao longo da conversa para:

- Identificar sinais de insatisfação (sentimento negativo)
- Classificar conversas como **críticas** quando houver risco de perda de venda, reclamação ou pedido explícito de humano
- Registrar a classificação e seus motivos no histórico (REQ-005)

A classificação de conversa crítica deve ser utilizada como insumo para o escalonamento humano (REQ-004).

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Conversas com clientes insatisfeitos podem passar despercebidas
- Reclamações e pedidos de humano precisam de resposta rápida

**Benefício Esperado**:
- Resposta mais rápida a conversas sensíveis
- Redução de risco reputacional
- Melhoria contínua do atendimento e da base de conhecimento

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-007.1 — Classificação de sentimento por mensagem**: O sistema deve analisar mensagens do cliente (e contexto recente) e atribuir uma classificação de sentimento, no mínimo:
  - `positivo`
  - `neutro`
  - `negativo`

- [ ] **REQ-007.2 — Critérios para marcar conversa como crítica**: O sistema deve classificar a conversa como **crítica** quando:
  - houver sentimento `negativo` persistente, ou
  - houver palavras/frases que indiquem reclamação/insatisfação, ou
  - o cliente pedir humano (gatilhos do REQ-004.6)

- [ ] **REQ-007.3 — Registro histórico das classificações**: O sistema deve registrar a cada atualização de classificação os campos abaixo, agregando saidas dos REQ-007.1 e REQ-007.2:

  | Campo registrado | Origem |
  |------------------|--------|
  | `sentimento` (atual) | REQ-007.1 |
  | `critica` (flag sim/não) | REQ-007.2 |
  | `motivos` (texto curto ou tags) | REQ-007.1 + REQ-007.2 |
  | `timestamp` | infraestrutura |

  Esses dados devem ser persistidos como evento auditavel no histórico (REQ-005) e ficar acessiveis para consulta posterior (REQ-007.10).

- [ ] **REQ-007.4 — Atualização incremental do estado crítico**: O sistema deve suportar atualização incremental: a conversa pode mudar de não-crítica para crítica (e vice-versa) conforme novas mensagens

- [ ] **REQ-007.5 — Acionamento de escalonamento ao detectar conversa crítica**: Quando classificar como crítica, o sistema deve acionar o fluxo de escalonamento do REQ-004 quando aplicável

### 4.2 Regras de Negócio

- [ ] **REQ-007.6 — Viés de segurança na dúvida (preferir crítica)**: A classificação como crítica deve priorizar segurança: em caso de dúvida, marcar como crítica

- [ ] **REQ-007.7 — Tratamento de negação e contexto**: A classificação deve considerar a presença de negação e contexto (ex: “não estou irritado” não deve ser interpretado como irritação)

- [ ] **REQ-007.8 — Respostas automáticas reduzidas em conversas críticas**: O sistema deve evitar respostas automáticas prolongadas quando a conversa estiver crítica; deve ser breve e orientar escalonamento (alinhado ao REQ-004)

### 4.3 Requisitos Não-Funcionais

- [ ] **REQ-007.9 — Tempo máximo de classificação por mensagem**: Tempo de classificação: < 2 segundos por mensagem, em condições normais
- [ ] **REQ-007.10 — Auditabilidade da classificação**: A classificação deve ser auditável (quais sinais levaram à decisão)

---

## 5. Sinais e Heurísticas (POC)

### 5.1 Lista inicial de sinais

- Reclamação/erro:
  - “não funciona”, “parou”, “defeito”, “erro”, “não consigo”, “não atende”, “não responde”
- Insatisfação:
  - “péssimo”, “horrível”, “decepcionado”, “estou irritado”, “cansado”, “não gostei”
- Ameaça de desistência:
  - “vou comprar em outro lugar”, “vou procurar outro fornecedor”, “desisti”

### 5.2 Regras simples

- Se encontrar 1 sinal forte de reclamação/ameaça, marcar conversa como crítica
- Se encontrar 2 sinais moderados em janela de últimas N mensagens (a definir), marcar como crítica

---

## 6. Integração com Requisitos Existentes

- **REQ-004**: conversa crítica pode acionar escalonamento
- **REQ-005**: registrar classificações e motivos como eventos auditáveis

---

## 7. Limitações Aceitas no POC

- [ ] Modelo de sentimento pode ser simples (regras + IA)
- [ ] Sem dashboard de métricas/indicadores de sentimento; foco em escalonamento (REQ-004) e registro (REQ-005). A exibição de sentimento por conversa pode aparecer nas telas do REQ-010 como informação complementar, mas não é obrigatória no POC

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| Falso positivo (marcar crítica sem necessidade) | Média | Baixo | Ajustar lista de sinais e thresholds |
| Falso negativo (não marcar crítica) | Média | Alto | Priorizar segurança e gatilhos do REQ-004 |
| Linguagem informal/ironia | Média | Médio | Usar IA e revisar casos reais |

---

## 9. Estimativas

| Atividade | Horas |
|-----------|-------|
| Definir sinais e regras iniciais | 2h |
| Implementar classificação (heurística + IA) | 4h |
| Integrar com REQ-004 (escalonamento) | 2h |
| Registrar eventos no histórico (REQ-005) | 2h |
| Testes com conversas reais | 4h |
| **Total** | **14h** |

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 16/04/2026 | 1.0 | Criação inicial do requisito | Kika |
| 12/05/2026 | 1.1 | Atualização da limitação "sem dashboard dedicado" para esclarecer que o REQ-010 (Painel Administrativo POC) pode exibir sentimento por conversa como informação complementar, sem obrigatoriedade no POC | Kika |
| 12/05/2026 | 1.2 | Adição de títulos descritivos a todos os requisitos do documento | Kika |
| 12/05/2026 | 1.3 | REQ-007.3 enriquecido com tabela explicitando a origem de cada campo registrado (REQ-007.1, REQ-007.2 ou infraestrutura) e referências cruzadas a REQ-005 e REQ-007.10 | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 16/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
