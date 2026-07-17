# REQ-012: Reports de Problema — Captura, Triagem e Evolução do Agente

<!-- CLASSIFICACAO: SISTEMA-CAIXAPRETA -->
<!-- CLASSIFICACAO: IA -->

**Versão**: 1.1
**Data**: 2026-05-18
**Autor**: Kika (Analista de Requisitos)
**Status**: Em Elaboração
**Prioridade**: Média

---

## 1. Identificação do Requisito

**ID**: REQ-012
**Tipo**: Funcional
**Categoria**: Qualidade do Agente / Observabilidade / Melhoria Contínua
**Solicitante**: Necessidade do produto (operação do vendedor + evolução do cérebro do assistente)

---

## 2. Descrição

O sistema deve oferecer um mecanismo estruturado para que usuários (vendedor, coordenador, desenvolvedor) **registrem problemas** observados no comportamento do agente — seja em mensagens reprovadas, classificações erradas, fluxos que tomaram decisões inadequadas, falhas de LLM ou inconsistências de dados — e o sistema deve suportar **triagem, acompanhamento e resolução** desses reports.

O objetivo é transformar **observações operacionais** (feitas no dia a dia pelo vendedor ou pelo time técnico) em **artefatos rastreáveis** que alimentam a evolução do cérebro do assistente: ajustes de prompts, regras do classificador, conteúdo da base RAG/Q&A (REQ-003 / REQ-011), correção de bugs, etc.

Este requisito **formaliza** o sistema de reports já implementado parcialmente no código (modelo `ReportProblema`, endpoints `/api/reports/*`, UI `ReportsPage` + `ReportDetalhe`), eliminando dívida de rastreabilidade e definindo critérios mínimos de qualidade.

### 2.1 Relação com REQ-011 (fronteira explícita)

REQ-011 e REQ-012 se tocam, mas têm papéis distintos:

- **REQ-011** é dono da **decisão de envio** de uma mensagem da IA (aprovar / reprovar / editar) e do **modo de execução** do sistema (`simulacao` / `conversa_controlada` / `execucao_normal`). É quem decide se a mensagem **vai ou não vai** para o cliente.
- **REQ-012** é dono da **gestão de defeitos** do agente — captura, triagem, ciclo de vida e resolução de problemas observados, independentemente de quando foram observados.

A única ponte automática entre eles é o **REQ-012.2**: uma reprovação em REQ-011 dispara a criação de um report em REQ-012. A partir daí o report **vive sob REQ-012** e REQ-011 não interage mais com ele.

Analogia: REQ-011 é o **inspetor da linha de produção** (vai/não vai); REQ-012 é o **departamento de qualidade** (classifica defeitos, investiga, acompanha resolução).

### 2.2 Fontes de report (entradas deste REQ)

REQ-012 é o **funil único** de captura de problemas do agente. REQ-011 é apenas **uma das fontes** — a mais frequente, mas não a única.

| Origem | REQ que dispara | Modo de criação | Observação |
|--------|-----------------|------------------|------------|
| Reprovação de mensagem da IA (modos `simulacao` e `conversa_controlada`) | REQ-011.7 / REQ-011.12 → REQ-012.2 | **Automático** | Categoria default `resposta_inadequada`, severidade `media`, descrição = feedback do vendedor |
| Edição de mensagem antes de aprovar | REQ-011.15 → REQ-012.2A | **Automático** | Sinaliza que o texto original era subótimo; categoria default `template` |
| Feedback retroativo sobre mensagem da IA enviada (modo `execucao_normal`) | REQ-011.17 → REQ-012.3 | **Manual avulso** | Vendedor abre detalhe da mensagem e clica "Reportar problema" |
| Feedback retroativo sobre mensagem **manual** (pós-POC) | REQ-011.17A → REQ-012.3 | **Manual avulso** | Coordenador avalia mensagem enviada manualmente; também dispara envio de sugestão ao WhatsApp do vendedor (específico do REQ-011.17A) |
| Observação técnica avulsa (LLM travou, RAG trouxe trecho irrelevante, fluxo errado) | REQ-012.3 direto | **Manual avulso** | Sem REQ-011 envolvido; reportado por desenvolvedor ou triador |

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Sem um canal estruturado para reportar problemas, defeitos do agente se perdem em conversas paralelas (chat, e-mail, WhatsApp do time).
- Não há vínculo claro entre "essa resposta saiu errada" e "qual processamento gerou essa resposta", dificultando o diagnóstico.
- Reprovações de mensagens (REQ-011.7 / REQ-011.12) e feedbacks retroativos (REQ-011.17) precisam de um destino organizado para virar ação corretiva.

