# REQ-013: Base de Pares Q&A Curados como Camada Prioritária do RAG

**Versão**: 1.0
**Data**: 2026-05-18
**Autor**: Kika (Analista de Requisitos)
**Status**: Em Elaboração
**Prioridade**: Alta

---

## 1. Identificação do Requisito

**ID**: REQ-013
**Tipo**: Funcional
**Categoria**: Qualidade do Agente / Conhecimento / Curadoria
**Solicitante**: Necessidade do produto (controlar qualidade das respostas mais sensíveis)

---

## 2. Descrição

O sistema deve manter uma **base de pares Pergunta+Resposta (Q&A) curados manualmente** que funciona como **camada prioritária** sobre o RAG genérico (REQ-003). Quando uma pergunta do cliente for muito similar a uma pergunta da base de Q&A curada, o sistema deve responder usando a resposta curada **diretamente**, sem reescrita pelo LLM, garantindo controle total sobre a saída em casos sensíveis (preços, prazos, condições comerciais, instalação).

Essa camada complementa o RAG por documentos do REQ-003 mas **tem precedência** sobre ele: a hierarquia de resposta é (1) Q&A curada com score acima do mínimo → (2) RAG por documentos → (3) qualificação/fluxo padrão (REQ-002) → (4) escalonamento (REQ-004).

Este requisito **formaliza** o sistema de Q&A Pairs já implementado parcialmente nas Sprints 1-2 (modelo `ParQA`, endpoints `/api/pares-qa/*`, UI `QABasePage`, modal de criação de par a partir de mensagem reprovada em `AcompanhamentoPage`, configuração dinâmica via `/api/config/rag`).

### 2.1 Relação com REQ-003 (RAG)

REQ-003 e REQ-013 compõem a camada de conhecimento do agente, mas operam em níveis diferentes:

| Aspecto | REQ-003 (RAG por documentos) | REQ-013 (Q&A curada) |
|---------|------------------------------|----------------------|
| Origem do conteúdo | Ingestão automática (catálogo, sites, documentos) | Curadoria manual + reprovações |
| Granularidade | Chunk de documento | Par pergunta/resposta atômico |
| Reescrita pelo LLM | **Sim** — resposta é gerada com base nos trechos | **Não** — resposta é entregue como está |
| Controle editorial | Indireto (depende do conteúdo ingerido) | Direto (vendedor escolhe palavra por palavra) |
| Custo de manutenção | Baixo (ingestão automática) | Médio-alto (curadoria humana) |
| Cobertura típica | Ampla, catálogo geral | Restrita a perguntas frequentes/sensíveis |
| Precedência na resposta | Segunda camada | **Primeira camada** |

**Regra de fronteira**: Q&A é para perguntas **estáveis e bem definidas** com resposta **curada e aprovada**. Conteúdo dinâmico, longo ou pouco repetitivo permanece no RAG documental.

### 2.2 Relação com REQ-011 e REQ-012

A base Q&A é **alimentada parcialmente** pelo workflow de reprovação (REQ-011) e pelos reports de problema (REQ-012):

- Quando uma mensagem é reprovada (REQ-011.7), o painel oferece a ação "criar par Q&A" a partir da pergunta original e de uma resposta corrigida pelo vendedor.
- Reports da categoria `resposta_inadequada` ou `template` (REQ-012.4) são candidatos naturais a virar pares Q&A.

A base também é alimentada por **ingestão direta** (sem passar por reprovação): cadastro manual no painel, importação de pastas de produtos, ou sugestão proativa do vendedor a partir de perguntas frequentes.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- O RAG documental (REQ-003) reescreve respostas via LLM, o que pode introduzir variação indesejada em respostas sensíveis (preços, prazos, condições).
- Conteúdo de catálogo nem sempre cobre perguntas frequentes do dia a dia ("vocês trabalham com X marca?", "qual o prazo para Y modelo?", "tem desconto à vista?").
- Reprovações de mensagens (REQ-011) precisam de um destino que **transforme o aprendizado em comportamento futuro do agente**, não apenas em report.

**Benefício Esperado**:
- **Controle editorial**: vendedor decide exatamente como o agente responde a perguntas críticas.
- **Aprendizado contínuo**: cada reprovação pode virar um par Q&A, fechando o ciclo "erro observado → correção curada → não erra mais".
- **Consistência**: mesmas perguntas geram mesmas respostas, eliminando variação do LLM em casos sensíveis.
- **Performance**: busca por similaridade vetorial é mais rápida e barata que RAG documental + LLM.

