# REQ-016: Identificação e Numeração de Negociações por Cliente

**Versão**: 1.0  
**Data**: 2026-06-01  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Média  

---

## 1. Identificação do Requisito

**ID**: REQ-016  
**Tipo**: Funcional  
**Categoria**: Modelo de Dados / Gestão Comercial  
**Solicitante**: vendedor (Inforrel)  

---

## 2. Descrição

O sistema deve formalizar o conceito de **Negociação** como **agrupador comercial** entre uma conversa (REQ-005) e um ou mais orçamentos (REQ-006) gerados em torno da mesma intenção de compra do cliente. Cada negociação recebe um **número sequencial por cliente** (1, 2, 3, ...), tornando a referência operacional do vendedor simples e estável (ex.: "Negociação #3 da ACME").

Hoje a tabela `negociacoes` já existe na base de dados, mas seu papel não está formalizado em nenhum requisito. Este REQ resolve essa dívida documental e adiciona a numeração sequencial pedida pelo vendedor.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- A tabela `negociacoes` existe no banco mas não tem requisito que descreva seu papel, ciclo de vida ou regras de criação.
- Quando o cliente pede uma revisão de orçamento (ex.: trocar de catraca pedestal para giratória), o sistema cria um novo `orcamento_id` (REQ-006.3), mas perde a noção de que "as duas cotações são da mesma compra".
- O vendedor não tem uma referência curta e estável para citar nas conversas internas ("a negociação #5 da ACME" é mais útil que `orcamento_id` 7a2f8...).

**Benefício Esperado**:
- Agrupar orçamentos relacionados a uma mesma intenção de compra.
- Dar ao vendedor uma referência curta e sequencial por cliente.
- Permitir métricas mais limpas (ex.: "conversão por negociação" em vez de "conversão por orçamento", que infla com revisões).
- Eliminar dívida documental sobre a tabela `negociacoes` que já existe.

**Feedback do vendedor (Rita)**: "quando um cliente solicita um orçamento, este receberia um número sequencial (começa com 1). Quando ele pede outro, seria o número 2... no painel seria legal exibir o número atual da negociação."

---

## 4. Critérios de Aceite

### 4.1 Definição e Estrutura

- [ ] **REQ-016.1 — Definição de Negociação**: Uma **Negociação** é a entidade comercial que agrupa, para um mesmo cliente (`telefone`), os elementos relacionados a uma intenção de compra:
  - Uma ou mais **conversas** (REQ-005) — uma negociação pode atravessar mais de uma conversa quando há reengajamento após abandono
  - Zero ou mais **orçamentos** (REQ-006) — uma negociação pode ter zero orçamentos (qualificação ainda em curso) ou múltiplos (revisões, alternativas)
  - Um **ciclo de vida próprio** (REQ-016.4)

- [ ] **REQ-016.2 — Identificadores da Negociação**: Cada negociação tem dois identificadores:
  - `negociacao_id`: identificador único global (UUID ou sequencial interno), usado em chaves estrangeiras e integrações
  - `numero_negociacao_cliente`: inteiro sequencial **por cliente**, começando em 1, usado para exibição ao vendedor e ao cliente

  Os dois coexistem: `negociacao_id` é a referência técnica; `numero_negociacao_cliente` é a referência humana.

- [ ] **REQ-016.3 — Numeração sequencial por cliente**: O `numero_negociacao_cliente` deve ser:
  - Inteiro positivo iniciando em **1** para a primeira negociação de cada cliente
  - **Incrementado em +1** a cada nova negociação criada para o mesmo cliente, independentemente do desfecho das anteriores (negociações perdidas/abandonadas continuam contando)
  - **Único** por par `(telefone, numero_negociacao_cliente)` — garantido por índice único no banco
  - **Imutável** após criação — não muda mesmo se uma negociação for cancelada/excluída logicamente

  **Mecanismo de geração** (referência de implementação):
  ```sql
  numero_negociacao_cliente = COALESCE(
      (SELECT MAX(numero_negociacao_cliente) FROM negociacoes WHERE telefone = :telefone),
      0
  ) + 1
  ```
  No POC, race conditions não são preocupação (vendedor único, baixa concorrência). Em produção: usar advisory lock por `telefone` ou sequência dedicada se necessário.

### 4.2 Ciclo de Vida

- [ ] **REQ-016.4 — Estados possíveis da negociação**: Uma negociação deve ter um dos seguintes estados:
  - `aberta` — em curso, recebendo mensagens, qualificação ou orçamentos
  - `ganha` — cliente confirmou compra (pelo menos um orçamento dela está em `convertido` no REQ-006)
  - `perdida` — cliente declinou ou todos os orçamentos foram `perdido` no REQ-006
  - `abandonada` — cliente parou de responder e a janela de reengajamento esgotou (alinhado a REQ-002.22)

  **Transições válidas**:
  - `aberta` → `ganha`, `perdida`, `abandonada`
  - `abandonada` → `aberta` (cliente voltou e o vendedor decidiu retomar a mesma negociação — ver REQ-016.7)
  - Demais transições requerem correção manual com justificativa

