# REQ-016: Identificação e Numeração de Atendimentos por Cliente

**Versão**: 2.0
**Data**: 2026-06-09
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

O sistema deve formalizar o conceito de **Atendimento** como **agrupador conversacional** entre uma conversa (REQ-005) e um ou mais orçamentos (REQ-006) gerados em torno da mesma intenção do cliente. Cada atendimento recebe um **número sequencial por cliente** (1, 2, 3, ...), tornando a referência operacional do vendedor simples e estável (ex.: "Atendimento #3 da ACME").

**Diferença em relação ao desfecho comercial**: o atendimento controla o **ciclo conversacional** (foi atendido / foi encerrado), enquanto o desfecho comercial (ganha/perdida) pertence ao **orçamento** (REQ-006). Um atendimento pode gerar zero, um ou mais orçamentos; cada orçamento tem seu próprio desfecho independente.

A tabela `negociacoes` (criada em sprints anteriores) é **renomeada** para `atendimentos` neste REQ, junto com todas as colunas e FKs relacionadas.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- A tabela `negociacoes` existe no banco mas seu papel conceitual estava confuso: misturava "agrupador conversacional" com "desfecho comercial" (ganha/perdida).
- Quando o cliente pede uma revisão de orçamento (ex.: trocar de catraca pedestal para giratória), o sistema cria um novo `orcamento_id` (REQ-006.3), mas perde a noção de que "as duas cotações são do mesmo atendimento".
- O vendedor não tem uma referência curta e estável para citar nas conversas internas ("o atendimento #5 da ACME" é mais útil que `orcamento_id` 7a2f8...).
- A decisão automática de "essa nova mensagem é continuação ou novo atendimento?" gerava ambiguidades — melhor perguntar ao cliente quando há dúvida.

**Benefício Esperado**:
- Separar **conversa** (REQ-005) de **agrupamento de orçamentos** (REQ-016) de **desfecho comercial** (REQ-006).
- Dar ao vendedor uma referência curta e sequencial por cliente.
- Permitir métricas mais limpas (ex.: "conversão por atendimento" em vez de "conversão por orçamento", que infla com revisões).
- Resolver dúvidas de continuidade via pergunta ao cliente, com janela curta de continuação automática para não interromper rajadas de mensagens.

**Feedback do vendedor (Rita)**: "quando um cliente solicita um orçamento, este receberia um número sequencial (começa com 1). Quando ele pede outro, seria o número 2... no painel seria legal exibir o número atual."

**Decisão da Kika (2026-06-09)**: substituir o termo "negociação" por "atendimento" em todo o sistema; ganha/perdida fica exclusivamente em REQ-006 (orçamento), removendo a confusão conceitual anterior.

---

## 4. Critérios de Aceite

### 4.1 Definição e Estrutura

- [ ] **REQ-016.1 — Definição de Atendimento**: Um **Atendimento** é a entidade que agrupa, para um mesmo cliente (`telefone`), os elementos relacionados a uma demanda conversacional:
  - Uma ou mais **conversas** (REQ-005) — um atendimento pode atravessar mais de uma conversa quando há reengajamento após abandono ou após pausa do cliente.
  - Zero ou mais **orçamentos** (REQ-006) — um atendimento pode ter zero orçamentos (qualificação ainda em curso, dúvida pré-venda) ou múltiplos (revisões, alternativas).
  - Um **ciclo de vida próprio** (REQ-016.4).

- [ ] **REQ-016.2 — Identificadores do Atendimento**: Cada atendimento tem dois identificadores:
  - `atendimento_id`: identificador único global (UUID ou sequencial interno), usado em chaves estrangeiras e integrações.
  - `numero_atendimento_cliente`: inteiro sequencial **por cliente**, começando em 1, usado para exibição ao vendedor e ao cliente.

  Os dois coexistem: `atendimento_id` é a referência técnica; `numero_atendimento_cliente` é a referência humana.

