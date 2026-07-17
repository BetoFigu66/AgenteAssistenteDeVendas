# REQ-006: Rastreamento de Orçamentos e Status de Conversão

<!-- CLASSIFICACAO: SISTEMA-CAIXAPRETA -->
<!-- CLASSIFICACAO: IA -->

**Versão**: 1.7  
**Data**: 2026-06-01  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Média  

---

## 1. Identificação do Requisito

**ID**: REQ-006  
**Tipo**: Funcional  
**Categoria**: Pós-venda / Métricas / Funil  
**Solicitante**: Necessidade do produto (visão geral) + operação do vendedor  

---

## 2. Descrição

O sistema deve permitir registrar e acompanhar o ciclo de um **orçamento**, conectando:

- A conversa (WhatsApp)
- O orçamento enviado
- O desfecho (converteu em compra ou não)

No POC, **todas** as transições de status do orçamento são feitas **manualmente pelo vendedor** através do painel administrativo (REQ-010), inclusive a marcação inicial de `rascunho` → `enviado` (o vendedor confirma no painel que o orçamento foi entregue ao cliente). Não há detecção automática de envio nesta fase.

**Escopo do POC — geração do orçamento**: a **geração** propriamente dita do orçamento (cálculo de preços, montagem do PDF/planilha, redacao das condições comerciais) **está fora do escopo do POC** e continua sendo um processo **manual do vendedor**, executado nas ferramentas que ele já usa hoje. O REQ-006 cobre apenas o **rastreamento** desse orçamento dentro do sistema: criar o registro, anexar o conteúdo/referência (REQ-006.4), acompanhar status e auditar transições. Quando a automação da geração entrar em escopo, será tratada por um novo REQ específico.

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

- [ ] **REQ-006.1 — Geração de identificador único do orçamento**: O sistema deve gerar um identificador único de orçamento (`orcamento_id`)

- [ ] **REQ-006.2 — Associação do orçamento à conversa, ao cliente e ao atendimento**: O sistema deve associar cada `orcamento_id` a:
  - `conversa_id`
  - `cliente_id` (telefone)
  - `atendimento_id` (REQ-016) — **obrigatório**: todo orçamento pertence a exatamente um atendimento
  - Timestamp de criação

- [ ] **REQ-006.3 — Múltiplos orçamentos por cliente e por atendimento**: O sistema deve permitir que um cliente tenha mais de um orçamento ao longo do tempo, e que um mesmo **atendimento** (REQ-016) tenha múltiplos orçamentos vinculados (ex.: revisões, alternativas dentro da mesma demanda). A numeração sequencial human-friendly do atendimento (REQ-016.3) substitui a necessidade de numéros sequenciais próprios no orçamento.

- [ ] **REQ-006.4 — Registro do conteúdo do orçamento enviado**: Para cada orçamento que chegar ao status `enviado` (REQ-006.5), o sistema deve persistir uma evidência do que foi entregue ao cliente, de forma que seja possível reconstituir o orçamento futuramente (consulta, auditoria e análise de conversão).
  - **Modos de armazenamento aceitos** (pelo menos um, conforme o caso):
    - **Conteúdo estruturado (inline)**: itens, quantidades, valores unitários, valor total, condições gerais (ex: validade, forma de pagamento) e observações, gravados no banco
    - **Conteúdo livre (inline)**: texto/markdown do orçamento, quando não houver estrutura formal
    - **Referência externa**: caminho do arquivo (PDF/planilha), URL pública (Drive, link compartilhado) ou identificador de documento em outro sistema
  - **Metadados obrigatórios** independentemente do modo:
    - `orcamento_id` (REQ-006.1)
    - Timestamp do envio
    - Canal de envio (ex: WhatsApp, e-mail) — mesmo que no POC seja só WhatsApp
    - Origem do conteúdo (gerado pelo sistema, anexado pelo vendedor, link externo)
  - **Imutabilidade**: o conteúdo registrado não deve ser alterado após o envio. Se houver revisão de orçamento, criar **novo `orcamento_id`** (REQ-006.3 permite múltiplos orçamentos por cliente) e manter o anterior intacto
  - **"Quando aplicável"**: não se exige conteúdo registrado para orçamentos em `rascunho` ou descartados antes do envio. A obrigatoriedade vale a partir da transição para `enviado`
  - **Integração com REQ-005**: o envio gera um evento auditável (ex: `orcamento_enviado`); este requisito define o "anexo" desse evento — a referência ou conteúdo deve ser acessível a partir do evento registrado