---

## 4. Critérios de Aceite

### 4.1 Modelo de Dados e Ciclo de Vida

- [ ] **REQ-013.1 — Estrutura mínima do par Q&A**: Cada par deve conter:
  - Pergunta (texto, obrigatório)
  - Resposta (texto, obrigatório)
  - Identificador externo único (`id_externo`) para deduplicação e rastreamento de origem (ex: `manual:abc123`, `reprovacao:msg_456`)
  - Contexto/categoria opcional (ex: `prazo`, `preco`, `instalacao`, `compatibilidade`) — texto livre por enquanto, mas a lista deve poder ser **consolidada em vocabulário controlado** em versão futura
  - Tags opcionais (lista de strings) para filtros adicionais
  - Autor (`criado_por`)
  - Timestamps de criação e atualização

- [ ] **REQ-013.2 — Workflow de aprovação do par**: Cada par tem dois estados booleanos independentes:
  - `aprovado`: indica que o par passou por curadoria humana e pode ser usado em busca semântica
  - `ativo`: indica que o par é elegível para ser retornado em buscas (soft delete usa `ativo=False`)

  **Regras**:
  - Pares são criados como `aprovado=False` e `ativo=True` (rascunho).
  - O embedding **só é gerado na aprovação** (lazy embedding), economizando custo em pares que não vão ser usados.
  - Apenas pares `aprovado=True` E `ativo=True` participam de buscas em produção.
  - Pares podem ser desativados (`ativo=False`) sem perder histórico (soft delete).

- [ ] **REQ-013.3 — Re-geração automática de embedding**: Quando a `pergunta` de um par for alterada, o embedding deve ser **re-gerado automaticamente** na atualização. Alterações apenas na `resposta`, `contexto` ou `tags` **não** disparam re-embedding (otimização de custo).

- [ ] **REQ-013.4 — Imutabilidade do histórico**: Pares Q&A não devem ser excluídos fisicamente. Casos de erro/duplicidade usam soft delete (`ativo=False`) com mantimento de `criado_por` e timestamps. Edições registram histórico em `atualizado_em` (alinha com REQ-005.7).

### 4.2 Origens de Criação

- [ ] **REQ-013.5 — Criação manual via painel**: O painel deve oferecer formulário para cadastro manual de par Q&A com todos os campos da REQ-013.1. Útil para curadoria proativa (não dependente de reprovação).

- [ ] **REQ-013.6 — Criação a partir de mensagem reprovada (REQ-011)**: Quando o vendedor reprovar uma mensagem da IA (REQ-011.7 / REQ-011.12), o painel deve oferecer ação "criar par Q&A a partir desta reprovação", pré-preenchendo:
  - `pergunta` ← mensagem do cliente que originou a resposta reprovada
  - `resposta` ← em branco (vendedor digita a resposta curada) ou pré-preenchida com sugestão editável
  - `id_externo` ← `reprovacao:<mensagem_id>` para rastrear origem
  - `criado_por` ← usuário que aprovou a criação

  O par criado entra como **rascunho** (`aprovado=False`); a aprovação é etapa explícita posterior.

- [ ] **REQ-013.7 — Criação a partir de report de problema (REQ-012)**: A partir do detalhe de um report (REQ-012.13), o painel deve oferecer ação análoga à REQ-013.6 quando a categoria for `resposta_inadequada` ou `template`. O par é vinculado ao report via `id_externo` (ex: `report:<report_id>`).

- [ ] **REQ-013.8 — Ingestão em lote a partir de pastas de produtos**: O sistema deve oferecer mecanismo (script CLI ou endpoint admin) para ingerir pares Q&A a partir de arquivos estruturados (markdown, CSV, JSON). Pares ingeridos:
  - Recebem `id_externo` baseado no arquivo de origem (ex: `produto_xyz.md:p3`)
  - Entram como **não aprovados** por padrão, exigindo curadoria antes de entrarem em produção
  - Podem ser aprovados em massa por usuário autorizado (ação explícita)

### 4.3 Busca e Uso em Produção