- [ ] **REQ-016.3 — Numeração sequencial por cliente**: O `numero_atendimento_cliente` deve ser:
  - Inteiro positivo iniciando em **1** para o primeiro atendimento de cada cliente.
  - **Incrementado em +1** a cada novo atendimento criado para o mesmo cliente, independentemente do desfecho dos anteriores (atendimentos encerrados continuam contando).
  - **Único** por par `(telefone, numero_atendimento_cliente)` — garantido por índice único no banco.
  - **Imutável** após criação — não muda mesmo se um atendimento for cancelado/excluído logicamente.

  **Mecanismo de geração** (referência de implementação):
  ```sql
  numero_atendimento_cliente = COALESCE(
      (SELECT MAX(numero_atendimento_cliente) FROM atendimentos WHERE telefone = :telefone),
      0
  ) + 1
  ```
  No POC, race conditions não são preocupação (vendedor único, baixa concorrência). Em produção: usar advisory lock por `telefone` ou sequência dedicada se necessário.

### 4.2 Ciclo de Vida

- [ ] **REQ-016.4 — Estados possíveis do atendimento**: Um atendimento tem **dois estados** simples:
  - `ativo` — em curso, recebendo mensagens, qualificação ou orçamentos.
  - `encerrado` — sem expectativa de continuação imediata; pode voltar a ser referenciado se o cliente reabrir manualmente (REQ-016.8).

  **Motivo de encerramento** (`motivo_encerramento`) é registrado quando a transição `ativo` → `encerrado` ocorre, com um dos valores:
  - `concluido_pelo_cliente` — cliente respondeu negativamente à pergunta de fechamento do REQ-016.10 ("Posso ajudar em mais alguma coisa?").
  - `abandono` — janela de inatividade do REQ-002.22 esgotou (72h sem resposta após o reengajamento).
  - `manual_vendedor` — vendedor encerrou explicitamente pelo painel administrativo (REQ-010).

  **Desfechos comerciais (ganha/perdida) ficam exclusivamente no orçamento** (REQ-006.5). O atendimento **não** carrega esse estado — um atendimento pode ter múltiplos orçamentos com desfechos diferentes (uma proposta convertida, outra perdida) sem que isso afete o estado conversacional do atendimento em si.

  **Transições válidas**:
  - `ativo` → `encerrado` (com `motivo_encerramento` obrigatório).
  - `encerrado` → `ativo` (somente via reabertura manual do vendedor — REQ-016.8 — ou via decisão do cliente em resposta à pergunta de continuação — REQ-016.9).

- [ ] **REQ-016.5 — Timestamps e auditoria de transição**: Para cada mudança de estado, registrar:
  - Estado anterior e novo.
  - Timestamp da transição.
  - `motivo_encerramento` (quando aplicável).
  - Quem alterou (sistema automático ou usuário do painel — análogo a REQ-006.10).
  - Evento auditável em REQ-005 (`atendimento_criado`, `atendimento_encerrado`, `atendimento_reaberto`).

### 4.3 Regras de Criação e Continuação

- [ ] **REQ-016.6 — Criação automática na primeira intenção do cliente**: Quando o sistema receber mensagem de um telefone que **não tem atendimento associado** (telefone novo) ou cujos atendimentos anteriores estão todos `encerrado`, ele deve criar automaticamente um novo atendimento ao detectar **intenção de compra** (REQ-002.1 categoria 1) ou ao iniciar fluxo de qualificação. Estado inicial: `ativo`. `numero_atendimento_cliente` gerado conforme REQ-016.3.

- [ ] **REQ-016.7 — Janela de continuação automática**: Quando o cliente envia nova mensagem e existe um atendimento anterior (ativo ou encerrado), o sistema consulta o parâmetro `janela_continuacao_atendimento` (REQ-014, default **24h**) calculado a partir da `ultima_mensagem_at` do atendimento mais recente, e aplica a seguinte matriz:

  | Estado anterior | Dentro da janela | Após a janela |
  |-----------------|------------------|---------------|
  | `ativo` | Continua automaticamente no mesmo atendimento (sem pergunta). | **Pergunta** ao cliente (REQ-016.9), default sugerido = continuar. |
  | `encerrado` | **Pergunta** ao cliente (REQ-016.9), default sugerido = continuar. | **Cria novo atendimento** direto (sem pergunta). |

  O objetivo da janela é evitar perguntar a cada rajada do cliente (ex.: cliente envia 3 mensagens seguidas; todas pertencem ao mesmo atendimento). O default 24h cobre o caso típico de "cliente saiu para almoçar / voltou no dia seguinte para continuar".