**Benefício Esperado**:
- **Rastreabilidade**: cada problema reportado fica vinculado ao processamento, mensagem, cliente e autor do report.
- **Priorização**: triagem por categoria/severidade permite focar nos defeitos mais críticos primeiro.
- **Aprendizado contínuo**: histórico de reports orienta evolução do classificador (REQ-002), do RAG (REQ-003) e dos prompts.
- **Visibilidade da qualidade**: estatísticas agregadas mostram tendências (mais reports em X categoria → atenção na sprint).

---

## 4. Critérios de Aceite

### 4.1 Captura do Report

- [ ] **REQ-012.1 — Criação de report a partir de um processamento**: O sistema deve permitir criar um report de problema vinculado a um **processamento de mensagem** (REQ-005.6), capturando:
  - Descrição em texto livre (obrigatória, mínimo 10 caracteres)
  - Categoria (REQ-012.4)
  - Severidade (REQ-012.5)
  - Autor do report (usuário identificado — REQ-010.2)
  - Vínculo opcional à `mensagem_id` específica que motivou o report (quando aplicável)
  - Timestamp de criação

- [ ] **REQ-012.2 — Criação automática a partir de reprovação de mensagem**: Quando o vendedor reprovar uma mensagem da IA (REQ-011.7 / REQ-011.12), o sistema deve gerar **automaticamente** um report associado:
  - Categoria default: `resposta_inadequada`
  - Severidade default: `media` (editável posteriormente na triagem)
  - Descrição: feedback textual fornecido na reprovação (REQ-011.7)
  - Vínculo à mensagem reprovada e ao processamento que a originou
  - Status inicial: `aberto`

- [ ] **REQ-012.2A — Criação automática a partir de edição de mensagem antes de aprovar**: Quando o vendedor editar o texto de uma mensagem pendente antes de aprová-la (REQ-011.15), o sistema deve gerar **automaticamente** um report associado:
  - Categoria default: `template`
  - Severidade default: `baixa` (editável posteriormente na triagem)
  - Descrição: motivo da edição (feedback do vendedor) + diferença entre texto original e texto editado (referência ou diff resumido)
  - Vínculo à mensagem editada e ao processamento que a originou
  - Status inicial: `aberto`

  **Justificativa**: uma edição significa que o texto gerado pela IA era subótimo. Registrar como report alimenta a melhoria contínua do prompt/template, mesmo quando o desfecho final foi positivo (mensagem aprovada e enviada).

  *Dependência: REQ-011.15 é opcional no POC; este subitem só entra em vigor quando REQ-011.15 for implementado.*

- [ ] **REQ-012.3 — Criação manual avulsa**: O painel deve permitir criação manual de report a partir da tela de detalhes de um atendimento ou processamento, **sem** depender de uma reprovação prévia. Útil para registrar:
  - Problemas observados em mensagens já enviadas em `execucao_normal` (alinha com REQ-011.17)
  - Problemas estruturais (ex: classificador errou intenção; RAG trouxe trecho irrelevante; LLM travou)
  - Sugestões de melhoria que não justificam reprovação imediata

### 4.2 Categorização e Triagem

- [ ] **REQ-012.4 — Categorias do report**: O sistema deve suportar, no mínimo, as seguintes categorias, indicando a **camada afetada**:
  - `classificacao` — intenção/entidades extraídas erradas
  - `fluxo` — orquestração/roteamento errado (próxima pergunta, transição de estado)
  - `template` — texto/tom da resposta inadequado
  - `resposta_inadequada` — resposta do agente gerada por IA inadequada (típica de reprovação)
  - `dados` — dados incorretos (CNPJ inválido aceito, contato confundido, etc.)
  - `llm` — problema técnico com a LLM (timeout, erro de API, resposta vazia)
  - `outro` — fallback para casos não previstos

  A lista deve ser **extensível** (futuras categorias adicionadas sem refatoração estrutural).

