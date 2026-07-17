# Análise: Renomeação "Negociação" → "Atendimento"

<!-- CLASSIFICACAO: HISTORICO -->

**Agente:** `[analista]` (inferido)
**Versão:** 0.4 (Fases 1-4 executadas)
**Data:** 2026-06-09
**Autor:** Beto
**Base:** conversa Kika ↔ Beto + REQ-016 v1.0
**Status:** Concluído. Fases 1-4 executadas: REQs e backlogs fechados, código renomeado (`backend/models.py` usa `Atendimento`/`StatusAtendimento`/`AtendimentoInfo`, classe `Negociacao` não existe mais) e painel usa a terminologia "Atendimento" ponta a ponta. Decisões D1–D6 fechadas; ganha/perdida confirmada exclusivamente no orçamento (D2-bis). (Corrigido em 2026-07-17 — rótulo anterior dizia Fases 3-4 pendentes.)

---

## 1. Proposta resumida

Substituir o conceito de **Negociação** por **Atendimento**, com as seguintes mudanças de comportamento (além do rename):

1. **Numeração sequencial por telefone**, iniciando em 1 — *igual ao REQ-016.3 atual*.
2. **Pergunta ao cliente** quando voltar a entrar em contato: "é continuação do atendimento anterior ou um novo?" — *substitui a regra automática de REQ-016.7/REQ-016.8*.
3. **Parâmetro de prazo mínimo** para fazer essa pergunta: se o cliente voltar **dentro** do prazo, assume continuação automaticamente; se voltar **depois** do prazo, pergunta — *conceito novo, sem equivalente em REQ-016*.
4. **Futuro**: inferência por contexto se o atendimento anterior foi de fato finalizado — *futuro pós-POC, fora do escopo desta proposta*.
5. **1 atendimento → N orçamentos** — *igual ao REQ-016.10 atual*.
6. **Tabela `negociacoes` é renomeada/substituída** por `atendimentos`.

---

## 2. Comparação conceitual

| Aspecto | Negociação (REQ-016 atual) | Atendimento (proposto) |
|---------|---------------------------|------------------------|
| **Nome** | Negociação | Atendimento |
| **Gatilho de criação** | Intenção de compra (REQ-002.1) | Intenção de compra OU primeiro contato sem atendimento anterior |
| **Numeração** | `numero_negociacao_cliente` (seq por telefone, começa em 1) | `numero_atendimento_cliente` (idem) |
| **Estados** | `aberta` / `ganha` / `perdida` / `abandonada` | Manter? Renomear? (ver decisão D3) |
| **Cliente volta** | Hoje vai automático pra "aberta" atual (REQ-016.7); se abandonada, cria nova (REQ-016.8) | **Pergunta ao cliente** se dentro do prazo + status compatível; **assume continuação** se dentro do prazo curto |
| **Vínculo conversa** | `conversa.negociacao_id` | `conversa.atendimento_id` |
| **Vínculo orçamento** | `orcamento.negociacao_id` (obrigatório) | `orcamento.atendimento_id` (obrigatório) |
| **Painel** | "ACME — Negociação #3" | "ACME — Atendimento #3" |
| **Cardinalidade** | 1 negociação → 0..N orçamentos | 1 atendimento → 0..N orçamentos (igual) |

**Diferença mais relevante**: hoje o **sistema** decide; na proposta nova o **cliente** decide (com auto-decisão dentro de um prazo curto).

---

## 3. Decisões pendentes (antes de executar)

Cinco pontos que precisam de definição da Kika para que a análise vire requisito formal:

### D1 — Renomear vs substituir tabela

**Opções:**
- **(a) Renomear** `negociacoes` → `atendimentos` (preserva dados, FK, índices; migration `RENAME TABLE` + `RENAME COLUMN`).
- **(b) Substituir**: criar `atendimentos` nova, migrar dados, dropar `negociacoes` (mais invasiva, mais segura para mudanças estruturais grandes).

**Recomendação:** (a) renomear. As mudanças de comportamento não exigem schema novo — só novos campos (timestamp de última mensagem, motivo de finalização) e a coluna de numeração já existe.

### D2 — Estado de "atendimento aberto" continua existindo?

A regra nova é "perguntar se é continuação". Para perguntar, o sistema precisa saber **qual atendimento candidato** mostrar. Isso pressupõe que ainda existe um estado **ativo** vs **encerrado**.