- [ ] **REQ-016.5 — Timestamps de transição**: Para cada mudança de estado, registrar:
  - Estado anterior e novo
  - Timestamp da transição
  - Quem alterou (sistema automático ou vendedor) — análogo a REQ-006.10

### 4.3 Regras de Criação

- [ ] **REQ-016.6 — Criação automática na primeira intenção de compra**: Quando o sistema detectar **intenção de compra/orçamento** (REQ-002.1) e o cliente **não tiver negociação aberta**, o sistema deve **criar automaticamente** uma nova negociação:
  - Estado inicial: `aberta`
  - `numero_negociacao_cliente` gerado conforme REQ-016.3
  - Associada à conversa em andamento (REQ-005)

- [ ] **REQ-016.7 — Comportamento quando já existe negociação aberta**: Se o cliente já tiver uma negociação no estado `aberta` quando chegar uma nova intenção de compra:
  - **POC (padrão)**: o sistema **não cria** uma negociação nova; a nova intenção é incorporada à negociação aberta existente (pode resultar em um novo orçamento dentro da mesma negociação — REQ-006.3 + REQ-016.10)
  - O vendedor pode, manualmente pelo painel (REQ-010), **encerrar a negociação atual** (transição para `perdida`/`ganha`/`abandonada`) e **abrir uma nova** se considerar que se trata de venda separada
  - **Não há detecção automática** de "este pedido é uma nova negociação" no POC; a regra é simples: uma aberta de cada vez, vendedor decide quando fechar e abrir outra

- [ ] **REQ-016.8 — Reabertura após abandono**: Se o cliente voltar a enviar mensagens depois que a negociação foi marcada como `abandonada` (REQ-002.22):
  - **POC (padrão)**: criar uma **nova negociação** com novo `numero_negociacao_cliente` (incremento natural). A negociação anterior permanece `abandonada` no histórico
  - Alternativamente, o vendedor pode, manualmente, **reabrir** a negociação anterior (transição `abandonada` → `aberta`) caso julgue ser a mesma venda. Essa decisão é registrada com autoria e timestamp (REQ-016.5)

### 4.4 Relação com outras entidades

- [ ] **REQ-016.9 — Vínculo com Conversa (REQ-005)**: Toda Conversa, ao ser criada por intenção de compra (REQ-002.1), deve ser associada a uma negociação (`negociacao_id`). Uma negociação pode ter múltiplas conversas vinculadas ao longo do tempo (caso de reengajamento sem criar nova negociação — REQ-016.7).

- [ ] **REQ-016.10 — Vínculo com Orçamento (REQ-006)**: Todo Orçamento (`orcamento_id`) deve estar associado a exatamente uma negociação (`negociacao_id`). Esta é a alteração principal no REQ-006 decorrente deste requisito (ver atualização do REQ-006).

- [ ] **REQ-016.11 — Conversas/mensagens sem intenção comercial**: Mensagens que **não** disparam o fluxo de qualificação (ex.: dúvidas isoladas atendidas via REQ-003, mensagens sociais) **não** criam negociação. Negociação só nasce de intenção de compra detectada pelo classificador REQ-002.1.

### 4.5 Exibição e Consulta

- [ ] **REQ-016.12 — Exibição no painel administrativo**: O painel (REQ-010) deve exibir o `numero_negociacao_cliente` em pelo menos:
  - **Cabeçalho da tela de conversa** (REQ-010.7A): junto ao nome do cliente, ex.: "ACME Ltda — Negociação #3"
  - **Lista de orçamentos** (REQ-010.5): coluna ou badge indicando a negociação à qual cada orçamento pertence
  - **Detalhe do orçamento** (REQ-010.6): referência clara à negociação pai com link para visualizar as outras conversas/orçamentos da mesma negociação

- [ ] **REQ-016.13 — Consulta por negociação**: O painel deve permitir, a partir de uma negociação, navegar para:
  - Todas as conversas vinculadas
  - Todos os orçamentos vinculados
  - Histórico de transições de estado (REQ-016.5)

### 4.6 Requisitos Não-Funcionais

- [ ] **REQ-016.14 — Integridade referencial**: Restrições de banco devem garantir:
  - Índice único em `(telefone, numero_negociacao_cliente)`
  - FK `orcamentos.negociacao_id` NOT NULL
  - FK `conversas.negociacao_id` NULL permitido apenas para conversas anteriores à adoção deste requisito (migração); novas conversas geradas por intenção de compra exigem `negociacao_id`

- [ ] **REQ-016.15 — Auditoria**: Criação de negociação, transições de estado e reaberturas devem ser registradas como eventos auditáveis em REQ-005.4 (ex.: `negociacao_criada`, `negociacao_estado_alterado`).

---

## 5. Fluxos Esperados

### 5.1 Cliente novo — primeira negociação

```
Cliente: "Olá, quero orçamento para 5 catracas"
Sistema: (REQ-002.1 detecta intenção)
        (REQ-016.6 cria Negociação #1 — estado `aberta`)
        (segue qualificação normal — REQ-002)
        ...
        (gera Orçamento A — vinculado à Negociação #1)
Painel: "ACME Ltda — Negociação #1 — 1 orçamento"
```