- [ ] **REQ-012.5 — Severidades do report**: O sistema deve suportar quatro níveis de severidade:
  - `baixa` — não impede atendimento; melhoria desejável
  - `media` — afeta qualidade mas o atendimento prossegue (default)
  - `alta` — afeta materialmente a experiência do cliente; precisa atenção rápida
  - `critica` — bloqueia/prejudica o cliente seriamente; ação imediata recomendada

- [ ] **REQ-012.6 — Workflow de status**: Cada report deve evoluir em um workflow com os seguintes estados:
  - `aberto` — recém-criado, ainda não triado
  - `em_analise` — sendo investigado pelo time técnico
  - `aguardando_fix` — diagnóstico feito, aguardando correção
  - `resolvido` — correção aplicada e verificada
  - `descartado` — reportado mas não considerado problema (falso positivo, fora de escopo, duplicado)

  **Transições válidas**:
  - `aberto` → `em_analise` ou `descartado`
  - `em_analise` → `aguardando_fix`, `resolvido` ou `descartado`
  - `aguardando_fix` → `resolvido` ou `em_analise` (reabertura)
  - `resolvido` → `em_analise` (apenas em correção explícita)
  - `descartado` → terminal (apenas correção explícita o reabre)

  Toda transição registra timestamp, ator e (opcional) observação curta.

### 4.3 Resolução e Auditoria

- [ ] **REQ-012.7 — Registro de resolução**: Ao mover um report para `resolvido` ou `descartado`, o sistema deve permitir registrar:
  - Texto livre com **descrição da resolução** (o que foi feito) ou **motivo do descarte**
  - Identificação de quem resolveu (`resolvido_por`)
  - Timestamp da resolução

- [ ] **REQ-012.8 — Imutabilidade do histórico**: Reports não devem ser **excluídos** do banco. Para casos de erro de digitação ou duplicidade, usar `descartado` com descrição clara. Edições de descrição/categoria/severidade são permitidas durante triagem mas devem registrar histórico de alterações (alinha com REQ-005.7).

### 4.4 Consulta e Visualização

- [ ] **REQ-012.9 — Listagem com filtros**: O painel deve oferecer listagem de reports com filtros por:
  - Status (um ou múltiplos)
  - Categoria
  - Severidade
  - Período de criação
  - Autor
  - Texto livre na descrição/resolução

- [ ] **REQ-012.10 — Estatísticas agregadas**: O painel deve exibir contadores rápidos no cabeçalho da tela de reports, mostrando:
  - Quantidade total
  - Quantidade por status (ao menos `aberto`, `em_analise`, `resolvido`, `descartado`)
  - Quantidade por categoria (top 5)
  - Quantidade por severidade

- [ ] **REQ-012.11 — Detalhe do report com contexto da conversa**: Ao abrir um report, o painel deve mostrar:
  - Todos os campos do report (descrição, categoria, severidade, status, autor, datas)
  - Resumo do processamento associado (intenção classificada, confiança, trechos RAG usados, resposta gerada)
  - **Janela de contexto da conversa**: mensagens **antes** e **depois** da mensagem reportada (sugestão default: 3 antes + 3 depois, configurável), para que o triador entenda o cenário

- [ ] **REQ-012.12 — Vínculo bidirecional com processamento e mensagem**: A partir do detalhe de um atendimento/mensagem, deve ser possível ver os reports associados; a partir de um report, deve ser possível navegar para o processamento e a mensagem originais.

### 4.5 Integração com outros módulos

- [ ] **REQ-012.13 — Reports como insumo para curadoria de Q&A**: Reports da categoria `resposta_inadequada` ou `template` devem ser candidatos naturais a virar pares Q&A curados (REQ-003 / sistema Q&A). O painel pode oferecer ação de "criar par Q&A a partir deste report" (já implementado parcialmente na reprovação — alinhar fluxos).