- [ ] **REQ-013.9 — Embedding sobre a pergunta**: O embedding usado em busca semântica é **gerado a partir da pergunta**, não da resposta. Isso maximiza similaridade cosseno com queries reais dos clientes.

- [ ] **REQ-013.10 — Threshold configurável de similaridade**: O sistema deve manter um **score mínimo** (`QA_SCORE_MINIMO`) configurável em runtime (REQ-013.13), abaixo do qual o resultado da busca Q&A é descartado. Sugestão de valor inicial: `0.85` em escala 0-1 de similaridade cosseno (calibrar com dados reais).

- [ ] **REQ-013.11 — Precedência sobre RAG documental**: Quando uma pergunta do cliente for processada (REQ-002 / REQ-003), a ordem de tentativa deve ser:
  1. **Buscar Q&A curada** (apenas pares `aprovado=True` E `ativo=True`).
  2. Se houver match com score ≥ `QA_SCORE_MINIMO`, **retornar a resposta curada como está**, sem passar pelo LLM.
  3. Se não houver match adequado, cair para o RAG documental (REQ-003).
  4. Se RAG documental também não tiver conteúdo suficiente, seguir REQ-003.7 (fallback).

- [ ] **REQ-013.12 — Filtro por contexto na busca**: A busca Q&A deve aceitar **filtro opcional por `contexto`**, permitindo restringir o universo (ex: "buscar apenas em pares de contexto `prazo`"). No POC o filtro pode ser desabilitado por default; em versões futuras pode ser usado por classificadores que detectam intent específica.

- [ ] **REQ-013.13 — Configuração dinâmica em runtime**: O sistema deve expor configuração em runtime (alinhada ao endpoint já existente `/api/config/rag`) com pelo menos:
  - `QA_ENABLED` — liga/desliga a camada Q&A globalmente
  - `QA_SCORE_MINIMO` — threshold de similaridade
  - Persistência: ao menos durante a sessão do servidor (POC); persistente entre reinícios em versão futura.

- [ ] **REQ-013.14 — Auditabilidade do uso**: Quando uma resposta for entregue via Q&A curada, o sistema deve registrar em `ProcessamentoMensagem` (REQ-005.6):
  - Que o caminho usado foi `qa_curada` (e não `rag_documental` ou `llm_generico`)
  - O `id` do par Q&A que foi usado
  - O score de similaridade

### 4.4 Operação e Curadoria

- [ ] **REQ-013.15 — Listagem com filtros**: O painel `QABasePage` deve listar pares Q&A com filtros por:
  - Status (`rascunho` = `aprovado=False`, `aprovado`, `desativado` = `ativo=False`)
  - Contexto
  - Tag
  - Texto livre (busca em pergunta/resposta)

- [ ] **REQ-013.16 — Visualização de par + ações**: A linha/card de cada par deve permitir, com no máximo dois cliques: editar, aprovar (se rascunho), desativar, ver origem (`id_externo`).

- [ ] **REQ-013.17 — Detecção de duplicatas na criação**: Ao criar um novo par, o sistema deve buscar pares existentes com pergunta similar (mesmo critério da busca em produção) e **alertar visualmente** o curador antes de gravar. Não impede a criação, mas evita duplicação inadvertida.

- [ ] **REQ-013.18 — Estatísticas básicas**: O painel deve mostrar contadores no cabeçalho:
  - Total de pares ativos e aprovados
  - Quantidade de rascunhos pendentes de aprovação
  - Pares mais usados nos últimos 7/30 dias (alinha com REQ-013.14)

### 4.5 Requisitos Não-Funcionais

- [ ] **REQ-013.19 — Tempo de busca**: Busca Q&A em produção deve responder em < 200ms para uma base de até 10 mil pares aprovados.

- [ ] **REQ-013.20 — Tempo de geração de embedding**: Geração de embedding na aprovação deve completar em < 3s (depende do provedor LLM).

- [ ] **REQ-013.21 — Custo controlado**: Embedding lazy (REQ-013.2) e re-embedding seletivo (REQ-013.3) são obrigatórios para manter custo proporcional ao volume curado, não ao volume total cadastrado.

- [ ] **REQ-013.22 — Compatibilidade com pgvector**: A coluna de embedding deve usar `pgvector` (já adotado no projeto), com índice apropriado para busca por similaridade cosseno em escala.

---