### 4.2 Status do Orçamento

- [ ] **REQ-006.5 — Estados possíveis do orçamento**: O sistema deve manter status do orçamento, no mínimo:
  - `rascunho`
  - `enviado`
  - `convertido`
  - `perdido`

- [ ] **REQ-006.6 — Registro de timestamp em cada transição de status**: O sistema deve registrar timestamp de transição de status

- [ ] **REQ-006.7 — Anotação de motivo para orçamento perdido**: O sistema deve permitir anotar motivo (texto curto) quando marcar como `perdido` (ex: preço, prazo, não respondeu)

### 4.3 Atualização Manual pelo vendedor (POC)

- [ ] **REQ-006.8 — Atualização manual de status pelo vendedor**: O sistema deve oferecer um meio para que o vendedor (ou outro usuário com papel equivalente, em versões futuras) atualize manualmente o status de um orçamento. No POC, **toda** transição de status passa por este fluxo manual, incluindo:
  - `rascunho` → `enviado` (o vendedor marca no painel que o orçamento foi efetivamente entregue ao cliente, seja pelo WhatsApp ou por outro canal)
  - `enviado` → `convertido` ou `perdido` (desfechos que acontecem fora do canal automatizado, ex: cliente fechou compra por telefone, desistiu, sumiu)
  - **Quem pode atualizar (POC)**: apenas o vendedor, autenticado no painel administrativo (REQ-010). Identidade do usuário deve ser conhecida para fins de auditoria (REQ-006.10)
  - **Transições permitidas**:
    - `rascunho` → `enviado`
    - `enviado` → `convertido`
    - `enviado` → `perdido`
    - `convertido` ↔ `perdido` apenas via correção explícita (ex: registrada com justificativa); não deve ser usual
    - **Não permitido**: voltar para `rascunho` após `enviado` (use novo orçamento — REQ-006.3)
  - **Validações na atualização**:
    - Orçamento deve estar identificado de forma clara (REQ-006.9)
    - Transição precisa ser válida conforme a tabela acima
    - Se o novo status for `perdido`, o motivo é obrigatório (REQ-006.7)
    - Se o novo status for `convertido`, permitir campo opcional de observação (ex: valor final fechado, data prevista de instalação)
  - **Interface mínima esperada (POC)**:
    - Tela/lista de orçamentos com filtros (REQ-006.11)
    - Ação de "Atualizar status" por orçamento
    - Confirmação antes de aplicar (evitar clique acidental)
  - **Efeitos colaterais**:
    - Registrar timestamp da transição (REQ-006.6)
    - Registrar autoria da alteração (REQ-006.10)
    - Gerar evento auditável em REQ-005 (ex: `orcamento_convertido`, `orcamento_perdido`)
  - **Fora do escopo do POC**: atualização automática via integração com ERP/NF, atualização em lote, fluxo de aprovação por terceiros

- [ ] **REQ-006.9 — Identificação clara do orçamento na atualização manual**: A atualização manual deve exigir identificação clara do orçamento, via:
  - `orcamento_id`, ou
  - seleção do orçamento dentro do histórico do cliente

- [ ] **REQ-006.10 — Auditoria de quem alterou o status e quando**: O sistema deve registrar quem alterou o status (vendedor) e quando

### 4.4 Consulta

- [ ] **REQ-006.11 — Listagem de orçamentos por período, cliente e status**: O sistema deve permitir listar orçamentos por:
  - Período
  - Cliente
  - Status

- [ ] **REQ-006.12 — Visualização consolidada do orçamento**: O sistema deve permitir visualizar, para um orçamento:
  - Conversa relacionada
  - Dados coletados (REQ-002)
  - Conteúdo/referência do orçamento
  - Histórico de status

---

## 5. Integração com Requisitos Existentes