- [ ] **REQ-012.14 — Reports não disparam ação automática**: Criar ou triar um report **não deve** alterar comportamento do agente em produção (não muda prompts, não desativa fluxos, não bloqueia respostas). Reports são insumo para **decisão humana** sobre correção; mudanças efetivas no agente seguem fluxo de implementação normal (`[implementador]`).

### 4.6 Requisitos Não-Funcionais

- [ ] **REQ-012.15 — Tempo de resposta da listagem**: A tela de reports deve carregar a listagem em menos de 2 segundos para volumes do POC (até alguns milhares de reports).

- [ ] **REQ-012.16 — Tempo de resposta do detalhe**: A tela de detalhe (com janela de contexto) deve carregar em menos de 3 segundos.

- [ ] **REQ-012.17 — Identificação do autor**: Todo report deve ter autor identificado. No POC, o autor é o usuário único do painel (REQ-010.3); pós-POC, deve refletir o usuário autenticado (REQ-010.1 / REQ-010.2).

---

## 5. Modelo de Dados (alto nível)

> **Nota:** os campos abaixo já existem no modelo `ReportProblema` em `backend/models.py`. Este REQ formaliza o que está implementado e fixa as regras de uso.

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `id` | int | sim | PK auto-incremento |
| `processamento_id` | int (FK) | recomendado | Vincula ao `ProcessamentoMensagem` (REQ-005.6) |
| `mensagem_id` | int (FK) | opcional | Vincula à mensagem específica reportada |
| `descricao` | text | sim | Mínimo 10 caracteres |
| `autor` | string | sim (POC: usuário único) | Identificação humana |
| `categoria` | enum | sim | Ver REQ-012.4 |
| `severidade` | enum | sim | Default: `media` |
| `status` | enum | sim | Default: `aberto` |
| `resolucao` | text | quando `resolvido`/`descartado` | Texto livre |
| `resolvido_por` | string | idem | Identificação humana |
| `resolvido_em` | datetime | idem | Timestamp |
| `created_at` / `updated_at` | datetime | sim | Auditoria padrão |

---

## 6. Fluxos (alto nível)

### 6.1 Reprovação de mensagem → report automático

```
1) Vendedor reprova mensagem da IA (REQ-011.7 / REQ-011.12) com feedback textual
2) Sistema cria report:
   - categoria = resposta_inadequada
   - severidade = media
   - descricao = feedback do vendedor
   - status = aberto
   - vínculos: processamento_id + mensagem_id
3) Report aparece na tela de Reports para triagem posterior
```

### 6.2 Triagem manual

```
1) Triador abre tela de Reports filtrada por status=aberto
2) Para cada report:
   a) Lê descrição e contexto da conversa (REQ-012.11)
   b) Ajusta categoria/severidade se necessário
   c) Move para em_analise OU descartado
3) Reports em_analise viram tarefas para o time técnico
4) Após correção, triador move para resolvido com descrição
```

### 6.3 Report manual avulso

```
1) Usuário identifica problema em uma conversa (em qualquer modo)
2) Abre detalhe da mensagem/processamento e clica "Reportar problema"
3) Preenche descrição, categoria e severidade
4) Sistema cria report com status=aberto
```

---

## 7. Limitações Aceitas no POC

- [ ] Sem notificações automáticas (push/e-mail) ao criar report.
- [ ] Sem SLA configurável por severidade — apenas registro do tempo de criação/resolução.
- [ ] Sem atribuição de "responsável pela correção" — qualquer usuário pode triar/resolver.
- [ ] Sem integração com ferramentas externas de issue tracking (Jira, GitHub Issues, etc.).
- [ ] Sem tags/labels customizáveis além das categorias predefinidas.
- [ ] Sem comentários/discussão em thread no report — apenas o campo `resolucao`.
- [ ] Sem detecção automática de reports duplicados.

---

## 8. Dependências