- [ ] **REQ-016.8 — Reabertura manual de atendimento encerrado**: O vendedor pode, pelo painel (REQ-010), **reabrir** um atendimento `encerrado` (transição `encerrado` → `ativo`) caso julgue que o novo contato do cliente é continuação direta. A decisão é registrada com autoria, timestamp e justificativa textual em REQ-016.5.

- [ ] **REQ-016.9 — Pergunta de continuação ao cliente**: Quando a matriz da REQ-016.7 indicar que o sistema deve perguntar, ele envia mensagem de transição com opções enumeradas (alinhado ao estilo do REQ-002.21):

  > "Oi! Vi que você já conversou conosco antes sobre **{resumo_curto}**. Quer continuar de onde paramos ou é um pedido novo?
  >
  > 1) Continuar
  > 2) Novo pedido"

  Comportamento:
  - Resposta `1` / `continuar` / `continua` / `sim` (com tolerância semântica via classificador REQ-002.1) → reusa o atendimento anterior, transitando `encerrado` → `ativo` se necessário (registra como reabertura por decisão do cliente, REQ-016.5).
  - Resposta `2` / `novo` / `outro` → cria novo atendimento conforme REQ-016.6.
  - Resposta ambígua → aplica REQ-002.21 (até 2 esclarecimentos; após esgotar, criar novo atendimento por padrão).
  - O `{resumo_curto}` é gerado a partir dos dados do último atendimento (tipo de produto, modelo, status do último orçamento). Se não houver dados suficientes, usar texto genérico ("seu atendimento anterior").

- [ ] **REQ-016.10 — Pergunta de fechamento do atendimento**: Quando o sistema considerar a demanda atual atendida (orçamento enviado, dúvida respondida, etc.), antes de simplesmente parar de interagir ele deve perguntar ao cliente se há algo mais:

  > "Posso te ajudar em mais alguma coisa?"

  Comportamento:
  - Resposta negativa (`não`, `obrigado`, `tudo certo`, etc., via classificador REQ-002.1) → transita o atendimento para `encerrado` com `motivo_encerramento = concluido_pelo_cliente`. Sistema envia mensagem de despedida cordial.
  - Resposta afirmativa ou nova demanda → permanece em `ativo`; novo ciclo de qualificação ou consulta à base de conhecimento conforme a classificação da mensagem.
  - Ausência de resposta → segue regra do REQ-002.22 (abandono em 72h totais → `motivo_encerramento = abandono`).

  **Quando disparar a pergunta**: ao final de um ciclo natural — por exemplo, após confirmação de envio de orçamento, após resposta a uma dúvida pré-venda sem qualificação aberta, ou após 30 minutos de silêncio dentro de uma conversa ativa (configurável em revisão futura).

### 4.4 Relação com outras entidades

- [ ] **REQ-016.11 — Vínculo com Conversa (REQ-005)**: Toda Conversa, ao ser criada por intenção de compra (REQ-002.1) ou retomada de atendimento, deve ser associada a um atendimento (`atendimento_id`). Um atendimento pode ter múltiplas conversas vinculadas ao longo do tempo (caso de reengajamento sem criar novo atendimento — REQ-016.7).

- [ ] **REQ-016.12 — Vínculo com Orçamento (REQ-006)**: Todo Orçamento (`orcamento_id`) deve estar associado a exatamente um atendimento (`atendimento_id`). Esta é a alteração principal no REQ-006 decorrente deste requisito.

  **Independência de desfecho**: o estado `convertido`/`perdido` do orçamento (REQ-006.5) **não** altera o estado do atendimento. Um atendimento permanece `ativo` enquanto o cliente puder voltar a interagir; só transita para `encerrado` pelos motivos do REQ-016.4.

- [ ] **REQ-016.13 — Conversas sem intenção comercial**: Mensagens que **não** disparam fluxo de qualificação e podem ser resolvidas inteiramente por REQ-003 (Q&A/RAG) **podem** criar atendimento anônimo conforme REQ-002.1B, mas o atendimento continua aplicável. Mensagens estritamente sociais (ex.: "obrigado") em atendimento já encerrado **não** criam atendimento novo.