**Opções:**
- **(a) Manter os 4 estados** do REQ-016.4 (`aberta` / `ganha` / `perdida` / `abandonada`) e usar "aberta" como o candidato a continuação.
- **(b) Simplificar para 2 estados** (`ativo` / `encerrado`), com `motivo_encerramento` capturando ganha/perdida/abandono.

**Recomendação:** (b) é mais aderente à narrativa de atendimento; (a) preserva mais informação operacional.

### D3 — Nome do parâmetro de prazo mínimo

Sugestões: `prazo_continuacao_automatica_horas`, `janela_continuacao_atendimento`, `tempo_max_continuacao_silenciosa`.

**Default sugerido:** 4h (entre a mesma "rajada" do cliente — ele saiu para almoçar, voltou, é continuação óbvia).

Esse parâmetro vai para **REQ-014** (configuração runtime).

### D4 — Comportamento por estado anterior do atendimento

Quando o cliente volta, **sempre** pergunta? Ou só em alguns estados?

| Estado anterior | Cliente volta dentro do prazo | Cliente volta após o prazo |
|-----------------|-------------------------------|----------------------------|
| `ativo` | continua automaticamente | **pergunta** |
| `encerrado:ganha` | ? | ? (provavelmente novo) |
| `encerrado:perdida` | ? | ? |
| `encerrado:abandonada` | continua automaticamente (?) | **pergunta** |

A Kika precisa preencher essa matriz. Sugestão minha:

| Estado anterior | Dentro do prazo | Após o prazo |
|-----------------|-----------------|--------------|
| `ativo` | continua | **pergunta** (defaults a continuar) |
| `encerrado:ganha` | **pergunta** (defaults a novo) | **novo atendimento direto** |
| `encerrado:perdida` | **pergunta** | **novo atendimento direto** |
| `encerrado:abandonada` | continua | **pergunta** (defaults a continuar) |

### D5 — Como exatamente o sistema "pergunta"

Mensagem template? Pergunta dirigida com opções enumeradas (REQ-002.21)?

Sugestão:
> "Oi! Vi que você já conversou conosco antes sobre **{resumo_curto}**. Quer continuar de onde paramos ou é um pedido novo?"
>
> 1) Continuar
> 2) Novo pedido

A resposta "1" ou "Continuar" → reusa atendimento anterior. "2" ou "Novo" → cria atendimento novo.

Essa interação deveria virar **REQ-002.X** (regra de fluxo) ou **REQ-016.X** (regra do agregador). Sugestão: ficar em REQ-016, com REQ-002 só referenciando.

---

## 4. Impacto por REQ

### REQ-016 (Identificação e Numeração de **Negociações**) — IMPACTO MÁXIMO

**Arquivo:** renomear `REQ-016-identificacao-numeracao-negociacoes.md` → `REQ-016-identificacao-numeracao-atendimentos.md`.

**Mudanças textuais (rename global):**

- Título, descrição, todos os subitens (REQ-016.1 a REQ-016.15).
- `negociacao_id` → `atendimento_id`.
- `numero_negociacao_cliente` → `numero_atendimento_cliente`.
- "Negociação #N" → "Atendimento #N".

**Mudanças de conteúdo (não-rename):**

- **REQ-016.7** (Comportamento quando já existe negociação aberta) **reescreve completamente** para refletir a pergunta ao cliente + prazo de continuação automática. Hoje diz "POC = vai pra aberta atual"; novo diz "consulta o estado + prazo + pergunta".
- **REQ-016.8** (Reabertura após abandono) **incorpora-se** ao novo REQ-016.7 (mesma lógica de decisão).
- **Novo REQ-016.X** — Parâmetro `janela_continuacao_atendimento` em REQ-014 (decisão D3).
- **Novo REQ-016.X** — Template de mensagem para perguntar (decisão D5).
- **Estados em REQ-016.4** podem mudar se Kika escolher D2(b).
- **Limitações no POC** atualizadas: remover "sem detecção automática de nova negociação" (essa detecção passa a existir via pergunta + prazo).

### REQ-002 (Fluxo Conversacional) — IMPACTO BAIXO (só rename)

Ocorrências:
- Linha 57: `"campo cnpj da negociação"` → `"campo cnpj do atendimento"`.
- Linhas 100, 102, 103 (REQ-002.1B): `"contato e negociação anônimos"` → `"contato e atendimento anônimos"`.

