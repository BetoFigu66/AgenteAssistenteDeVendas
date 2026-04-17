# REQ-004: Escalonamento para Humano (Human Takeover)

**Versão**: 1.0  
**Data**: 2026-04-15  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-004  
**Tipo**: Funcional  
**Categoria**: Operação / Atendimento  
**Solicitante**: Rita (Inforrel) + requisitos definidos por Beto  

---

## 2. Descrição

O sistema deve identificar quando uma conversa exige intervenção humana e realizar o escalonamento (handoff) de forma segura, garantindo que:

- O cliente saiba que será atendido por uma pessoa quando aplicável
- Rita (ou outro atendente humano) seja notificada
- O histórico da conversa fique registrado

No POC, o escalonamento deve notificar a Rita, que responderá ao cliente pelo próprio WhatsApp. Em versões posteriores, o atendente poderá responder por um dashboard.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Parte das conversas exige análise humana (compatibilidade, cliente grande, controle de acesso)
- Conversas críticas podem ficar escondidas no volume do dia a dia

**Benefício Esperado**:
- Evitar respostas erradas (principalmente sobre compatibilidade e prazos)
- Garantir atendimento humano quando solicitado
- Reduzir risco de perda de oportunidade em clientes críticos

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-004.1**: O sistema deve detectar gatilhos de escalonamento a partir da mensagem do cliente e do contexto da conversa

- [ ] **REQ-004.2**: Quando decidir escalar, o sistema deve:
  - Registrar a conversa como “crítica”
  - Gerar um resumo do contexto (para o humano)
  - Notificar a Rita

- [ ] **REQ-004.3**: O sistema deve suportar escalonamento manual:
  - Se o cliente pedir explicitamente para falar com humano
  - Se a Rita solicitar assumir a conversa (POC: via procedimento combinado)

- [ ] **REQ-004.4**: O sistema deve manter estado “em atendimento humano” para evitar respostas automáticas indevidas após o handoff

- [ ] **REQ-004.5**: O sistema deve registrar no histórico:
  - Motivo do escalonamento
  - Timestamp
  - Conteúdo do resumo

- [ ] **REQ-004.5A**: Antes de escalar para um vendedor, o sistema deve tentar coletar as informações mínimas necessárias para o atendimento humano (alinhado ao fluxo de qualificação do REQ-002), exceto nos casos de escalonamento imediato (REQ-004.6 e REQ-004.7)

### 4.2 Gatilhos de Escalonamento

- [ ] **REQ-004.6**: O sistema deve escalar imediatamente quando o cliente solicitar humano, incluindo variações como:
  - “quero falar com alguém”
  - “falar com vendedor”
  - “falar com humano”
  - “atendente”
  - “pessoa real”

- [ ] **REQ-004.7**: O sistema deve escalar quando houver indícios de insatisfação ou reclamação:
  - “reclamação”, “não funciona”, “problema”, “péssimo”, “estou irritado”, etc.

- [ ] **REQ-004.8**: O sistema deve escalar quando o tema exigir análise técnica/humana, como:
  - Compatibilidade com software/sistema do cliente
  - Controle de acesso (ex: controle facial em porta): sempre considerar como projeto complexo e escalar/direcionar para um vendedor (exige Ivan/técnico)
  - Cliente grande/projeto complexo
  Para identificar “cliente grande/projeto complexo”, o sistema deve considerar, no mínimo:
  - Quantidade de equipamentos (quando o cliente informar ou quando o sistema conseguir inferir): se quantidade >= 4 (catracas ou relógios), escalar
  - Quantidade de funcionários (quando o cliente informar): se funcionários >= LIMIAR_FUNCIONARIOS (a definir com a Rita), escalar

- [ ] **REQ-004.9**: O sistema deve escalar quando não conseguir responder com segurança, por exemplo:
  - Base de conhecimento insuficiente
  - Confiança baixa na resposta
  - Contradições de dados relevantes

### 4.3 Regras de Negócio

- [ ] **REQ-004.10**: Após escalonamento, o sistema não deve continuar respondendo automaticamente para o cliente, a menos que o humano finalize o atendimento

- [ ] **REQ-004.10A**: Quando o escalonamento não for imediato (ou seja, não acionado por pedido explícito de humano ou reclamação/insatisfação), o sistema deve coletar, no mínimo:
  - Dados de CNPJ (REQ-001)
  - Se é para instalar, entregar ou retirada
  - Se for relógio de ponto:
    - Qual sistema ele usa
    - Qual faixa de funcionários
  - Se for catraca:
    - Qual sistema ele usa
    - Se o modelo que quer é homologado

- [ ] **REQ-004.11**: O sistema deve usar mensagem de transição adequada ao cliente, por exemplo:
  - “Perfeito, vou acionar um atendente para te ajudar e já te retorno.”

- [ ] **REQ-004.12**: Se o escalonamento ocorrer por reclamação/insatisfação, o sistema deve ser empático e rápido, sem debater

### 4.4 Requisitos Não-Funcionais

- [ ] **REQ-004.13**: Notificação ao humano deve ocorrer em até 10 segundos
- [ ] **REQ-004.14**: Registro do escalonamento deve ser auditável

---

## 5. Notificação ao Humano (POC)

No POC, a notificação deve ser feita via WhatsApp para a Rita.

### 5.1 Conteúdo mínimo da notificação
- Identificação do cliente (nome/telefone)
- Motivo do escalonamento
- Resumo da conversa
- Última mensagem do cliente

---

## 6. Resumo da Conversa (para o humano)

O sistema deve gerar um resumo curto, orientado à ação, incluindo quando possível:
- Intenção do cliente
- Produto(s) de interesse
- Dados já coletados (CNPJ, localidade, quantidade, etc.)
- Pendências (o que falta perguntar/confirmar)
- Motivo do escalonamento

---

## 7. Fluxo de Escalonamento (alto nível)

```
1) Mensagem do cliente
2) Classificação / análise de risco
3) Se gatilho:
   3.1 Marcar conversa como crítica
   3.2 Gerar resumo
   3.3 Notificar humano
   3.4 Enviar mensagem de transição ao cliente
   3.5 Bloquear respostas automáticas para esta conversa
4) Humano assume e responde pelo WhatsApp (POC)
```

---

## 8. Limitações Aceitas no POC

- [ ] Sem dashboard (Rita responde pelo WhatsApp)
- [ ] Sem fila de atendimento (apenas notificação)
- [ ] Sem roteamento entre múltiplos atendentes

---

## 9. Dependências

### 9.1 Dependências Técnicas
- Integração com WhatsApp para notificação
- Persistência de estado da conversa (ex: “handoff ativo”)
- IA para resumo de conversa

### 9.2 Dependências de Negócio
- Definição do canal de notificação (WhatsApp e número)
- Lista de frases gatilho refinada com a Rita

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| Escalonar demais e perder automação | Média | Médio | Ajustar gatilhos e revisar logs |
| Escalonar de menos e responder errado | Média | Alto | Priorizar segurança; regra “não inventar” |
| Humano não responder rápido | Média | Médio | Mensagem de expectativa e SLA interno |

---

## 11. Estimativas

| Atividade | Horas |
|-----------|-------|
| Definir gatilhos iniciais (frases + regras) | 2h |
| Implementar detecção de escalonamento | 3h |
| Implementar estado “em atendimento humano” | 2h |
| Implementar resumo para humano | 3h |
| Implementar notificação (POC) | 3h |
| Testes com conversas reais | 4h |
| **Total** | **17h** |

---

## 12. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 15/04/2026 | 1.0 | Criação inicial do requisito | Kika |

---

## 13. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
