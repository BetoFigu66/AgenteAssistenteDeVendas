<#
.SYNOPSIS
  Bootstrap do GitHub Projects para o repositorio AgenteAssistenteDeVendas.
  Executa os itens 6.2 (labels, milestone) e 6.3 (issues dos bugs FAIL) da proposta
  `artefatos/gerente_de_projetos/proposta_github_projects.md`.

.DESCRIPTION
  Pre-requisitos:
    - gh CLI instalado (gh --version)
    - gh autenticado: gh auth login -h github.com
    - Repositorio com permissao Write para a conta autenticada

  Itens NAO cobertos por este script (fazer pela UI do GitHub):
    - Criar o Project v2 ("Assistente de Vendas - Board") e campos customizados
      (Status, Sprint, Prioridade, REQ, Tipo, Estimativa) - secao 3.5 da proposta.
    - Adicionar as issues criadas aqui ao Project (drag-and-drop ou bulk add).
    - Configurar protecao de branches (politica_branches.md secao 5).

.PARAMETER DryRun
  Se especificado, imprime os comandos que seriam executados sem chama-los.

.EXAMPLE
  .\scripts\bootstrap_github_projects.ps1 -DryRun
  .\scripts\bootstrap_github_projects.ps1
#>

[CmdletBinding()]
param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-Gh {
  param([string[]]$Arguments)
  $cmd = "gh " + ($Arguments -join " ")
  if ($DryRun) {
    Write-Host "[DRY] $cmd" -ForegroundColor Yellow
    return
  }
  Write-Host "> $cmd" -ForegroundColor Cyan
  & gh @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Falhou: $cmd (exit $LASTEXITCODE)"
  }
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
Write-Host "== Pre-flight ==" -ForegroundColor Green
$ghVersion = gh --version 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "gh CLI nao instalado. Veja https://cli.github.com/"
}
Write-Host $ghVersion[0]

$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host $authStatus -ForegroundColor Red
  throw "gh nao autenticado. Rode: gh auth login -h github.com"
}
Write-Host "Auth OK." -ForegroundColor Green

# ---------------------------------------------------------------------------
# 6.2.1 Labels
# ---------------------------------------------------------------------------
Write-Host "`n== 6.2.1 Labels ==" -ForegroundColor Green

$labels = @(
  # tipo
  @{ name = "tipo:bug";     color = "d73a4a"; desc = "Defeito / falha em teste" }
  @{ name = "tipo:feature"; color = "0e8a16"; desc = "Entrega de REQ ou funcionalidade" }
  @{ name = "tipo:task";    color = "1d76db"; desc = "Tarefa tecnica / refatoracao / config" }
  @{ name = "tipo:chore";   color = "c5def5"; desc = "Manutencao, documentacao, housekeeping" }
  @{ name = "tipo:spike";   color = "fbca04"; desc = "Investigacao com prazo curto" }

  # prioridade
  @{ name = "prio:critica"; color = "b60205"; desc = "Bloqueia uso ou viola seguranca" }
  @{ name = "prio:alta";    color = "d93f0b"; desc = "Impacta fluxo principal" }
  @{ name = "prio:media";   color = "fbca04"; desc = "Impacta fluxo secundario" }
  @{ name = "prio:baixa";   color = "0e8a16"; desc = "Melhoria ou impacto pequeno" }

  # area
  @{ name = "area:backend";   color = "5319e7"; desc = "Backend FastAPI / SQLAlchemy" }
  @{ name = "area:frontend";  color = "1d76db"; desc = "Frontend React / Vite" }
  @{ name = "area:infra";     color = "bfd4f2"; desc = "Docker, banco, deploy, CI" }
  @{ name = "area:integracao";color = "fef2c0"; desc = "Twilio, Receita Federal, OpenAI, etc." }
  @{ name = "area:qa";        color = "c5def5"; desc = "Testes manuais, runner, planos" }

  # qa
  @{ name = "qa:reproduzido";  color = "fbca04"; desc = "Bug confirmado em ambiente local" }
  @{ name = "qa:em-validacao"; color = "0e8a16"; desc = "Correcao implantada, aguarda reteste" }
  @{ name = "qa:aprovado";     color = "0e8a16"; desc = "Reteste aprovado pela QA" }

  # REQs ativos (Sprint 02/03)
  @{ name = "REQ-001"; color = "ededed"; desc = "Integracao Receita Federal" }
  @{ name = "REQ-002"; color = "ededed"; desc = "Fluxo conversacional guiado" }
  @{ name = "REQ-003"; color = "ededed"; desc = "Base de respostas automaticas (Q&A / RAG)" }
  @{ name = "REQ-005"; color = "ededed"; desc = "Registro de interacoes e historico" }
  @{ name = "REQ-006"; color = "ededed"; desc = "Rastreamento de orcamentos e conversao" }
  @{ name = "REQ-010"; color = "ededed"; desc = "Painel administrativo" }
  @{ name = "REQ-012"; color = "ededed"; desc = "Relatorios" }
  @{ name = "REQ-013"; color = "ededed"; desc = "Base de conhecimento (RAG)" }
  @{ name = "REQ-014"; color = "ededed"; desc = "Configuracao runtime camadas conhecimento" }
)

$existingLabelsJson = gh label list --limit 200 --json name 2>$null
$existingLabelNames = @()
if ($existingLabelsJson) {
  $existingLabelNames = ($existingLabelsJson | ConvertFrom-Json) | ForEach-Object { $_.name }
}