## 5. Modelo de Dados (alto nível)

> **Nota:** os campos abaixo já existem no modelo `ParQA` em `backend/models.py:629`. Este REQ formaliza o que está implementado e fixa as regras de uso.

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `id` | int | sim | PK auto-incremento |
| `id_externo` | string | sim | Único; rastreia origem (manual, reprovacao, report, ingestao) |
| `pergunta` | text | sim | Base do embedding |
| `resposta` | text | sim | Entregue como está |
| `contexto` | string | opcional | Categoria livre; futuro: vocabulário controlado |
| `tags` | array<string> | opcional | Filtros adicionais |
| `embedding` | vector(1536) | gerado na aprovação | pgvector |
| `ativo` | bool | sim | Default `true`; soft delete |
| `aprovado` | bool | sim | Default `false`; gate para busca |
| `criado_por` | string | sim | Usuário (POC: usuário único) |
| `criado_em` / `atualizado_em` | datetime | sim | Auditoria padrão |

---

## 6. Fluxos (alto nível)

### 6.1 Reprovação de mensagem → criação de par Q&A

```
1) Vendedor reprova mensagem da IA (REQ-011.7)
2) Sistema cria report automático (REQ-012.2)
3) Vendedor abre detalhe da reprovação e clica "criar par Q&A"
4) Painel pré-preenche pergunta = mensagem do cliente
5) Vendedor escreve a resposta curada e (opcional) ajusta contexto/tags
6) Sistema persiste como rascunho (aprovado=false), sem embedding
7) Curador aprova o par → embedding gerado → par entra em produção
```

### 6.2 Atendimento a uma pergunta

```
1) Cliente envia pergunta
2) Sistema gera embedding da pergunta
3) Busca em pares_qa onde aprovado=true e ativo=true
4) Top 1 com score >= QA_SCORE_MINIMO?
   SIM → entrega resposta curada como está; registra processamento (REQ-013.14)
   NÃO → cai para RAG documental (REQ-003)
5) Se RAG documental também não atender → fallback (REQ-003.7)
```

### 6.3 Curadoria proativa

```
1) Curador identifica pergunta frequente sem cobertura
2) Cria par manual no painel (REQ-013.5)
3) Aprova o par
4) Próximas ocorrências dessa pergunta passam a ser respondidas pela Q&A
```

---

## 7. Limitações Aceitas no POC

- [ ] Vocabulário de `contexto` é texto livre — sem normalização forçada.
- [ ] Sem A/B testing entre resposta curada e resposta gerada (toda match passa direto).
- [ ] Sem versionamento de par (edições sobrescrevem; histórico só por `atualizado_em`).
- [ ] Sem multi-idioma — pares assumem PT-BR.
- [ ] Configuração dinâmica (REQ-013.13) é volátil entre reinícios do servidor; persistência em arquivo/banco fica para versão futura.
- [ ] Aprovação em massa (REQ-013.8) sem fluxo de revisão por par individual; fica para versão futura quando volume crescer.
- [ ] Detecção de duplicatas (REQ-013.17) é alerta, não bloqueio.
- [ ] Sem analytics avançado (taxa de match, drift de score) além dos contadores básicos da REQ-013.18.

---

## 8. Dependências

### 8.1 Dependências Técnicas
- REQ-003 (RAG) — Q&A é primeira camada antes do RAG documental
- REQ-005 (histórico) — para `ProcessamentoMensagem` registrar uso de Q&A
- REQ-010 (painel administrativo) — UI `QABasePage`
- REQ-011 e REQ-012 — fontes de criação de par via reprovação/report
- pgvector + provider de embeddings (já configurado)
- Modelo `ParQA` + endpoints `/api/pares-qa/*` + endpoint `/api/config/rag` já implementados

### 8.2 Dependências de Negócio
- Definir vocabulário inicial de `contexto` (mesmo que como guia, não como restrição)
- Calibrar `QA_SCORE_MINIMO` com base em dados reais (sugestão inicial: `0.85`)

---

## 9. Restrições e Limitações