- **REQ-002**: dados coletados durante a qualificação devem poder ser ligados ao orçamento
- **REQ-004**: se houve escalonamento, deve constar no histórico do orçamento (quando aplicável)
- **REQ-005**: eventos `orcamento_criado`, `orcamento_enviado`, `orcamento_convertido`, `orcamento_perdido` devem ser registrados como eventos auditáveis
- **REQ-016**: todo orçamento pertence a um atendimento (`atendimento_id` obrigatório em REQ-006.2). O desfecho do orçamento (`convertido`/`perdido`) é **independente** do estado do atendimento — atendimento permanece `ativo` enquanto o cliente puder voltar a interagir, e ganha/perdida ficam exclusivamente no orçamento (REQ-016.12).

---

## 6. Fluxo (alto nível)

```
1) Conversa qualificada (dados mínimos coletados)
2) Orçamento gerado/enviado (gera orcamento_id)
3) Sistema registra evento de envio
4) Dias depois: vendedor marca manualmente:
   - convertido, ou
   - perdido (com motivo)
5) Sistema registra eventos e timestamps
```

---

## 7. Limitações Aceitas no POC

- [ ] **Geração do orçamento (cálculo, PDF/planilha, condições comerciais) permanece manual** — fora do escopo do POC; será tratada em REQ futuro específico
- [ ] Sem integração automática com ERP/NF para confirmar compra
- [ ] A atualização de status depende do processo do vendedor
- [ ] Relatórios avançados podem ficar para versão posterior

---

## 8. Dependências

### 8.1 Dependências Técnicas
- Persistência de orçamentos e status (PostgreSQL no POC)
- Associações com conversa/cliente

### 8.2 Dependências de Negócio
- Definir como o vendedor irá operar a atualização manual (interface/admin simples vs comando)

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| vendedor não atualiza o status | Média | Médio | Tornar o fluxo simples e rápido |
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
| 12/05/2026 | 1.1 | Adição de títulos descritivos a todos os requisitos do documento | Kika |
| 12/05/2026 | 1.2 | Detalhamento do REQ-006.4: modos de armazenamento aceitos (estruturado, livre, referência externa), metadados obrigatórios, imutabilidade, escopo do "quando aplicável" e integração com REQ-005 | Kika |
| 12/05/2026 | 1.3 | Detalhamento do REQ-006.8: papel autorizado, transições de status permitidas/proibidas, validações, interface mínima, efeitos colaterais (timestamp, autoria, evento em REQ-005) e fora de escopo do POC | Kika |
| 12/05/2026 | 1.4 | Atualização da referência ao painel administrativo no REQ-006.8 para apontar ao REQ-010 (Painel Administrativo POC), recém-criado | Kika |
| 12/05/2026 | 1.5 | Esclarecimento de que no POC **todas** as transições de status do orçamento são manuais pelo vendedor no painel (REQ-010), inclusive `rascunho` → `enviado`; não há detecção automática de envio nesta fase (descrição em §2 e REQ-006.8 atualizados) | Kika |
| 13/05/2026 | 1.6 | Decisão de produto registrada: **geração do orçamento** (cálculo, PDF/planilha, condições comerciais) permanece **manual e fora do escopo do POC**; o REQ-006 cobre apenas rastreamento. Atualizações em §2 (Descrição) e §7 (Limitações Aceitas no POC); será tratada em REQ futuro específico quando entrar em escopo | Kika |
| 01/06/2026 | 1.7 | Vinculação ao novo REQ-016 (Negociações): REQ-006.2 agora exige `negociacao_id` obrigatório em todo orçamento; REQ-006.3 esclarece que múltiplos orçamentos podem pertencer à mesma negociação (revisões/alternativas) e que a numeração human-friendly fica no nível da negociação (REQ-016.3). Seção 5 atualizada com integração ao REQ-016. | Kika |
| 09/06/2026 | 1.8 | Renomeação Negociação → Atendimento (REQ-016 v2.0): REQ-006.2 agora referencia `atendimento_id`; REQ-006.3 atualizado para múltiplos orçamentos por atendimento. §5 reescrita: ganha/perdida do orçamento ficam **independentes** do estado do atendimento (atendimento só conhece `ativo`/`encerrado`). Análise em `analise_renomeacao_negociacao_para_atendimento.md`. | Beto |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