Sem mudança de comportamento. Apenas rename.

### REQ-003 (Respostas Automáticas / RAG) — NENHUM IMPACTO REAL

Ocorrências:
- Linha 57: `"sem negociação de desconto"` — **VERBO**, não é a entidade. **NÃO renomear**.
- Linha 76: `"Não negociar desconto"` — idem.

**Falso positivo do grep**. REQ-003 fica intacto.

### REQ-005 (Registro de Interações) — IMPACTO BAIXO

Ocorrências:
- Linha 83: `"o cliente fizer perguntas, negociar ou pedir esclarecimentos"` — **verbo**, falso positivo.

**Mas há impacto indireto**: eventos auditáveis `negociacao_criada`, `negociacao_estado_alterado` (citados em REQ-016.15) viram `atendimento_criado`, `atendimento_estado_alterado`. Ajustar onde forem listados no REQ-005.

### REQ-006 (Rastreamento de Orçamentos) — IMPACTO MÉDIO (rename + FK)

Ocorrências de **entidade** (renomear):
- Linha 53 (REQ-006.2): `"Associação do orçamento à conversa, ao cliente e à negociação"`.
- Linha 56: `negociacao_id (REQ-016) — obrigatório`.
- Linha 59 (REQ-006.3): `"Múltiplos orçamentos por cliente e por negociação"` — manter texto, só ajustar termo.
- Linha 140: `"todo orçamento pertence a uma negociação"`.
- Linha 212 (histórico): manter como histórico (é record), só anotar mudança em nova linha.

FK no banco: `orcamentos.negociacao_id` → `orcamentos.atendimento_id`.

### REQ-010 (Painel Administrativo) — IMPACTO MÉDIO (UI fala "Negociação")

Ocorrências:
- Linha 79, 82, 83: `"Negociação #3"`, `"Negociação #1 · ⚠️ restrição"` — UI exibida ao vendedor.
- Linha 111: tabela de integração com REQ-016 — reescrever para "Atendimento".

**Decisão de UX implícita**: o vendedor já está acostumado com "Negociação #N"? Vale conferir com a Rita se "Atendimento #N" é mais natural para ela (recomendado fazer essa pergunta no próximo contato).

### REQ-011 (Modos de Execução) — IMPACTO BAIXO (rename)

Ocorrências:
- Linha 59 (REQ-011.2): `"Granularidade por negociação"` → `"Granularidade por atendimento"`.
- Linha 110 (REQ-011.14): `"Quando a negociação estiver em estado Em atendimento humano"` — observe: aqui há **colisão** entre o conceito antigo (`negociação`) e a expressão `em atendimento humano` (verbo, REQ-004.4). Reescrever: `"Quando o atendimento estiver em modo humano (REQ-004.4)"` (mais limpo após a renomeação).
- Linha 130, 230: `"filtros por vendedor, período e negociação"` e `"sem granularidade por negociação"` → rename.

**Atenção**: a expressão "atendimento humano" (estado do REQ-004) **vai conflitar visualmente** com a nova entidade "Atendimento". Considerar renomear o estado de **REQ-004.4** de `Em atendimento humano` para `Em handover humano` ou `Em modo humano` — ver decisão **D6** abaixo.

### REQ-012 (Reports) — IMPACTO BAIXO (rename)

Ocorrências:
- Linha 98 (REQ-012.3): `"detalhes de uma negociação ou processamento"`.
- Linha 168 (REQ-012.12): `"detalhe de uma negociação/mensagem"`.

### REQ-013 (Pares Q&A) — NENHUM IMPACTO

- Linha 259: `"não negociar desconto"` — verbo, falso positivo.

### REQs sem ocorrências mas com impacto secundário

- **REQ-014 (Configuração Runtime)**: adicionar o novo parâmetro `janela_continuacao_atendimento` (decisão D3).
- **REQ-004 (Human Takeover)**: revisar a expressão "Em atendimento humano" (D6).

---

## D6 — Colisão "Atendimento" (entidade) × "atendimento humano" (estado de REQ-004)

Após o rename, o vendedor lerá no painel:
> "Atendimento #3 — em atendimento humano"

Ambíguo. Sugestões:

- Renomear o estado de REQ-004.4 para `Em modo humano` ou `Handover humano`.
- Ou usar adjetivo: `Atendimento #3 — assistido por humano`.