### 4.5 Exibição e Consulta

- [ ] **REQ-016.14 — Exibição no painel administrativo**: O painel (REQ-010) deve exibir o `numero_atendimento_cliente` em pelo menos:
  - **Cabeçalho da tela de conversa** (REQ-010.7A): junto ao nome do cliente, ex.: "ACME Ltda — Atendimento #3".
  - **Lista de orçamentos** (REQ-010.5): coluna ou badge indicando o atendimento ao qual cada orçamento pertence.
  - **Detalhe do orçamento** (REQ-010.6): referência clara ao atendimento pai com link para visualizar as outras conversas/orçamentos do mesmo atendimento.

- [ ] **REQ-016.15 — Consulta por atendimento**: O painel deve permitir, a partir de um atendimento, navegar para:
  - Todas as conversas vinculadas.
  - Todos os orçamentos vinculados (com seus desfechos independentes).
  - Histórico de transições de estado (REQ-016.5).

### 4.6 Requisitos Não-Funcionais

- [ ] **REQ-016.16 — Integridade referencial**: Restrições de banco devem garantir:
  - Índice único em `(telefone, numero_atendimento_cliente)`.
  - FK `orcamentos.atendimento_id` NOT NULL.
  - FK `conversas.atendimento_id` NULL permitido apenas para conversas anteriores à adoção deste requisito (migração); novas conversas geradas por intenção de compra exigem `atendimento_id`.
  - Coluna `ultima_mensagem_at` (TIMESTAMP) em `atendimentos` para suportar o cálculo da janela de continuação (REQ-016.7).

- [ ] **REQ-016.17 — Auditoria**: Criação, encerramento e reabertura de atendimento devem ser registrados como eventos auditáveis em REQ-005.4: `atendimento_criado`, `atendimento_encerrado`, `atendimento_reaberto`. Pergunta de continuação (REQ-016.9) e de fechamento (REQ-016.10) também devem ser registradas como eventos para análise posterior de UX.

### 4.7 Configuração

- [ ] **REQ-016.18 — Parâmetro `janela_continuacao_atendimento`**: Configurável em runtime conforme REQ-014, controla a duração da janela usada em REQ-016.7. Default: **24 horas** (`86400` segundos ou `24` se a unidade for horas — definição final no REQ-014). Validação: inteiro positivo.

---

## 5. Fluxos Esperados

### 5.1 Cliente novo — primeiro atendimento

```
Cliente: "Olá, quero orçamento para 5 catracas"
Sistema: (REQ-002.1 detecta intenção)
        (REQ-016.6 cria Atendimento #1 — estado `ativo`)
        (segue qualificação normal — REQ-002)
        ...
        (gera Orçamento A — vinculado ao Atendimento #1)
        (após confirmar envio, REQ-016.10 pergunta "Posso ajudar em mais alguma coisa?")
Cliente: "Não, obrigado"
Sistema: (transita Atendimento #1 → `encerrado`, motivo = `concluido_pelo_cliente`)
Painel: "ACME Ltda — Atendimento #1 (encerrado) — 1 orçamento"
```

### 5.2 Cliente volta dentro da janela (24h) com atendimento `encerrado`

```
Cliente (10h depois): "Aquela catraca pedestal sai por menos se for giratória?"
Sistema: (último Atendimento #1 está `encerrado`, dentro da janela de 24h)
        (REQ-016.9 pergunta "Quer continuar de onde paramos ou é um pedido novo?")
Cliente: "Continuar"
Sistema: (reabre Atendimento #1 → `ativo`)
        (gera Orçamento B — vinculado ao Atendimento #1)
Painel: "ACME Ltda — Atendimento #1 (ativo) — 2 orçamentos"
```

### 5.3 Cliente volta após 24h com atendimento `encerrado`

```
Cliente (3 dias depois): "Vou precisar de mais catracas, podem cotar?"
Sistema: (REQ-016.7 — encerrado + fora da janela → cria novo atendimento direto)
        (REQ-016.6 cria Atendimento #2)
Painel: "ACME Ltda — Atendimento #2 — em qualificação"
```