foreach ($l in $labels) {
  if ($existingLabelNames -contains $l.name) {
    Write-Host "  label '$($l.name)' ja existe - pulando" -ForegroundColor DarkGray
    continue
  }
  Invoke-Gh @("label", "create", $l.name, "--color", $l.color, "--description", $l.desc)
}

# ---------------------------------------------------------------------------
# 6.2.2 Milestone Sprint 03
# ---------------------------------------------------------------------------
Write-Host "`n== 6.2.2 Milestone Sprint 03 ==" -ForegroundColor Green

$msTitle = "Sprint 03"
$milestonesJson = gh api '/repos/{owner}/{repo}/milestones?state=open' 2>$null
$msExists = $null
if ($milestonesJson) {
  $msMatch = ($milestonesJson | ConvertFrom-Json) | Where-Object { $_.title -eq $msTitle } | Select-Object -First 1
  if ($msMatch) { $msExists = $msMatch.number }
}
if ($msExists) {
  Write-Host "  milestone '$msTitle' ja existe (#$msExists) - pulando" -ForegroundColor DarkGray
} else {
  Invoke-Gh @("api", "/repos/{owner}/{repo}/milestones", "-f", "title=$msTitle", "-f", "description=Primeiro sprint com GitHub Projects ativo. Cadencia G02 (14 dias). Datas a definir no planning.")
}

# ---------------------------------------------------------------------------
# 6.3 Carga inicial - issues dos bugs FAIL atuais
# ---------------------------------------------------------------------------
Write-Host "`n== 6.3 Carga inicial: issues dos bugs FAIL ==" -ForegroundColor Green
Write-Host "  (D1: Kika cria as issues na sessao de teste; este script eh apenas a carga inicial)" -ForegroundColor DarkGray

$repoNameWithOwner = (gh repo view --json nameWithOwner | ConvertFrom-Json).nameWithOwner
$repoUrlBase = "https://github.com/$repoNameWithOwner/blob/main/artefatos/qa/bugs"

$bugsDir = "artefatos/qa/bugs"
$bugFiles = Get-ChildItem -Path $bugsDir -Filter "CTF-*.md" | Sort-Object Name

if (-not $bugFiles) {
  Write-Host "  Nenhum arquivo CTF-*.md encontrado em $bugsDir" -ForegroundColor Yellow
}

$existingIssuesJson = gh issue list --state all --limit 200 --json title 2>$null
$existingIssueTitles = @()
if ($existingIssuesJson) {
  $existingIssueTitles = ($existingIssuesJson | ConvertFrom-Json) | ForEach-Object { $_.title }
}

foreach ($file in $bugFiles) {
  $content = Get-Content -Path $file.FullName -Encoding UTF8 -TotalCount 10
  if (-not $content) { continue }

  $h1 = $content | Where-Object { $_ -match '^#\s+' } | Select-Object -First 1
  if (-not $h1) {
    Write-Host "  AVISO: $($file.Name) sem H1 - pulando" -ForegroundColor Yellow
    continue
  }
  $issueTitle = $h1 -replace '^#\s+', ''

  $idFromFile = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)

  $cobreLine = $content | Where-Object { $_ -match '^\- \*\*Cobre:\*\*\s+(REQ-\d+' } | Select-Object -First 1
  $req = if ($cobreLine) {
    if ($cobreLine -match '(REQ-\d+)') { $Matches[1] } else { "REQ-???" }
  } else { "REQ-???" }

  $sevLine = $content | Where-Object { $_ -match '^\- \*\*Severidade:\*\*' } | Select-Object -First 1
  $prio = "media"
  if ($sevLine) {
    if ($sevLine -match 'Alta') { $prio = "alta" }
    elseif ($sevLine -match 'Critica') { $prio = "critica" }
    elseif ($sevLine -match 'Baixa') { $prio = "baixa" }
  }

  $area = if ($req -eq "REQ-010") { "frontend" } else { "backend" }

  if ($existingIssueTitles -contains $issueTitle) {
    Write-Host "  issue '$issueTitle' ja existe - pulando" -ForegroundColor DarkGray
    continue
  }

  $bodyLines = @(
    "## Identificacao",
    "",
    "- **Cenario de teste:** ``$idFromFile``",
    "- **REQ relacionado:** ``$req``",
    "- **Severidade:** $prio",
    "- **Evidencia:** [$idFromFile.md]($repoUrlBase/$idFromFile.md)",
    "",
    "## Origem",
    "",
    "Carga inicial do GitHub Projects (proposta secao 6.3). Issue gerada a partir de ``$($file.Name)``.",
    "",
    "## Branch sugerida",
    "",
    "``````",
    "branch:  bugfix/<descricao-curta>",
    "commit:  fix($idFromFile): <descricao>",
    "``````"
  )
  $body = $bodyLines -join "`n"
  $labels = "tipo:bug,prio:$prio,area:$area,$req"

  Invoke-Gh @(
    "issue", "create",
    "--title", $issueTitle,
    "--body", $body,
    "--label", $labels,
    "--milestone", $msTitle
  )
}

Write-Host "`n== Bootstrap concluido. Proximos passos manuais (UI do GitHub) ==" -ForegroundColor Green
Write-Host "  1. Criar Project v2 'Assistente de Vendas - Board' (secao 3.5)" -ForegroundColor White
Write-Host "  2. Adicionar campos customizados: Status, Sprint, Prioridade, REQ, Tipo, Estimativa" -ForegroundColor White
Write-Host "  3. Adicionar as issues criadas ao Project (bulk add)" -ForegroundColor White
Write-Host "  4. Configurar protecao de branches (politica_branches.md secao 5)" -ForegroundColor White