- Q&A curada **não substitui** o RAG documental — ela complementa em casos sensíveis. Ingestão de catálogo inteiro como Q&A é antipattern (mata a vantagem da curadoria).
- Q&A curada **não substitui** o classificador (REQ-002) — apenas perguntas que viram match com score adequado são respondidas direto. Demais perguntas seguem o fluxo normal.
- Resposta curada **não passa pelo LLM**, então o curador é responsável por garantir que ela está completa, em PT-BR e respeita as regras de negócio (não prometer prazo, não negociar desconto — REQ-003.6 / REQ-003.8).

---

## 10. Critérios de Sucesso

### 10.1 Métricas
- **Cobertura**: ≥ 30% das perguntas frequentes (top 50 mais repetidas) cobertas por Q&A curada após 1 mês de operação.
- **Precisão**: < 5% das respostas via Q&A geram report de problema (REQ-012) reabrindo o caso.
- **Drift do threshold**: revisão mensal de `QA_SCORE_MINIMO` se taxa de falsos positivos > 10%.
- **Volume de curadoria**: ≥ 50% das mensagens reprovadas (REQ-011.7) viram par Q&A em até 7 dias.

### 10.2 Condições de Aceite Final
- Vendedor consegue criar par Q&A a partir de reprovação em < 1 minuto.
- Curador consegue revisar e aprovar pares pendentes na tela `QABasePage`.
- Quando uma pergunta tem match Q&A, o sistema entrega a resposta curada **sem reescrever** via LLM.
- Configuração `QA_ENABLED=false` desativa completamente a camada Q&A em runtime sem reiniciar o servidor.

---

## 11. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Falsos positivos (match Q&A que não deveria) | Média | Alto | `QA_SCORE_MINIMO` configurável (REQ-013.13); revisão mensal; fallback para RAG quando score limítrofe |
| Resposta curada desatualizada (preço mudou, modelo descontinuado) | Alta | Alto | Revisão periódica obrigatória; campo `atualizado_em` para identificar pares antigos; possibilidade de adicionar "validade" em versão futura |
| Curadoria não acompanha volume de reprovações | Alta | Médio | Estatísticas (REQ-013.18) destacam rascunhos pendentes; SLA visual para itens há muito tempo sem aprovação |
| Duplicação de pares com perguntas similares | Média | Baixo | Detecção de duplicatas na criação (REQ-013.17) |
| Q&A respondendo perguntas que mereciam fluxo de qualificação (REQ-002) | Média | Médio | Curadoria deve evitar pares cobrindo intenções de qualificação; REQ-003.10 (não acionar respostas para qualificação) replica regra |
| Embedding lazy não gerado por bug → par "aprovado" sem embedding | Baixa | Médio | Validação no endpoint de aprovação; busca filtra `embedding IS NOT NULL`; healthcheck identifica pares aprovados sem embedding |

---

## 12. Estimativas

> **Nota:** parte significativa já está implementada nas Sprints 1-2. As estimativas abaixo cobrem **gaps** entre o estado atual e os critérios de aceite deste REQ.

| Atividade | Horas |
|-----------|-------|
| Validação dos campos atuais do `ParQA` contra REQ-013.1/.2 | 2h |
| Garantir lazy embedding e re-embedding seletivo (REQ-013.2/.3) — verificar fluxo atual | 3h |
| Endpoint/ação "criar par Q&A a partir de report" (REQ-013.7) | 3h |
| Filtro por contexto na busca em produção (REQ-013.12) | 2h |
| Auditoria do uso de Q&A em `ProcessamentoMensagem` (REQ-013.14) | 3h |
| Detecção de duplicatas na criação (REQ-013.17) | 4h |
| Estatísticas no cabeçalho da `QABasePage` (REQ-013.18) | 3h |
| Persistência de `QA_ENABLED` / `QA_SCORE_MINIMO` em runtime — verificar `/api/config/rag` | 2h |
| Testes (busca, lazy embedding, precedência sobre RAG, soft delete) | 6h |
| Documentação operacional para curadores | 2h |
| **Total** | **30h** |

---

## 13. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 18/05/2026 | 1.0 | Criação inicial do requisito formalizando a base de pares Q&A curados (modelo `ParQA`, endpoints `/api/pares-qa/*`, UI `QABasePage`, modal de criação a partir de reprovação) já parcialmente implementado nas Sprints 1-2. Estabelece precedência sobre RAG documental (REQ-003), origens de criação (manual, reprovação REQ-011, report REQ-012, ingestão em lote) e regras de embedding lazy. | Kika |

---

## 14. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 18/05/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
