<#
.SYNOPSIS
  Cria as 6 issues restantes do backlog REQ-016 (Renomeacao Negociacao->Atendimento)
  para Sprint 04. Complementa scripts\criar_issues_req016_sprint03.ps1.

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/backlog_req016_atendimentos.md (v0.2)

  Tarefas cobertas neste script (Sprint 04):
    T-A5   Janela de continuacao + pergunta de continuacao
    T-A6   Encerramento explicito + pergunta de fechamento
    T-A7   Reabertura de atendimento encerrado
    T-A9   Painel: exibicao "Atendimento #N" + acoes encerrar/reabrir
    T-A10  Eventos de auditoria de atendimento em REQ-005.4
    T-A12  Cenarios de teste manual no QA Runner

  Tarefas T-A1, T-A1b, T-A2, T-A3, T-A4, T-A8, T-A11 ja estao em scripts\criar_issues_req016_sprint03.ps1.

.PARAMETER DryRun
  Imprime os comandos sem chama-los.

.PARAMETER MilestoneTitle
  Nome do milestone para vincular (default: "Sprint 04"). Cria se nao existir.
#>

[CmdletBinding()]
param(
  [switch]$DryRun,
  [string]$MilestoneTitle = "Sprint 04"
)

$ErrorActionPreference = "Stop"

function Invoke-Gh {
  param([string[]]$Arguments)
  $cmd = "gh " + ($Arguments -join " ")
  if ($DryRun) { Write-Host "[DRY] $cmd" -ForegroundColor Yellow; return }
  Write-Host "> $cmd" -ForegroundColor Cyan
  & gh @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Falhou: $cmd (exit $LASTEXITCODE)" }
}

Write-Host "== Pre-flight ==" -ForegroundColor Green
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& gh --version *>$null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh CLI nao instalado." }
& gh auth status *>$null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh nao autenticado." }
$ErrorActionPreference = $prevEAP