### 5.4 Cliente envia rajada de mensagens (mesma janela, atendimento `ativo`)

```
Cliente: "preciso de orçamento"
Sistema: cria Atendimento #1, pergunta tipo de produto
Cliente (2 min depois): "para 5 catracas"
Sistema: (Atendimento #1 ativo, dentro da janela → continua sem perguntar)
Cliente (5 min depois): "biométricas"
Sistema: (idem — segue qualificação)
```

### 5.5 Abandono

```
Cliente: (some por 24h dentro de Atendimento #1 ativo)
Sistema: (REQ-002.22 envia mensagem única de reengajamento)
Cliente: (não responde por mais 48h — 72h totais)
Sistema: (transita Atendimento #1 → `encerrado`, motivo = `abandono`)

Cliente (10 dias depois): "Oi, desculpa a demora"
Sistema: (REQ-016.7 — encerrado + fora da janela → cria Atendimento #2)
```

### 5.6 Orçamento perdido não encerra o atendimento

```
Atendimento #1 ativo, com Orçamento A enviado.
Vendedor (no painel): marca Orçamento A como `perdido` com motivo "preço".
Sistema: Atendimento #1 permanece `ativo` (orçamento perdido não fecha atendimento).
Cliente (1 dia depois): "E se eu trocar de modelo?"
Sistema: (continua no Atendimento #1 → gera Orçamento B)
```

---

## 6. Limitações Aceitas no POC

- [ ] Sem fusão de atendimentos (se vendedor abrir dois por engano, não há ação automatizada de mesclar; correção manual via banco).
- [ ] Sem inferência automática de continuidade por contexto (resumo semântico do atendimento anterior para decidir sozinho se é continuação) — apenas a janela temporal + pergunta ao cliente.
- [ ] `{resumo_curto}` na pergunta do REQ-016.9 é gerado a partir de campos estruturados; sumarização semântica via LLM fica como evolução.
- [ ] Métricas agregadas de funil por atendimento ficam para versão futura.
- [ ] Pergunta de fechamento (REQ-016.10) acionada por regra simples no POC; heurística mais elaborada (ex.: detectar "fim de ciclo" por análise de intenção) é evolução pós-POC.

---

## 7. Dependências

### 7.1 Dependências Técnicas
- Tabela `atendimentos` (renomeada de `negociacoes`) no PostgreSQL com coluna `numero_atendimento_cliente` e `ultima_mensagem_at`, índice único composto.
- Migration Alembic para o rename (tabela, colunas, FKs em `orcamentos`, `conversas`, `mensagens`, `atendimento_infos`).
- Tabela `atendimento_infos` (renomeada de `negociacao_infos`) com FK `atendimento_id`.
- Endpoint no backend para criação automática (acionada pelo classificador REQ-002.1).
- Job/scheduler para suportar REQ-002.22 e disparar a janela de continuação.
- Ajustes no frontend (REQ-010) para exibição.

### 7.2 Dependências entre Requisitos
- **REQ-002.1** — gatilho de criação do atendimento.
- **REQ-002.21** — política de retry usada na pergunta de continuação (REQ-016.9).
- **REQ-002.22** — abandono dispara transição `ativo` → `encerrado` com motivo `abandono`.
- **REQ-005** — eventos auditáveis (criação, encerramento, reabertura) e vínculo com Conversa.
- **REQ-006** — vínculo `orcamento.atendimento_id`; alteração obrigatória decorrente (REQ-016.12).
- **REQ-010** — exibição no painel (REQ-016.14); ajustes no REQ-010.7A (cabeçalho) decorrentes.
- **REQ-014** — parâmetro `janela_continuacao_atendimento` configurável em runtime (REQ-016.18).

---

## 8. Critérios de Sucesso

### 8.1 Métricas
- 100% das novas conversas de intenção de compra geram exatamente um atendimento.
- 0 violações de unicidade `(telefone, numero_atendimento_cliente)` em produção.
- Vendedor consegue citar um atendimento pelo número sem ambiguidade ("Atendimento #3 da ACME").
- > 80% das rajadas (mensagens em sequência dentro de 1h) ficam no mesmo atendimento sem o sistema perguntar.