**Recomendação:** Renomear o estado para `modo humano` (alinhado ao vocabulário do REQ-011 que já fala em "modos de execução").

---

## 5. Impacto no modelo de dados

### Tabelas (migration Alembic)

| Tabela atual | Operação | Tabela nova |
|--------------|----------|-------------|
| `negociacoes` | `RENAME TO` | `atendimentos` |
| `negociacao_infos` | `RENAME TO` | `atendimento_infos` |

### Colunas

| Coluna atual | Operação | Coluna nova |
|--------------|----------|-------------|
| `negociacoes.numero_negociacao_cliente` | `RENAME TO` | `atendimentos.numero_atendimento_cliente` |
| `orcamentos.negociacao_id` | `RENAME TO` | `orcamentos.atendimento_id` |
| `conversas.negociacao_id` (se existir) | `RENAME TO` | `conversas.atendimento_id` |
| `negociacao_infos.negociacao_id` | `RENAME TO` | `atendimento_infos.atendimento_id` |
| `mensagens.negociacao_id` (citado em `models.py`) | `RENAME TO` | `mensagens.atendimento_id` |

### Colunas novas

| Tabela | Coluna nova | Propósito |
|--------|-------------|-----------|
| `atendimentos` | `ultima_mensagem_at` (TIMESTAMP) | Cálculo da janela de continuação (D3) |
| `atendimentos` | `motivo_encerramento` (enum/string) | Substituiria os estados granulares se D2(b) |

### Índices e constraints

| Atual | Novo |
|-------|------|
| `idx_negociacao_*` | `idx_atendimento_*` (mesmos critérios) |
| FK `orcamentos.negociacao_id → negociacoes.id` | FK `orcamentos.atendimento_id → atendimentos.id` |
| Unique `(telefone, numero_negociacao_cliente)` | Unique `(telefone, numero_atendimento_cliente)` |

---

## 6. Impacto no código (resumo, sem patches)

Arquivos com referências a "negociacao" (não exaustivo, baseado em busca prévia):

- `backend/models.py` — classe `Negociacao`, enum `StatusNegociacao`, `NegociacaoInfo`, `OrigemInfo`. Renomear classes + tabelas mapeadas.
- `backend/services/processador.py` — `_negociacao_ativa`, `_obter_ou_criar_negociacao`, `_atualizar_infos_negociacao`.
- `backend/services/identificador.py` — pode ter referências.
- `backend/services/respostas/*` — templates podem citar "negociação".
- `frontend/src/**` — labels de UI ("Negociação #N"), tipos TypeScript, services.

**Estratégia recomendada**: rename amplo via grep + revisão manual dos falsos positivos ("negociar desconto", "negociação de prazos" em texto natural).

---

## 7. Plano sugerido (ordem de execução)

1. **Decisões D1–D6** acima — Kika fecha.
2. **Atualizar REQ-016** com nome novo, renumerar arquivo, reescrever REQ-016.7/REQ-016.8 conforme decisão final.
3. **Atualizar REQ-002, REQ-005, REQ-006, REQ-010, REQ-011, REQ-012** com rename + ajustes (REQ-011 tem ajuste real além do rename).
4. **Atualizar REQ-014** com novo parâmetro `janela_continuacao_atendimento`.
5. **Atualizar REQ-004** com renomeação do estado (se decisão D6 = sim).
6. **Migration Alembic** com renames.
7. **Refatoração do código** backend + frontend.
8. **Adicionar tarefa no backlog REQ-002** (`backlog_req002_tarefas.md`): nova tarefa **T-12 — Pergunta de continuação de atendimento**, ou incorporar à T-05 (estado dos campos).

---

## 8. Pontos de atenção

- **Backlog REQ-002 já criado** (`backlog_req002_tarefas.md` v0.1) usa o termo "negociação". Após decisão, atualizar para "atendimento" antes de virar issues no GitHub Projects.
- **Política de branches v1.1** não é afetada.
- **Bugs CTF abertos** não são afetados (só citam contato/empresa/conversa).
- **Sprint Review YAMLs** podem ter "negociação" no texto — checar antes da próxima review (G01).

---

## Histórico

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-09 | 0.1 | Criação inicial — análise textual dos REQs (REQ-002, 003, 005, 006, 010, 011, 012, 013, 016) e mapeamento de pontos de ajuste decorrentes da renomeação Negociação → Atendimento. Lista 6 decisões pendentes (D1–D6). | Beto |