Write-Host "`n== Labels ==" -ForegroundColor Green
$extraLabels = @(
  @{ name = "REQ-016"; color = "ededed"; desc = "Identificacao e numeracao de atendimentos" },
  @{ name = "REQ-005"; color = "ededed"; desc = "Registro de interacoes / auditoria" },
  @{ name = "REQ-010"; color = "ededed"; desc = "Painel administrativo" }
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

Write-Host "`n== Milestone $MilestoneTitle ==" -ForegroundColor Green
$milestonesJson = gh api '/repos/{owner}/{repo}/milestones?state=open' 2>$null
$msExists = $null
if ($milestonesJson) {
  $msMatch = ($milestonesJson | ConvertFrom-Json) | Where-Object { $_.title -eq $MilestoneTitle } | Select-Object -First 1
  if ($msMatch) { $msExists = $msMatch.number }
}
if (-not $msExists) {
  Write-Host "  Milestone '$MilestoneTitle' nao existe. Criando..." -ForegroundColor Yellow
  Invoke-Gh @("api", "/repos/{owner}/{repo}/milestones", "-f", "title=$MilestoneTitle", "-f", "state=open", "-f", "description=Sprint 04 -- complemento REQ-016 + outros")
}

Write-Host "`n== Idempotencia ==" -ForegroundColor Green
$existingIssuesJson = gh issue list --state all --limit 300 --json title 2>$null
$existingIssueTitles = @()
if ($existingIssuesJson) {
  $existingIssueTitles = ($existingIssuesJson | ConvertFrom-Json) | ForEach-Object { $_.title }
}

Write-Host "`n== Criando issues REQ-016 Sprint 04 ==" -ForegroundColor Green

$issues = @(
  @{
    title = "[REQ-016] T-A5 -- Janela de continuacao + pergunta de continuacao"
    body = @(
      "## Subitens REQ", "", "- REQ-016.7 -- Janela de continuacao baseada em ultima_mensagem_at", "- REQ-016.9 -- Pergunta de continuacao quando cliente reabre conversa dentro da janela", "- REQ-016.18 -- Parametro janela_continuacao_atendimento_horas", ""
      "## Contexto", "", "Hoje toda nova mensagem do mesmo telefone cai no mesmo Negociacao. Precisamos decidir se continua o atendimento aberto ou abre um novo, baseado na janela de inatividade.", ""
      "## Escopo", "", "- Calcular delta entre agora e ultima_mensagem_at do atendimento ativo.", "- Se delta <= janela -> continua o mesmo atendimento.", "- Se delta > janela e atendimento ainda ativo -> perguntar 'Quer continuar o atendimento anterior ou iniciar um novo?'.", "- Se atendimento ja encerrado -> abre novo automaticamente.", ""
      "## Validacao no painel", "", "- Botao dev 'envelhecer atendimento' para simular passagem do tempo.", "- Mensagem apos janela -> pergunta de continuacao.", ""
      "## Dependencias", "", "T-A1, T-A2, T-A3 (ultima_mensagem_at), T-A4, T-A7 (reabertura), T-A8 (parametro).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-016-janela-continuacao", "commit:  feat(REQ-016/T-A5): janela de continuacao e pergunta de continuacao", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-016"
  },
  @{
    title = "[REQ-016] T-A6 -- Encerramento explicito + pergunta de fechamento"
    body = @(
      "## Subitens REQ", "", "- REQ-016.4 -- Ciclo de vida ativo / encerrado", "- REQ-016.10 -- Pergunta de fechamento ao detectar conclusao", ""
      "## Contexto", "", "Hoje atendimento fica aberto indefinidamente. Precisa de mecanismo de encerramento explicito por sinais conversacionais (orcamento aceito/recusado, cliente finalizando) e por acao manual no painel.", ""
      "## Escopo", "", "- Detectar intencoes terminais (ACEITAR_ORCAMENTO, RECUSAR_ORCAMENTO, AGRADECER_FIM, DESISTIR).", "- Pergunta de fechamento: 'Posso considerar este atendimento finalizado?'.", "- Em 'Sim' -> status encerrado, motivo_encerramento preenchido.", "- Endpoint POST /api/atendimentos/{id}/encerrar.", ""
      "## Validacao no painel", "", "- Conversa com 'Aceito o orcamento' -> pergunta de fechamento + status encerrado.", "- Botao manual 'Encerrar' no painel funciona.", ""
      "## Dependencias", "", "T-A1, T-A2, T-A4.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-016-encerramento-atendimento", "commit:  feat(REQ-016/T-A6): encerramento explicito de atendimento com pergunta de fechamento", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-016"
  },
  @{
    title = "[REQ-016] T-A7 -- Reabertura de atendimento encerrado"
    body = @(
      "## Subitens REQ", "", "- REQ-016.8 -- Reabertura de atendimento", ""
      "## Contexto", "", "Cliente pode voltar a mensagear apos encerramento. Precisamos decidir entre reabrir o anterior ou criar novo.", ""
      "## Escopo", "", "- Se atendimento mais recente esta encerrado ha menos de N dias (parametrizavel) -> oferecer reabrir.", "- Se ha mais tempo -> abrir novo atendimento referenciando o anterior.", "- Botao 'Reabrir' no painel.", ""
      "## Validacao no painel", "", "- Atendimento encerrado ha 1 dia + nova mensagem -> oferece reabertura.", "- Atendimento encerrado ha 30 dias -> abre novo.", ""
      "## Dependencias", "", "T-A1, T-A2, T-A6.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-016-reabertura-atendimento", "commit:  feat(REQ-016/T-A7): reabertura de atendimento encerrado recente", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-016"
  },
  @{
    title = "[REQ-016] T-A9 -- Painel: exibicao 'Atendimento #N' + acoes encerrar/reabrir"
    body = @(
      "## Subitens REQ", "", "- REQ-016.14 -- Identificacao por numero do atendimento", "- REQ-016.15 -- Listagem por atendimento", "- REQ-016.8 -- Acao manual de reabertura", "- REQ-010 v1.3", ""
      "## Contexto", "", "Painel precisa exibir 'Atendimento #N' no lugar do antigo 'Negociacao #N', listar atendimentos por contato e expor acoes Encerrar / Reabrir.", ""
      "## Escopo", "", "- Header da conversa: 'Atendimento #42 -- Ativo' (badge colorido).", "- Listagem de atendimentos por contato com filtro por status.", "- Botoes Encerrar (se ativo) e Reabrir (se encerrado recente).", "- Confirmation modal antes de executar acao.", ""
      "## Validacao no painel", "", "- Header e listagem refletem novo vocabulario.", "- Acoes funcionam end-to-end.", ""
      "## Dependencias", "", "T-A2, T-A6, T-A7, T-A11 (rename UI).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-016-painel-atendimento", "commit:  feat(REQ-016/T-A9): painel exibe atendimento #N com acoes encerrar/reabrir", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:frontend,REQ-016,REQ-010"
  },
  @{
    title = "[REQ-016] T-A10 -- Eventos de auditoria de atendimento em REQ-005.4"
    body = @(
      "## Subitens REQ", "", "- REQ-005.4 v1.10 -- Eventos de auditoria", "- REQ-016.4/.6/.8/.9/.10 (transicoes de estado)", ""
      "## Contexto", "", "Cada transicao no ciclo de vida do atendimento (criado, continuado, encerrado, reaberto) deve gerar evento de auditoria.", ""
      "## Escopo", "", "- Tipos de evento: atendimento_criado, atendimento_continuado, atendimento_encerrado, atendimento_reaberto.", "- Cada evento registra ator (sistema|operador), motivo, timestamp, atendimento_id.", "- Hook em T-A4, T-A5, T-A6, T-A7.", "- Endpoint /api/atendimentos/{id}/eventos retorna timeline.", ""
      "## Validacao no painel", "", "- Tela de detalhe do atendimento mostra timeline de eventos.", ""
      "## Dependencias", "", "T-A4, T-A5, T-A6, T-A7.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-016-eventos-auditoria-atendimento", "commit:  feat(REQ-016/T-A10): registra eventos de auditoria nas transicoes do atendimento", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-016,REQ-005"
  },
  @{
    title = "[REQ-016] T-A12 -- Cenarios de teste manual no QA Runner para novo ciclo de vida"
    body = @(
      "## Subitens REQ", "", "- Transversal -- valida T-A4 a T-A7 e T-A9", ""
      "## Contexto", "", "QA Runner precisa de cenarios cobrindo: criacao automatica, continuacao dentro da janela, pergunta apos janela, encerramento, reabertura recente, abertura nova apos encerramento antigo.", ""
      "## Escopo", "", "- Cenario CTF-016-01 a CTF-016-06 cobrindo cada transicao do ciclo.", "- Documentar resultados esperados (status, motivo, eventos de auditoria).", "- Adicionar ao QA Runner existente.", ""
      "## Validacao no painel", "", "- QA Runner executa os 6 cenarios e todos passam.", ""
      "## Dependencias", "", "T-A4 a T-A7 + T-A9 + T-A10.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-016-cenarios-qa-runner", "commit:  test(REQ-016/T-A12): adiciona cenarios CTF-016 para ciclo de vida do atendimento", "``````"
    ) -join "`n"
    labels = "tipo:test,prio:media,area:qa,REQ-016"
  }
)

foreach ($i in $issues) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray; continue
  }
  Invoke-Gh @("issue", "create", "--title", $i.title, "--body", $i.body, "--label", $i.labels, "--milestone", $MilestoneTitle)
}

Write-Host "`n== Concluido ==" -ForegroundColor Green