### 8.2 Condições de Aceite Final
- Painel exibe "Cliente — Atendimento #N" no cabeçalho do chat.
- Lista de orçamentos mostra o atendimento a que cada um pertence.
- Numeração reinicia em 1 para cada cliente novo, incrementa corretamente.
- Pergunta de continuação (REQ-016.9) e de fechamento (REQ-016.10) funcionam end-to-end no painel administrativo (sem WhatsApp).
- `janela_continuacao_atendimento` ajustável em runtime via REQ-014 reflete sem reiniciar o servidor.

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Cliente confuso com a pergunta "continuar ou novo?" | Média | Baixo | Pergunta com opções enumeradas (REQ-016.9) + janela curta default 24h evita perguntar à toa |
| Janela curta demais força pergunta excessiva | Média | Médio | Configurável em runtime (REQ-014); calibragem com dados reais |
| Janela longa demais junta atendimentos diferentes | Baixa | Médio | Pergunta de fechamento (REQ-016.10) limita atendimentos "vivos por tempo demais" |
| Confusão entre `orcamento_id` e `numero_atendimento_cliente` na UI | Média | Baixo | UI sempre usa "Atendimento #N" para humano; `orcamento_id` apenas técnico |
| Vendedor não usa o painel para encerrar manualmente, atendimentos acumulam ativos | Média | Baixo | Pergunta de fechamento automática + abandono em 72h cobrem a maioria dos casos |
| Race condition em alta concorrência (numeração) | Baixa (POC) | Médio | Advisory lock por `telefone` se necessário em fase posterior |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| Migration Alembic (rename `negociacoes`→`atendimentos`, colunas, FKs, índices) | 3h |
| Coluna `ultima_mensagem_at` + atualização automática a cada mensagem | 2h |
| Lógica de criação automática integrada ao REQ-002.1 | 3h |
| Janela de continuação + pergunta REQ-016.9 (template + classificação da resposta) | 5h |
| Pergunta de fechamento REQ-016.10 (gatilho + classificação da resposta) | 4h |
| Transições de estado (encerramento manual via painel) | 2h |
| Ajustes no REQ-006 (FK orcamento → atendimento) | 2h |
| Ajustes no painel (REQ-010): cabeçalho, lista, detalhe, ação encerrar/reabrir | 5h |
| Parâmetro `janela_continuacao_atendimento` em REQ-014 | 2h |
| Eventos auditáveis em REQ-005 | 2h |
| Testes e ajustes | 4h |
| **Total** | **34h** |

---

## 11. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 01/06/2026 | 1.0 | Criação inicial do requisito formalizando o conceito de Negociação como agrupador entre Conversa e Orçamento, com numeração sequencial por cliente. Resolve dívida documental sobre a tabela `negociacoes` já existente. Inclui ciclo de vida (aberta/ganha/perdida/abandonada), regras de criação automática, reabertura, vínculos com REQ-002, REQ-005, REQ-006, REQ-010. | Kika |
| 09/06/2026 | 2.0 | Renomeação **Negociação → Atendimento** em todo o requisito (decisão Kika 2026-06-09). Mudanças estruturais: (a) tabela `negociacoes` renomeada para `atendimentos` (D1); (b) ciclo de vida simplificado para 2 estados `ativo`/`encerrado` + `motivo_encerramento` restrito a 3 valores (D2/D2-bis); ganha/perdida deixam de existir no atendimento e ficam exclusivas no orçamento (REQ-006); (c) novo REQ-016.7 com janela `janela_continuacao_atendimento` (default 24h, D3) e matriz "estado anterior × dentro/fora da janela" (D4); (d) novo REQ-016.9 com template de pergunta de continuação (D5); (e) novo REQ-016.10 com pergunta de fechamento "Posso ajudar em mais alguma coisa?" (D4); (f) novo REQ-016.18 sobre parâmetro em REQ-014. Renomeação `negociacao_id` → `atendimento_id` em todos os vínculos. Análise de impacto registrada em `analise_renomeacao_negociacao_para_atendimento.md`. | Beto + Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | ____/____/____ | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
