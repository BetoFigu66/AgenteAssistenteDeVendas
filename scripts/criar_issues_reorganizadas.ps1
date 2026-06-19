<#
.SYNOPSIS
  Cria as 16 issues reorganizadas por funcionalidade entregavel e testavel.

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/proposta_reorganizacao_issues.md
  Substitui os scripts antigos de criacao granular (criar_issues_req001, req002, req013, req015, req016).

  Issues criadas (16 no total):
    Sprint 03: REQ-016-F01, REQ-016-F02, REQ-001-F01, REQ-001-F02,
               REQ-002-F01, REQ-002-F02, REQ-013-F01, REQ-013-F02, REQ-015-F01
    Sprint 04: REQ-016-F03, REQ-016-F04, REQ-002-F03, REQ-002-F04,
               REQ-013-F03, REQ-015-F02, REQ-015-F03

.PARAMETER DryRun
  Imprime os comandos sem executa-los.

.EXAMPLE
  .\scripts\criar_issues_reorganizadas.ps1 -DryRun
  .\scripts\criar_issues_reorganizadas.ps1
#>

[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = "Stop"

function Invoke-Gh {
  param([string[]]$Arguments)
  $cmd = "gh " + ($Arguments -join " ")
  if ($DryRun) { Write-Host "[DRY] $cmd" -ForegroundColor Yellow; return }
  Write-Host "> $cmd" -ForegroundColor Cyan
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & gh @Arguments 2>$null
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $prev
  if ($exitCode -ne 0) { throw "Falhou: $cmd (exit $exitCode)" }
}

function New-Issue {
  param(
    [string]$Title,
    [string]$Body,
    [string]$Labels,
    [string]$Milestone
  )
  if ($DryRun) {
    Write-Host "[DRY] gh issue create --title `"$Title`" --body-file <tmp> --label `"$Labels`" --milestone `"$Milestone`"" -ForegroundColor Yellow
    return
  }
  $tmp = [System.IO.Path]::GetTempFileName()
  try {
    [System.IO.File]::WriteAllText($tmp, $Body, [System.Text.Encoding]::UTF8)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & gh issue create --title $Title --body-file $tmp --label $Labels --milestone $Milestone 2>$null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($exitCode -ne 0) { throw "Falhou ao criar issue '$Title' (exit $exitCode)" }
  } finally {
    Remove-Item $tmp -ErrorAction SilentlyContinue
  }
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
Write-Host "== Pre-flight ==" -ForegroundColor Green
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& gh --version *>$null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh CLI nao instalado." }
& gh auth status *>$null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh nao autenticado. Rode: gh auth login" }
$ErrorActionPreference = $prevEAP
Write-Host "Auth OK." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Labels adicionais
# ---------------------------------------------------------------------------
Write-Host "`n== Labels adicionais ==" -ForegroundColor Green
$extraLabels = @(
  @{ name = "REQ-001"; color = "ededed"; desc = "Integracao Receita Federal (CNPJ)" },
  @{ name = "REQ-002"; color = "ededed"; desc = "Fluxo conversacional guiado" },
  @{ name = "REQ-003"; color = "ededed"; desc = "Base documental RAG" },
  @{ name = "REQ-004"; color = "ededed"; desc = "Escalonamento humano" },
  @{ name = "REQ-005"; color = "ededed"; desc = "Registro de interacoes / auditoria" },
  @{ name = "REQ-008"; color = "ededed"; desc = "Reengajamento / abandono" },
  @{ name = "REQ-010"; color = "ededed"; desc = "Painel administrativo" },
  @{ name = "REQ-012"; color = "ededed"; desc = "Reports de problema" },
  @{ name = "REQ-013"; color = "ededed"; desc = "Pares Q&A curados" },
  @{ name = "REQ-014"; color = "ededed"; desc = "Configuracao runtime camadas conhecimento" },
  @{ name = "REQ-015"; color = "ededed"; desc = "Validacao CPF + Consulta Debitos" },
  @{ name = "REQ-016"; color = "ededed"; desc = "Renomeacao Negociacao -> Atendimento" }
)
$existingLabelsJson = gh label list --limit 200 --json name 2>$null
$existingLabelNames = @()
if ($existingLabelsJson) {
  $existingLabelNames = ($existingLabelsJson | ConvertFrom-Json) | ForEach-Object { $_.name }
}
foreach ($l in $extraLabels) {
  if ($existingLabelNames -contains $l.name) {
    Write-Host "  label '$($l.name)' ja existe - pulando" -ForegroundColor DarkGray; continue
  }
  Invoke-Gh @("label", "create", $l.name, "--color", $l.color, "--description", $l.desc)
}

# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------
Write-Host "`n== Milestones ==" -ForegroundColor Green
$milestonesJson = gh api '/repos/{owner}/{repo}/milestones?state=open&per_page=50' 2>$null
$milestones = @{}
if ($milestonesJson) {
  ($milestonesJson | ConvertFrom-Json) | ForEach-Object { $milestones[$_.title] = $_.number }
}
foreach ($ms in @("Sprint 03", "Sprint 04")) {
  if ($milestones.ContainsKey($ms)) {
    Write-Host "  milestone '$ms' OK (#$($milestones[$ms]))" -ForegroundColor DarkGray
  } else {
    throw "Milestone '$ms' nao encontrado. Rode .\scripts\bootstrap_github_projects.ps1"
  }
}

# ---------------------------------------------------------------------------
# Idempotencia
# ---------------------------------------------------------------------------
Write-Host "`n== Idempotencia ==" -ForegroundColor Green
$existingIssuesJson = gh issue list --state open --limit 500 --json title 2>$null
$existingIssueTitles = @()
if ($existingIssuesJson) {
  $existingIssueTitles = ($existingIssuesJson | ConvertFrom-Json) | ForEach-Object { $_.title }
}

# ---------------------------------------------------------------------------
# Issues — Sprint 03
# ---------------------------------------------------------------------------
Write-Host "`n== Criando issues Sprint 03 ==" -ForegroundColor Green

$issuesSprint03 = @(

  # ---- REQ-016 ----
  @{
    title = "[REQ-016] F01 -- Migracao completa do modelo negociacao para atendimento"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-016"
    body = @"
## Descricao

Renomear o conceito de "negociacao" para "atendimento" em toda a stack: banco de dados, codigo Python e interface do usuario. Inclui a migration de rename de tabelas/colunas, a restricao do ciclo de vida do atendimento aos estados ativo/encerrado, o refactor completo do codigo Python e as atualizacoes visuais no frontend.

## Criterio de aceite

A funcionalidade esta pronta quando o painel exibir "Atendimento #N" no lugar de "Negociacao", sem regressao visivel nas telas principais, e pytest backend/tests passar.

## Subtarefas

- [ ] **T-A1** -- Migration Alembic: rename negociacoes -> atendimentos, colunas e FKs
- [ ] **T-A1b** -- Migration Alembic: drop dos estados antigos com remapeamento para ativo/encerrado e coluna motivo_encerramento
- [ ] **T-A2** -- Refactor Python: models, schemas, services e rotas (/api/negociacoes/* -> /api/atendimentos/*)
- [ ] **T-A11** -- Frontend: renomear labels, badges, breadcrumbs e rotas de /negociacoes/* -> /atendimentos/*

## Validacao funcional

- alembic upgrade head e alembic downgrade -1 rodam limpos
- grep -ri negocia backend/ retorna zero matches relevantes
- Navegar pelo painel nao exibe mais "Negociacao" em nenhum label visivel

## Roteiros de teste

> REQ-016 ainda nao possui roteiro RT-* dedicado. Validar manualmente pelos criterios acima apos implementacao.
> Acompanhar: artefatos/qa/roteiros_teste/indice_cobertura_reqs.md

## Branch sugerida

feature/migration-rename-atendimentos
"@
  },

  @{
    title = "[REQ-016] F02 -- Criacao automatica de atendimento com numeracao sequencial"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,REQ-016,REQ-014"
    body = @"
## Descricao

Centralizar a criacao de atendimentos em um servico dedicado (services/atendimentos.py), adicionar rastreamento de timestamp da ultima mensagem e expor o parametro de janela de continuacao via configuracao de runtime.

## Criterio de aceite

Telefone novo envia mensagem -> painel mostra "Atendimento #1". Segundo atendimento do mesmo telefone -> "Atendimento #2". Timestamp da ultima mensagem atualiza em tempo real.

## Subtarefas

- [ ] **T-A3** -- Coluna ultima_mensagem_at no atendimento + atualizacao a cada mensagem recebida
- [ ] **T-A4** -- Servico obter_ou_criar_atendimento_para_mensagem com numeracao sequencial e lock anti-race
- [ ] **T-A8** -- Parametro janela_continuacao_atendimento_horas na tabela de parametros (REQ-014.2C)

## Validacao funcional

- Simulador: telefone novo -> Atendimento #1; mesmo telefone -> reutiliza
- Alterar janela_continuacao_atendimento_horas via endpoint -> efeito imediato sem reiniciar

## Roteiros de teste

> REQ-016 ainda nao possui roteiro RT-* dedicado. Validar manualmente pelos criterios acima apos implementacao.
> Acompanhar: artefatos/qa/roteiros_teste/indice_cobertura_reqs.md

## Branch sugerida

feature/criacao-automatica-atendimento
"@
  },

  # ---- REQ-001 ----
  @{
    title = "[REQ-001] F01 -- Captura e confirmacao de CNPJ com politica de tentativas"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,REQ-001,REQ-004"
    body = @"
## Descricao

Completar o fluxo de identificacao via CNPJ: ecoar os dados retornados pela Receita para confirmacao do cliente, aplicar politica de 3 tentativas com distincao de falha do cliente vs. falha de infraestrutura, e escalar automaticamente ao esgotar as tentativas.

## Criterio de aceite

CNPJ valido -> bot exibe razao social e pergunta confirmacao. 3 CNPJs invalidos consecutivos -> escalonamento para humano. Timeout da API nao consome tentativa do cliente.

## Subtarefas

- [ ] **T-01** -- Eco e confirmacao dos dados retornados pela Receita (template CONFIRMA_DADOS_EMPRESA, estado aguardando_confirmacao_empresa)
- [ ] **T-02** -- Politica de 3 tentativas + escalonamento via REQ-004.9 ao esgotar
- [ ] **T-03** -- Retry com backoff exponencial na chamada a API da Receita (3 tentativas: 1s/2s/4s), com fallback para API alternativa
- [ ] **T-04** -- Tipagem de erros: tipo cliente|infra para garantir que falha de infra nao consome tentativa do cliente

## Validacao funcional

- CNPJ valido -> tela de confirmacao; cliente confirma -> avanca para qualificacao
- Simular timeout (mock) -> contador de tentativas do cliente permanece em 0
- 3 CNPJs invalidos -> status aguardando_humano no painel

## Roteiros de teste

- **RT-001** -- Jornada: Novo cliente envia CNPJ e faz pergunta tecnica
  - Passo 2: Enviar CNPJ da empresa (valida REQ-001.1, REQ-001.2, REQ-001.3)
  - Passo 3: Verificar vinculo da empresa com a negociacao (valida REQ-001.5)
  - Passo 8: Enviar o mesmo CNPJ por um segundo contato -- reuso sem nova consulta (valida REQ-001.7)
- Arquivo: artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md

## Branch sugerida

feature/REQ-001-captura-cnpj-completo
"@
  },

  @{
    title = "[REQ-001] F02 -- Auditoria e metricas da consulta CNPJ"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-001,REQ-005"
    body = @"
## Descricao

Registrar evento de auditoria para cada tentativa de CNPJ e instrumentar metricas de latencia e disponibilidade da consulta a Receita Federal.

## Criterio de aceite

Detalhe da conversa no painel exibe timeline de tentativas de CNPJ com resultado. Aba de metricas mostra contadores agregados das ultimas 24h/7d/30d.

## Subtarefas

- [ ] **T-05** -- Instrumentacao de NFRs: log de latencia, endpoint /api/metrics/req001, alertas quando p95 > 3s ou taxa de erro > 1%
- [ ] **T-06** -- Evento tentativa_cnpj em EventoAuditoria com CNPJ, resultado, motivo, numero da tentativa e timestamp

## Validacao funcional

- Aba Metricas REQ-001 exibe contadores reais
- Timeline da conversa mostra cada tentativa de CNPJ com resultado

## Roteiros de teste

- **RT-001** -- Jornada: Novo cliente envia CNPJ e faz pergunta tecnica
  - Passo 2: apos execucao, verificar se evento de auditoria foi gerado no historico
  - Passo 7: Verificar historico completo da conversa (valida REQ-005.2, REQ-005.5)
- Arquivo: artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md

## Branch sugerida

feature/REQ-001-auditoria-metricas
"@
  },

  # ---- REQ-002 ----
  @{
    title = "[REQ-002] F01 -- Classificador com categorias e fallback para RAG"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002,REQ-003"
    body = @"
## Descricao

Adicionar o campo categoria (1-4) ao classificador, consumir limiares de REQ-014 em vez de valores fixos, e implementar fallback condicional para Q&A/RAG quando a confianca for baixa, alem de tratamento de mensagens compostas.

## Criterio de aceite

Painel exibe categoria e nivel de confianca no detalhe da mensagem. Mensagem com confianca baixa consulta a base RAG antes de devolver fallback generico. Mensagem composta registra ambas as intencoes corretamente.

## Subtarefas

- [ ] **T-01** -- Adicionar categoria (1-4) e justificativa_curta ao ResultadoClassificacao; adaptar _decidir_resposta para rotear por categoria; consumir limiares de REQ-014
- [ ] **T-02** -- Fallback condicional ao REQ-003 quando confianca_nivel = baixa + tratamento de mensagem composta com pergunta embutida

## Validacao funcional

- "Quais produtos a Inforrel vende?" com classificador hesitante -> resposta da base RAG (nao fallback generico)
- "5, mas voces tem modelo com biometria facial?" -> registra quantidade=5 E responde sobre facial

## Roteiros de teste

- **RT-001** -- Jornada: Novo cliente envia CNPJ e faz pergunta tecnica
  - Passo 1: Enviar saudacao (valida REQ-002.1 -- classificacao de saudacao)
  - Passo 6: Enviar pergunta tecnica sobre produto (valida REQ-003.2 -- fallback RAG)
- Arquivo: artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md

## Branch sugerida

feature/classificador-categorias-fallback
"@
  },

  @{
    title = "[REQ-002] F02 -- Identificacao PF/PJ e roteamento antes da qualificacao"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002"
    body = @"
## Descricao

Permitir que o cliente faca perguntas sobre produto/empresa antes de fornecer documento fiscal (criando contato anonimo), inferir automaticamente se e PF ou PJ, e rotear para o fluxo correto de captura de documento.

## Criterio de aceite

Telefone novo pergunta sobre produto sem fornecer CNPJ/CPF -> painel mostra contato anonimo + resposta da base. Quando fornece CNPJ posteriormente -> contato e promovido com historico preservado.

## Subtarefas

- [ ] **T-03** -- Roteamento pre-identificacao: criar contato anonimo quando categoria 3 com confianca alta e sem documento fiscal
- [ ] **T-04** -- Inferencia PF/PJ a partir da mensagem inicial; pergunta dirigida quando ambiguo; troca de tipo no meio da conversa

## Validacao funcional

- "Quais relogios de ponto voces vendem?" de numero novo -> contato anonimo no painel + resposta
- Em mensagem seguinte, fornece CNPJ -> contato promovido, conversa anterior preservada
- "Quero orcamento para minha casa" -> pergunta PF ou PJ

## Roteiros de teste

- **RT-001** -- Jornada: Novo cliente envia CNPJ e faz pergunta tecnica
  - Passo 4: Enviar quantidade e tipo de produto (valida REQ-002.2 -- extracao de entidades)
  - Passo 5: Verificar campos pendentes (valida REQ-002.3 -- visibilidade do estado)
- Arquivo: artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md

## Branch sugerida

feature/identificacao-pf-pj-roteamento
"@
  },

  # ---- REQ-013 ----
  @{
    title = "[REQ-013] F01 -- Curadoria e workflow de aprovacao"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-013,REQ-012,REQ-005"
    body = @"
## Descricao

Completar o ciclo de curadoria de pares Q&A: criacao a partir de reports de problema, alerta de duplicatas antes de salvar e historico completo de revisoes com notificacao de rascunhos pendentes.

## Criterio de aceite

Report de categoria resposta_inadequada exibe botao "Criar par Q&A" com campos pre-preenchidos. Tentativa de criar par com pergunta similar exibe modal de alerta. Editar um par gera entrada na timeline de revisoes.

## Subtarefas

- [ ] **T-01** -- Botao "Criar par Q&A" no detalhe de report (categorias resposta_inadequada e template) com pre-preenchimento
- [ ] **T-04** -- Deteccao de duplicatas na criacao: busca de similaridade (score >= 0.85) antes de salvar, com modal de confirmacao
- [ ] **T-07** -- Tabela revisoes_par_qa com historico de edicoes + notificacao in-app de rascunhos pendentes ha mais de 7 dias

## Validacao funcional

- Abrir report resposta_inadequada -> botao visivel; clicar -> modal pre-preenchido
- Criar par com pergunta similar -> modal de alerta com candidatos
- Editar pergunta -> timeline mostra snapshot antes + ator + timestamp

## Roteiros de teste

- **RT-002** -- Jornada: Aprovacao de mensagem pendente e par Q&A
  - Cobre ciclo completo de criacao, aprovacao e curadoria de pares Q&A
- **RT-004** -- Jornada: Gestao de reports no painel
  - Passo 3: Criar par Q&A a partir de report (valida REQ-013.7 -- criacao a partir de report)
- Arquivos: artefatos/qa/roteiros_teste/RT-002-jornada-aprovacao-qa.md
          artefatos/qa/roteiros_teste/RT-004-jornada-reports-painel.md

## Branch sugerida

feature/REQ-013-curadoria-workflow-aprovacao
"@
  },

  @{
    title = "[REQ-013] F02 -- Busca, auditoria e estatisticas da base Q&A"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-013,REQ-005"
    body = @"
## Descricao

Adicionar filtro por contexto na busca, registrar o caminho de cada resposta (Q&A curada vs. RAG vs. LLM) em ProcessamentoMensagem e exibir estatisticas de uso no cabecalho da tela de gestao.

## Criterio de aceite

Detalhe de mensagem no painel exibe qual caminho de resposta foi usado e o ID do par Q&A quando aplicavel. Cabecalho da tela Q&A exibe 4 cards de contadores.

## Subtarefas

- [ ] **T-02** -- Parametro contexto opcional no endpoint de busca Q&A com index parcial no Postgres
- [ ] **T-03** -- Campos caminho_resposta, par_qa_id e qa_score em ProcessamentoMensagem + migration Alembic
- [ ] **T-05** -- Endpoint GET /api/pares-qa/estatisticas + 4 cards de contadores no cabecalho de QABasePage

## Validacao funcional

- Detalhe da mensagem mostra: qa_curada | ID: 42 | score: 0.91
- Aprovar/desativar par -> contadores atualizam imediatamente

## Roteiros de teste

- **RT-002** -- Jornada: Aprovacao de mensagem pendente e par Q&A
  - Apos aprovar um par, verificar no detalhe da proxima mensagem respondida via Q&A se caminho_resposta = qa_curada
- **RT-001** -- Passo 6: enviar pergunta tecnica e inspecionar modal de raciocinio (valida REQ-005.6)
- Arquivos: artefatos/qa/roteiros_teste/RT-002-jornada-aprovacao-qa.md
          artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md

## Branch sugerida

feature/REQ-013-busca-auditoria-estatisticas
"@
  },

  # ---- REQ-015 ----
  @{
    title = "[REQ-015] F01 -- Captura e confirmacao de CPF com politica de tentativas"
    milestone = "Sprint 03"
    labels = "tipo:feature,prio:alta,area:backend,REQ-015,REQ-004"
    body = @"
## Descricao

Completar o fluxo de identificacao via CPF para clientes PF: eco e confirmacao, politica de 3 tentativas e tratamento de cliente que recusa fornecer o CPF.

## Criterio de aceite

CPF valido -> confirmacao exibida. 3 CPFs invalidos consecutivos -> escalonamento. Cliente recusa CPF -> campos de nome/endereco ainda sao coletados antes de escalar.

## Subtarefas

- [ ] **T-01** -- Eco e confirmacao do CPF capturado (analogo ao REQ-001 T-01)
- [ ] **T-02** -- Politica de 3 tentativas + escalonamento para CPF invalido
- [ ] **T-03** -- Tratamento de PF que recusa fornecer CPF: prosseguir com campos independentes e escalar antes de finalizar orcamento

## Validacao funcional

- CPF valido -> confirmacao; 3 CPFs invalidos -> escalonamento
- Cliente recusa CPF -> campos de nome/endereco ainda sao coletados antes de escalar

## Roteiros de teste

> REQ-015 ainda nao possui roteiro RT-* dedicado.
> Apos implementacao, criar RT-009 cobrindo: captura CPF, confirmacao, politica de tentativas e recusa.
> Acompanhar: artefatos/qa/roteiros_teste/indice_cobertura_reqs.md

## Branch sugerida

feature/REQ-015-captura-cpf-completo
"@
  }
)

# ---------------------------------------------------------------------------
# Issues — Sprint 04
# ---------------------------------------------------------------------------
$issuesSprint04 = @(

  # ---- REQ-016 ----
  @{
    title = "[REQ-016] F03 -- Ciclo de vida do atendimento: janela de continuacao, encerramento e reabertura"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:alta,area:backend,REQ-016"
    body = @"
## Descricao

Implementar o ciclo de vida completo do atendimento: deteccao automatica de continuacao por janela de tempo, encerramento explicito com pergunta de fechamento e reabertura de atendimentos encerrados.

## Criterio de aceite

Um atendimento encerrado pode ser reaberto quando o cliente retorna dentro da janela configurada. Fora da janela, um novo atendimento e criado automaticamente.

## Subtarefas

- [ ] **T-A5** -- Janela de continuacao: verificar ultima_mensagem_at vs. janela_continuacao_atendimento_horas ao receber nova mensagem de contato com atendimento encerrado
- [ ] **T-A6** -- Encerramento explicito: pergunta de fechamento ao operador + motivo de encerramento
- [ ] **T-A7** -- Reabertura de atendimento encerrado dentro da janela + atualizacao de ultima_mensagem_at

## Validacao funcional

- Atendimento encerrado ha 2h + janela de 24h + nova mensagem -> reabre o mesmo atendimento
- Atendimento encerrado ha 48h + janela de 24h + nova mensagem -> cria novo atendimento

## Roteiros de teste

> REQ-016 ainda nao possui roteiro RT-* dedicado. Validar manualmente pelos criterios acima.
> Acompanhar: artefatos/qa/roteiros_teste/indice_cobertura_reqs.md

## Branch sugerida

feature/ciclo-vida-atendimento
"@
  },

  @{
    title = "[REQ-016] F04 -- Painel e auditoria de atendimentos"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-016,REQ-005"
    body = @"
## Descricao

Exibir o atendimento com identificacao "Atendimento #N" no painel, expor acoes de encerrar/reabrir e registrar eventos de auditoria do ciclo de vida.

## Criterio de aceite

Painel exibe "Atendimento #N" no cabecalho da conversa. Operador pode encerrar ou reabrir via botao. Cada transicao gera evento de auditoria visivel na timeline.

## Subtarefas

- [ ] **T-A9** -- Painel: exibicao "Atendimento #N" + botoes encerrar/reabrir na tela da conversa
- [ ] **T-A10** -- Eventos de auditoria de atendimento em REQ-005.4 (ativo->encerrado, encerrado->ativo)
- [ ] **T-A12** -- Cenarios de teste manual no QA Runner para o ciclo de vida de atendimento

## Validacao funcional

- Encerrar atendimento via painel -> evento de auditoria aparece na timeline
- QA Runner carrega os cenarios de T-A12 e todos passam

## Roteiros de teste

- **RT-003** -- Jornada: Takeover humano suspende agente
  - Cobre acoes do operador no painel e registro de eventos de auditoria (valida REQ-005, REQ-010)
- Arquivo: artefatos/qa/roteiros_teste/RT-003-jornada-takeover-humano.md
> Apos T-A12 implementado, os cenarios criados serao adicionados a um RT-* dedicado ao REQ-016.

## Branch sugerida

feature/painel-auditoria-atendimentos
"@
  },

  # ---- REQ-002 ----
  @{
    title = "[REQ-002] F03 -- Qualificacao adaptativa completa do atendimento"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-002"
    body = @"
## Descricao

Implementar o motor de qualificacao completo: catalogo de campos por tipo de cliente, perguntas dinamicas baseadas no estado atual, captura de tipo/modelo/dados adicionais/endereco, validacoes, eco consolidado e tratamento de ambiguidade com retry e RAG durante a qualificacao.

## Criterio de aceite

Mensagem rica inicial preenche multiplos campos de uma vez. Painel mostra lista de campos com status. Ao final, sumarizacao completa e apresentada antes de encaminhar para orcamento.

## Subtarefas

- [ ] **T-05** -- Catalogo canonico de campos por tipo de cliente (PF/PJ) + servico proxima_pergunta(atendimento) + integracao no processador
- [ ] **T-06** -- Captura adaptativa: tipo de produto (T-06.1), modelo (T-06.2), dados adicionais (T-06.3), endereco (T-06.4)
- [ ] **T-07** -- Validacoes de respostas capturadas: CPF, e-mail, telefone, modelo, endereco, quantidade
- [ ] **T-08** -- Eco consolidado de dados extraidos (REQ-002.16) + sumarizacao final da qualificacao (REQ-002.5)
- [ ] **T-09** -- Tratamento de ambiguidade: contador de tentativas por campo, reformulacao dirigida, escalonamento apos esgotar, retomada do RAG sem consumir tentativa

## Validacao funcional

- Painel mostra status de cada campo (capturado / pendente / nao-aplicavel)
- Resposta invalida (CPF errado) -> mensagem de esclarecimento; 3 falhas -> escalonamento

## Roteiros de teste

- **RT-001** -- Jornada: Novo cliente envia CNPJ e faz pergunta tecnica
  - Passo 4: Enviar quantidade e tipo de produto (valida REQ-002.2 -- extracao)
  - Passo 5: Verificar campos pendentes na negociacao (valida REQ-002.3)
- **RT-003** -- Jornada: Takeover humano suspende agente
  - Cobre escalonamento apos esgotamento de tentativas (valida REQ-004)
- Arquivos: artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md
          artefatos/qa/roteiros_teste/RT-003-jornada-takeover-humano.md

## Branch sugerida

feature/qualificacao-adaptativa-completa
"@
  },

  @{
    title = "[REQ-002] F04 -- Abandono de conversa, reengajamento e integracao WhatsApp"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:baixa,area:backend,area:infra,area:integracao,REQ-002,REQ-008"
    body = @"
## Descricao

Detectar abandono por inatividade, enviar mensagem de reengajamento e, apos maturidade do painel, validar todos os comportamentos do REQ-002 no canal real do WhatsApp.

## Criterio de aceite

Inatividade de 24h -> mensagem de reengajamento enviada. Apos 72h sem resposta -> atendimento finalizado com motivo abandono.

## Subtarefas

- [ ] **T-10** -- Job/scheduler de deteccao de inatividade 24h, mensagem unica de reengajamento, finalizacao apos 72h e retomada de contexto em nova conversa
- [ ] **T-11** -- Integracao Twilio/Meta Cloud API + validacao de comportamentos REQ-002 no canal real + ajustes de UX WhatsApp (limites de caracteres, listas, midia)

## Validacao funcional

- Simular inatividade de 24h (botao dev ou ajuste de timestamp) -> mensagem de reengajamento
- Canal WhatsApp real: enviar 4 mensagens-tipo e conferir roteamento por categoria

## Roteiros de teste

- **RT-001** -- Jornada: Novo cliente envia CNPJ e faz pergunta tecnica
  - Passo 9: Confirmar que agente nao enviou mensagens reais ao WhatsApp (valida REQ-008.5 -- gap conhecido)
- Arquivo: artefatos/qa/roteiros_teste/RT-001-jornada-novo-cliente.md
> T-11 (integracao WhatsApp real) requer roteiro dedicado a ser criado apos maturidade do painel.

## Dependencias

T-11 so vai para In Progress quando F01, F02 e F03 estiverem Done.

## Branch sugerida

feature/abandono-reengajamento-whatsapp
"@
  },

  # ---- REQ-013 ----
  @{
    title = "[REQ-013] F03 -- Configuracao persistente e ingestao em lote"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-013,REQ-014"
    body = @"
## Descricao

Persistir as configuracoes de runtime do RAG (QA_ENABLED, QA_SCORE_MINIMO) entre reinicializacoes e permitir ingestao em lote de pares Q&A a partir de CSV/Markdown.

## Criterio de aceite

Alterar QA_SCORE_MINIMO via painel, reiniciar servidor -> valor persiste. Upload de CSV com 20 perguntas -> tela de revisao em massa com checkboxes; aprovar selecionados -> embeddings gerados.

## Subtarefas

- [ ] **T-06** -- Tabela configuracoes_runtime + persistencia no banco + historico de alteracoes; PATCH /api/config/rag persiste; boot carrega antes de aceitar requisicoes
- [ ] **T-08** -- Script scripts/ingerir_pares_qa.py (markdown/CSV/JSON) + endpoint admin POST /api/pares-qa/ingestao + tela de revisao em massa com selecao multipla

## Validacao funcional

- Mudar QA_SCORE_MINIMO, reiniciar servidor -> valor persiste
- Subir CSV de 20 perguntas -> tabela de revisao com checkboxes; aprovar 5 -> embedding gerado

## Roteiros de teste

- **RT-005** -- Jornada: Configuracao RAG em runtime
  - Passo 6: Verificar persistencia da configuracao apos reinicio do backend (valida REQ-014 -- gap persistencia)
- Arquivo: artefatos/qa/roteiros_teste/RT-005-jornada-configuracao-rag.md

## Branch sugerida

feature/REQ-013-config-persistente-ingestao-lote
"@
  },

  # ---- REQ-015 ----
  @{
    title = "[REQ-015] F02 -- Consulta de debitos e tratamento de restricao"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-015,REQ-004,REQ-010"
    body = @"
## Descricao

Integrar provedor de consulta de debitos, tratar restricao financeira sem negar automaticamente (LGPD art. 20) e sinalizar visualmente no painel sem expor o CPF completo.

## Criterio de aceite

CPF com restricao -> painel exibe badge de alerta + escalonamento para humano. CPF nao aparece em texto pleno em nenhuma tela.

## Subtarefas

- [ ] **T-04** -- Decisao e integracao do provedor de consulta de debitos (Serasa/SPC/Boa Vista/Quod)
- [ ] **T-05** -- Tratamento de restricao financeira: registrar, sinalizar no painel e escalar (nao negar automaticamente)
- [ ] **T-08** -- Sinalizacao visual de restricao no painel sem expor CPF completo

## Validacao funcional

- CPF com restricao -> painel exibe badge de alerta + escalonamento; CPF nao aparece em texto pleno

## Roteiros de teste

> REQ-015 ainda nao possui roteiro RT-* dedicado.
> Apos implementacao de F01, criar RT-009 cobrindo tambem consulta de debitos e sinalizacao de restricao.
> Acompanhar: artefatos/qa/roteiros_teste/indice_cobertura_reqs.md

## Branch sugerida

feature/REQ-015-consulta-debitos-restricao
"@
  },

  @{
    title = "[REQ-015] F03 -- LGPD, auditoria e reuso de CPF"
    milestone = "Sprint 04"
    labels = "tipo:feature,prio:alta,area:backend,REQ-015,REQ-005"
    body = @"
## Descricao

Garantir conformidade com a LGPD para o CPF: mascaramento em logs e telas, evento de auditoria por consulta de debitos e reuso de CPF ja validado em conversas futuras do mesmo telefone.

## Criterio de aceite

CPF nao aparece em texto pleno em nenhum log ou tela do painel. Cliente que ja validou CPF em conversa anterior nao precisa fornecer novamente.

## Subtarefas

- [ ] **T-06** -- Mascaramento de CPF em logs, modal de raciocinio e auditoria (LGPD art. 20)
- [ ] **T-07** -- Evento de auditoria por consulta de debitos com CPF mascarado
- [ ] **T-09** -- Reuso de CPF ja validado em conversas futuras do mesmo telefone

## Validacao funcional

- CPF nao aparece em texto pleno em nenhum log ou tela do painel
- Cliente que ja validou CPF em conversa anterior nao precisa fornecer novamente

## Roteiros de teste

> REQ-015 ainda nao possui roteiro RT-* dedicado.
> RT-009 (a criar) devera incluir: verificacao de mascaramento em logs, auditoria de consulta e reuso de CPF.
> Acompanhar: artefatos/qa/roteiros_teste/indice_cobertura_reqs.md

## Branch sugerida

feature/REQ-015-lgpd-auditoria-reuso-cpf
"@
  }
)

# ---------------------------------------------------------------------------
# Criar issues Sprint 03
# ---------------------------------------------------------------------------
foreach ($i in $issuesSprint03) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray
    continue
  }
  Write-Host "  Criando: $($i.title)" -ForegroundColor White
  New-Issue -Title $i.title -Body $i.body -Labels $i.labels -Milestone $i.milestone
}

# ---------------------------------------------------------------------------
# Criar issues Sprint 04
# ---------------------------------------------------------------------------
Write-Host "`n== Criando issues Sprint 04 ==" -ForegroundColor Green
foreach ($i in $issuesSprint04) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray
    continue
  }
  Write-Host "  Criando: $($i.title)" -ForegroundColor White
  New-Issue -Title $i.title -Body $i.body -Labels $i.labels -Milestone $i.milestone
}

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
Write-Host "`n== Concluido ==" -ForegroundColor Green
Write-Host "  16 issues reorganizadas criadas (ou puladas se ja existiam)." -ForegroundColor White
Write-Host "  Proximos passos manuais:" -ForegroundColor White
Write-Host "    1. Adicionar issues ao Project v2 'Assistente de Vendas - Board' (bulk add)" -ForegroundColor White
Write-Host "    2. Definir Sprint, Prioridade e Estimativa nos campos customizados" -ForegroundColor White
