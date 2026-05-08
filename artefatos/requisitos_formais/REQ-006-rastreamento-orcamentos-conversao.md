# REQ-006: Rastreamento de Orçamentos e Status de Conversão

**Versão**: 1.0  
**Data**: 2026-04-15  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Média  

---

## 1. Identificação do Requisito

**ID**: REQ-006  
**Tipo**: Funcional  
**Categoria**: Pós-venda / Métricas / Funil  
**Solicitante**: Necessidade do produto (visão geral) + operação da Rita  

---

## 2. Descrição

O sistema deve permitir registrar e acompanhar o ciclo de um **orçamento**, conectando:

- A conversa (WhatsApp)
- O orçamento enviado
- O desfecho (converteu em compra ou não)

No POC, a atualização do status de conversão será **manual pela Rita**.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- O processo de venda pode levar dias/meses
- Sem rastreamento, fica difícil saber quais atendimentos geram vendas

**Benefício Esperado**:
- Visibilidade do funil (orçamentos enviados vs convertidos)
- Melhor priorização de follow-up
- Base para métricas e melhorias do atendimento

---

## 4. Critérios de Aceite

### 4.1 Criação e Identificação do Orçamento

- [ ] **REQ-006.1**: O sistema deve gerar um identificador único de orçamento (`orcamento_id`)

- [ ] **REQ-006.2**: O sistema deve associar cada `orcamento_id` a:
  - `conversa_id`
  - `cliente_id` (telefone)
  - Timestamp de criação

- [ ] **REQ-006.3**: O sistema deve permitir que um cliente tenha mais de um orçamento ao longo do tempo

- [ ] **REQ-006.4**: O sistema deve registrar o conteúdo do orçamento enviado (ou referência ao arquivo/link), quando aplicável

### 4.2 Status do Orçamento

- [ ] **REQ-006.5**: O sistema deve manter status do orçamento, no mínimo:
  - `rascunho`
  - `enviado`
  - `convertido`
  - `perdido`

- [ ] **REQ-006.6**: O sistema deve registrar timestamp de transição de status

- [ ] **REQ-006.7**: O sistema deve permitir anotar motivo (texto curto) quando marcar como `perdido` (ex: preço, prazo, não respondeu)

### 4.3 Atualização Manual pela Rita (POC)

- [ ] **REQ-006.8**: O sistema deve permitir que a Rita atualize o status do orçamento de forma manual

- [ ] **REQ-006.9**: A atualização manual deve exigir identificação clara do orçamento, via:
  - `orcamento_id`, ou
  - seleção do orçamento dentro do histórico do cliente

- [ ] **REQ-006.10**: O sistema deve registrar quem alterou o status (Rita) e quando

### 4.4 Consulta

- [ ] **REQ-006.11**: O sistema deve permitir listar orçamentos por:
  - Período
  - Cliente
  - Status

- [ ] **REQ-006.12**: O sistema deve permitir visualizar, para um orçamento:
  - Conversa relacionada
  - Dados coletados (REQ-002)
  - Conteúdo/referência do orçamento
  - Histórico de status

---

## 5. Integração com Requisitos Existentes

- **REQ-002**: dados coletados durante a qualificação devem poder ser ligados ao orçamento
- **REQ-004**: se houve escalonamento, deve constar no histórico do orçamento (quando aplicável)
- **REQ-005**: eventos `orcamento_criado`, `orcamento_enviado`, `orcamento_convertido`, `orcamento_perdido` devem ser registrados como eventos auditáveis

---

## 6. Fluxo (alto nível)

```
1) Conversa qualificada (dados mínimos coletados)
2) Orçamento gerado/enviado (gera orcamento_id)
3) Sistema registra evento de envio
4) Dias depois: Rita marca manualmente:
   - convertido, ou
   - perdido (com motivo)
5) Sistema registra eventos e timestamps
```

---

## 7. Limitações Aceitas no POC

- [ ] Sem integração automática com ERP/NF para confirmar compra
- [ ] A atualização de status depende do processo da Rita
- [ ] Relatórios avançados podem ficar para versão posterior

---

## 8. Dependências

### 8.1 Dependências Técnicas
- Persistência de orçamentos e status (PostgreSQL no POC)
- Associações com conversa/cliente

### 8.2 Dependências de Negócio
- Definir como a Rita irá operar a atualização manual (interface/admin simples vs comando)

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| Rita não atualiza o status | Média | Médio | Tornar o fluxo simples e rápido |
| Orçamento sem referência clara | Média | Médio | Garantir `orcamento_id` e vincular ao cliente |
| Duplicidade de orçamentos | Média | Baixo | Permitir múltiplos por cliente e manter timestamps |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| Modelo de dados e eventos do orçamento | 3h |
| Implementar persistência e associação com conversa | 4h |
| Interface/fluxo simples para atualização manual | 4h |
| Consultas (listar/filtrar) | 3h |
| Testes e ajustes | 3h |
| **Total** | **17h** |

---

## 11. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 15/04/2026 | 1.0 | Criação inicial do requisito | Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
