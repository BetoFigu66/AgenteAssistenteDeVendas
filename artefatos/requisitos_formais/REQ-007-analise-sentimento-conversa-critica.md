# REQ-007: Análise de Sentimento e Classificação de Conversas Críticas

**Versão**: 1.0  
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

- [ ] **REQ-007.1**: O sistema deve analisar mensagens do cliente (e contexto recente) e atribuir uma classificação de sentimento, no mínimo:
  - `positivo`
  - `neutro`
  - `negativo`

- [ ] **REQ-007.2**: O sistema deve classificar a conversa como **crítica** quando:
  - houver sentimento `negativo` persistente, ou
  - houver palavras/frases que indiquem reclamação/insatisfação, ou
  - o cliente pedir humano (gatilhos do REQ-004.6)

- [ ] **REQ-007.3**: O sistema deve registrar a cada atualização de classificação:
  - sentimento atual
  - flag `critica` (sim/não)
  - motivos (texto curto ou tags)
  - timestamp

- [ ] **REQ-007.4**: O sistema deve suportar atualização incremental: a conversa pode mudar de não-crítica para crítica (e vice-versa) conforme novas mensagens

- [ ] **REQ-007.5**: Quando classificar como crítica, o sistema deve acionar o fluxo de escalonamento do REQ-004 quando aplicável

### 4.2 Regras de Negócio

- [ ] **REQ-007.6**: A classificação como crítica deve priorizar segurança: em caso de dúvida, marcar como crítica

- [ ] **REQ-007.7**: A classificação deve considerar a presença de negação e contexto (ex: “não estou irritado” não deve ser interpretado como irritação)

- [ ] **REQ-007.8**: O sistema deve evitar respostas automáticas prolongadas quando a conversa estiver crítica; deve ser breve e orientar escalonamento (alinhado ao REQ-004)

### 4.3 Requisitos Não-Funcionais

- [ ] **REQ-007.9**: Tempo de classificação: < 2 segundos por mensagem, em condições normais
- [ ] **REQ-007.10**: A classificação deve ser auditável (quais sinais levaram à decisão)

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
- [ ] Sem dashboard dedicado; foco em escalonamento e registro

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

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 16/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