### 8.1 Dependências Técnicas
- REQ-005 — `ProcessamentoMensagem` precisa existir para vincular reports
- REQ-010 — Painel administrativo (telas + autenticação)
- REQ-011 — Workflow de aprovação/reprovação (gera reports automáticos)
- Modelo `ReportProblema` e endpoints `/api/reports/*` já implementados

### 8.2 Dependências de Negócio
- Definir quem triamente reports no time (POC: vendedor + Beto; pós-POC: papel formal)
- Acordar critérios de severidade (o que é `alta` vs `critica`)

---

## 9. Restrições e Limitações

- Reports são **artefatos de melhoria contínua**, não substituem o canal de escalonamento ao cliente (REQ-004) nem o tratamento de reclamações pós-venda (REQ-009).
- Reports **não** devem ser usados como mecanismo de comunicação entre vendedor e cliente — apenas como registro interno de qualidade do agente.

---

## 10. Critérios de Sucesso

### 10.1 Métricas
- **Taxa de triagem**: ≥ 80% dos reports `aberto` triados em até 7 dias (média móvel mensal).
- **Tempo médio de resolução**: alvo < 14 dias para `resolvido` ou `descartado` em severidade `media`/`alta`.
- **Razão de descarte**: < 30% dos reports terminam em `descartado` (acima disso indica que a captura está pouco filtrada na origem).

### 10.2 Condições de Aceite Final
- Vendedor consegue criar report de qualquer mensagem/processamento em até 3 cliques.
- Triador vê estatísticas agregadas no cabeçalho da tela de reports.
- Reports gerados automaticamente por reprovação ficam corretamente vinculados ao processamento e à mensagem.
- Histórico de status de cada report é auditável.

---

## 11. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Acúmulo de reports `aberto` sem triagem (vira "caixa preta") | Alta | Médio | Cabeçalho com contadores (REQ-012.10); revisão semanal pelo `[gerente]` |
| Reports muito vagos (descrição "ruim") | Alta | Médio | Mínimo 10 caracteres na descrição; orientação ao vendedor sobre o que escrever |
| Mesma issue reportada várias vezes | Média | Baixo | Listagem com busca textual (REQ-012.9); duplicados podem ser `descartados` com referência ao original |
| Triagem inconsistente entre triadores | Média | Médio | Definir guia de severidade/categoria antes de habilitar múltiplos triadores (pós-POC) |
| Reports usados como canal de "vent" sem ação corretiva | Baixa | Baixo | Métrica de razão de descarte (10.1) sinaliza o problema |

---

## 12. Estimativas

> **Nota:** parte significativa já está implementada. As estimativas abaixo cobrem **gaps** entre o estado atual do código e os critérios de aceite deste REQ.

| Atividade | Horas |
|-----------|-------|
| Validação dos campos atuais do `ReportProblema` contra REQ-012.1/.4/.5/.6 | 2h |
| Garantir criação automática a partir de reprovação (REQ-012.2) — verificar fluxo atual | 3h |
| Adicionar histórico de transições de status com ator/observação (REQ-012.6) | 4h |
| Filtros faltantes na listagem (REQ-012.9) | 3h |
| Janela de contexto da conversa no detalhe (REQ-012.11) — verificar `/api/reports/{id}/contexto` | 2h |
| Botão "criar par Q&A a partir deste report" (REQ-012.13) | 3h |
| Testes (criação automática, triagem, resolução, filtros) | 5h |
| Documentação operacional para triadores | 2h |
| **Total** | **24h** |

---

## 13. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 18/05/2026 | 1.0 | Criação inicial do requisito formalizando o sistema de reports de problema (modelo `ReportProblema`, endpoints `/api/reports/*`, UI `ReportsPage` + `ReportDetalhe`) já parcialmente implementado nas Sprints 1-2. | Kika |
| 18/05/2026 | 1.1 | Adicionada §2.1 ("Relação com REQ-011 — fronteira explícita") e §2.2 ("Fontes de report"), tornando explícita a divisão de responsabilidades entre REQ-011 (decisão de envio) e REQ-012 (gestão de defeitos). Adicionado REQ-012.2A cobrindo criação automática de report a partir de edição em REQ-011.15. | Kika |

---

## 14. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 18/05/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
