# REQ-004: Escalonamento para Humano (Human Takeover)

**Versão**: 1.6  
**Data**: 2026-05-06  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-004  
**Tipo**: Funcional  
**Categoria**: Operação / Atendimento  
**Solicitante**: vendedor (Inforrel) + requisitos definidos por Beto  

---

## 2. Descrição

O sistema deve identificar quando uma conversa exige intervenção humana e realizar o escalonamento (handoff) de forma segura, garantindo que:

- O cliente saiba que será atendido por uma pessoa quando aplicável
- vendedor (ou outro atendente humano) seja notificada
- O histórico da conversa fique registrado

No POC, o escalonamento deve notificar o vendedor, que responderá ao cliente pelo próprio WhatsApp. O **painel administrativo do REQ-010** dá visibilidade aos escalonamentos pendentes (gestão), mas **não é** usado para responder ao cliente no POC. Em versões posteriores, o atendente poderá responder diretamente pelo painel.

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

- [ ] **REQ-004.1 — Detecção de gatilhos de escalonamento**: O sistema deve detectar gatilhos de escalonamento a partir da mensagem do cliente e do contexto da conversa. Os gatilhos são classificados em duas categorias (detalhadas na seção 4.2):
  - **Explícitos**: o cliente pede diretamente atendimento humano (ver REQ-004.6)
  - **Implícitos**: o sistema infere a necessidade pelo conteúdo/contexto, como insatisfação, análise técnica necessária ou baixa confiança na resposta (ver REQ-004.7, REQ-004.8 e REQ-004.9)

- [ ] **REQ-004.2 — Gerar resumo do contexto e notificar vendedor**: Quando decidir escalar, o sistema deve:
  - Registrar a conversa como “crítica”
  - Gerar um resumo do contexto (para o humano)
  - Notificar o vendedor

- [ ] **REQ-004.3 — Assumir conversa iniciada de forma manual pelo vendedor**: O sistema deve suportar **takeover iniciado pela operadora** (vendedor), independente da existência de gatilhos do lado do cliente:
  - O vendedor pode solicitar assumir uma conversa em andamento a qualquer momento (POC: via procedimento combinado)
  - Ao assumir, o sistema deve aplicar o mesmo tratamento de uma conversa escalada (REQ-004.2 e REQ-004.4): marcar a conversa como em atendimento humano, gerar resumo de contexto e bloquear respostas automáticas
  - Observação: o escalonamento iniciado por **pedido explícito do cliente** é tratado como gatilho explícito (REQ-004.1 + REQ-004.6), não por este requisito

- [ ] **REQ-004.4 — Alterar conversa para estado "em atendimento humano"**: O sistema deve manter, por conversa, um **estado persistente** indicando se ela está em atendimento humano. Esse estado:
  - É **ativado** no momento do handoff (REQ-004.2) ou quando o vendedor assume manualmente (REQ-004.3)
  - É **desativado** apenas quando o humano sinalizar a finalização do atendimento
  - Deve ser consultável pelos demais módulos do sistema (REQ-002, REQ-003) para decidir se podem responder automaticamente

- [ ] **REQ-004.5 — Registro de histórico de escalonamento**: O sistema deve registrar no histórico:
  - Motivo do escalonamento
  - Timestamp
  - Conteúdo do resumo

- [ ] **REQ-004.5A — Pré-qualificação antes do escalonamento**: Antes de escalar para um vendedor (exceto nos casos de escalonamento imediato — REQ-004.6 e REQ-004.7), o sistema deve coletar, no mínimo:
  - Dados de CNPJ (REQ-001)
  - Se é para instalar, entregar ou retirada
  - Se for relógio de ponto:
    - Qual sistema ele usa
    - Qual faixa de funcionários
  - Se for catraca:
    - Qual sistema ele usa
    - Se o modelo que quer é homologado
  
  Esses dados devem ser obtidos pelo fluxo de qualificação (REQ-002).

### 4.2 Gatilhos de Escalonamento

- [ ] **REQ-004.6 — Escalonamento por pedido explícito do cliente**: O sistema deve escalar imediatamente quando o cliente solicitar humano, incluindo variações como:
  - “quero falar com alguém”
  - “falar com vendedor”
  - “falar com humano”
  - “atendente”
  - “pessoa real”

- [ ] **REQ-004.7 — Escalonamento por insatisfação ou reclamação**: O sistema deve escalar quando houver indícios de insatisfação ou reclamação:
  - “reclamação”, “não funciona”, “problema”, “péssimo”, “estou irritado”, etc.

  **Prioridade de fluxo quando se tratar de pós-venda**: se a reclamação for sobre **atraso de entrega, produto que não funciona, suporte ou outra situação de pós-venda** (conforme detecção do REQ-009.1), o fluxo do **REQ-009 prevalece** sobre o escalonamento imediato deste requisito. Nesses casos, o sistema deve:
  - Marcar a conversa como crítica (REQ-009.2 / REQ-007.2)
  - Identificar o orçamento/pedido relacionado (REQ-009.3 a REQ-009.7)
  - Só então escalar com contexto completo (REQ-009.8), passando pelos mecanismos do REQ-004.2

  Para reclamações que **não se enquadrem em pós-venda** (ex: insatisfação genérica durante a qualificação ou consulta), aplicar este REQ-004.7 normalmente: escalar imediatamente.