### 5.2 Mesmo cliente, revisão de orçamento na mesma negociação

```
Cliente (3 dias depois): "Aquela catraca pedestal sai por menos se for giratória?"
Sistema: (REQ-016.7 — negociação #1 ainda `aberta` → não cria nova)
        (gera Orçamento B — também vinculado à Negociação #1)
Painel: "ACME Ltda — Negociação #1 — 2 orçamentos"
```

### 5.3 Negociação perdida, cliente volta meses depois

```
Vendedor (no painel): marca Negociação #1 como `perdida`
...
6 meses depois:
Cliente: "Vou precisar de mais catracas, podem cotar?"
Sistema: (REQ-002.1 detecta intenção)
        (REQ-016.6 — não há negociação `aberta` → cria Negociação #2)
Painel: "ACME Ltda — Negociação #2 — em qualificação"
```

### 5.4 Abandono e retomada

```
Cliente: (some por 4 dias)
Sistema: (REQ-002.22 finaliza conversa, Negociação #2 → `abandonada`)

Cliente: "Oi, desculpa a demora"
Sistema: (REQ-016.8 — POC padrão: cria Negociação #3)
        (ou, se vendedor reabriu manualmente: continua na #2 como `aberta`)
```

---

## 6. Limitações Aceitas no POC

- [ ] Sem fusão de negociações (se vendedor abrir duas por engano, não há ação automatizada de mesclar; correção manual via banco)
- [ ] Sem detecção automática de "esta nova intenção é uma negociação diferente" — sempre cai na aberta atual (REQ-016.7)
- [ ] Sem reabertura automatizada por inferência de contexto — só manual pelo vendedor (REQ-016.8)
- [ ] Sem métricas agregadas de funil por negociação no POC (futuro)

---

## 7. Dependências

### 7.1 Dependências Técnicas
- Tabela `negociacoes` no PostgreSQL (já existe; precisa de coluna `numero_negociacao_cliente` se ainda não tiver, e índice único composto)
- Migration Alembic para adicionar coluna e índice
- Endpoint no backend para criação automática (acionada pelo classificador REQ-002.1)
- Ajustes no frontend (REQ-010) para exibição

### 7.2 Dependências entre Requisitos
- **REQ-002.1** — gatilho de criação da negociação
- **REQ-002.22** — abandono dispara transição `aberta` → `abandonada`
- **REQ-005** — eventos auditáveis (criação, transição) e vínculo com Conversa
- **REQ-006** — vínculo `orcamento.negociacao_id`; alteração obrigatória decorrente (REQ-016.10)
- **REQ-010** — exibição no painel (REQ-016.12); ajustes no REQ-010.7A (cabeçalho) decorrentes

---

## 8. Critérios de Sucesso

### 8.1 Métricas
- 100% das novas conversas de intenção de compra geram exatamente uma negociação
- 0 violações de unicidade `(telefone, numero_negociacao_cliente)` em produção
- Vendedor consegue citar uma negociação pelo número sem ambiguidade ("Negociação #3 da ACME")

### 8.2 Condições de Aceite Final
- Painel exibe "Cliente — Negociação #N" no cabeçalho do chat
- Lista de orçamentos mostra a negociação a que cada um pertence
- Numeração reinicia em 1 para cada cliente novo, incrementa corretamente

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Vendedor abrir negociações em excesso (uma por mensagem) | Baixa | Médio | REQ-016.7 deixa explícito: uma aberta por vez; nova só por ação manual |
| Migração com conversas antigas sem `negociacao_id` | Alta | Baixo | REQ-016.14 permite NULL para conversas antigas; novas exigem |
| Confusão entre `orcamento_id` e `numero_negociacao_cliente` na UI | Média | Baixo | UI sempre usa "Negociação #N" para humano, `orcamento_id` apenas técnico |
| Race condition em alta concorrência | Baixa (POC) | Médio | Advisory lock por `telefone` se necessário em fase posterior |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| Migration Alembic (coluna `numero_negociacao_cliente` + índice único) | 2h |
| Lógica de criação automática integrada ao REQ-002.1 | 3h |
| Transições de estado (manuais via painel) | 3h |
| Ajustes no REQ-006 (FK orcamento → negociacao) | 2h |
| Ajustes no painel (REQ-010): cabeçalho, lista, detalhe | 4h |
| Eventos auditáveis em REQ-005 | 2h |
| Testes e ajustes | 3h |
| **Total** | **19h** |

---

## 11. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 01/06/2026 | 1.0 | Criação inicial do requisito formalizando o conceito de Negociação como agrupador entre Conversa e Orçamento, com numeração sequencial por cliente (`numero_negociacao_cliente`). Resolve dívida documental sobre a tabela `negociacoes` já existente. Inclui ciclo de vida (aberta/ganha/perdida/abandonada), regras de criação automática, reabertura, vínculos com REQ-002, REQ-005, REQ-006, REQ-010. | Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 01/06/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