- [ ] **REQ-004.8 — Escalonamento por análise técnica ou projeto complexo**: O sistema deve escalar quando o tema exigir análise técnica/humana, como:
  - Compatibilidade com software/sistema do cliente
  - Controle de acesso (ex: controle facial em porta): sempre considerar como projeto complexo e escalar/direcionar para um vendedor (exige Ivan/técnico)
  - Cliente grande/projeto complexo
  Para identificar “cliente grande/projeto complexo”, o sistema deve considerar, no mínimo:
  - Quantidade de equipamentos (quando o cliente informar ou quando o sistema conseguir inferir): se quantidade >= 4 (catracas ou relógios), escalar
  - Quantidade de funcionários (quando o cliente informar): se funcionários >= LIMIAR_FUNCIONARIOS (a definir com o vendedor), escalar

- [ ] **REQ-004.9 — Escalonamento por baixa confiança na resposta**: O sistema deve escalar quando não conseguir responder com segurança, por exemplo:
  - Base de conhecimento insuficiente
  - Confiança baixa na resposta
  - Contradições de dados relevantes

### 4.3 Regras de Negócio

- [ ] **REQ-004.10 — Suspensão de respostas automáticas até finalização do atendimento humano**: Enquanto o estado “em atendimento humano” (REQ-004.4) estiver ativo, o sistema **não deve** gerar respostas automáticas para o cliente — nem do fluxo de qualificação (REQ-002), nem da base de conhecimento/RAG (REQ-003). O sistema só retoma respostas automáticas após o humano sinalizar a finalização do atendimento

- [ ] **REQ-004.11 — Comunicação com o cliente no momento do escalonamento**: O sistema deve enviar uma mensagem de transição ao cliente ao iniciar o escalonamento, adequando o tom ao motivo:
  - **Caso geral**: mensagem cordial informando o handoff (ex: “Perfeito, vou acionar um atendente para te ajudar e já te retorno.”)
  - **Escalonamento por reclamação/insatisfação (REQ-004.7)**: tom empático e rápido, **sem debater** o problema com o cliente

### 4.4 Requisitos Não-Funcionais

- [ ] **REQ-004.13 — SLA de notificação ao humano**: Notificação ao humano deve ocorrer em até 10 segundos
- [ ] **REQ-004.14 — Auditabilidade do registro de escalonamento**: Registro do escalonamento deve ser auditável

---

## 5. Notificação ao Humano (POC)

No POC, a notificação deve ser feita via WhatsApp para o vendedor.

### 5.1 Conteúdo mínimo da notificação
- Identificação do cliente (nome/telefone)
- Motivo do escalonamento
- Resumo da conversa
- Última mensagem do cliente

---

## 6. Resumo da Conversa (para o humano)

O sistema deve gerar um resumo curto, orientado à ação, incluindo quando possível:
- Telefone do cliente
- Data/hora da mensagem
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

- [ ] Sem resposta ao cliente pelo painel — vendedor responde pelo WhatsApp (o painel do REQ-010 é apenas para gestão/visualização dos escalonamentos)
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
- Lista de frases gatilho refinada com o vendedor

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
| 06/05/2026 | 1.1 | Refatoração de REQ-004.1 (categorias explícito/implícito de gatilhos) e REQ-004.3 (escopo restrito a takeover iniciado pelo vendedor), eliminando sobreposição entre os dois requisitos | Kika |
| 06/05/2026 | 1.2 | Adição de títulos descritivos a todos os requisitos do documento e refatoração de REQ-004.4 (capacidade: estado persistente) e REQ-004.10 (regra: suspensão de respostas automáticas) para eliminar duplicação semântica | Kika |
| 06/05/2026 | 1.3 | Fusão de REQ-004.5A e REQ-004.10A em um único requisito (REQ-004.5A) com a lista detalhada de campos mínimos para pré-qualificação; REQ-004.10A removido | Kika |
| 06/05/2026 | 1.4 | Fusão de REQ-004.11 (mensagem de transição) e REQ-004.12 (tom empático em reclamação) em um único requisito (REQ-004.11) sobre comunicação com o cliente no momento do escalonamento; REQ-004.12 removido | Kika |
| 12/05/2026 | 1.5 | Atualização das menções a "dashboard" para referenciar o REQ-010 (Painel Administrativo POC), esclarecendo que o painel cobre gestão/visualização de escalonamentos mas que a resposta ao cliente continua pelo WhatsApp no POC | Kika |
| 12/05/2026 | 1.6 | REQ-004.7 enriquecido com regra de prioridade: reclamações de pós-venda (atraso, defeito, suporte) seguem o fluxo do REQ-009 (identificação de orçamento antes do escalonamento); reclamações genéricas continuam escalando imediatamente | Kika |

---

## 13. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
