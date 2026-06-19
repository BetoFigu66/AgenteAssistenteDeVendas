<#
.SYNOPSIS
  Remove as issues de tarefas tecnicas criadas no formato antigo (uma issue por subtarefa),
  preservando integralmente as issues de bug (titulos que comecam com "[CTF-").

.DESCRIPTION
  Issues removidas: aquelas com titulo no padrao "[REQ-XXX] T-YY --" ou "[T-AX]"
  (geradas pelos scripts criar_issues_req001, req002, req013, req015 e req016).

  Issues PRESERVADAS (nao tocadas por este script):
    - Qualquer issue cujo titulo comece com "BUG em CTF-" (bugs do QA Runner)
    - Qualquer issue que nao corresponda ao padrao de tarefas antigas

  IMPORTANTE: a GitHub CLI nao permite deletar issues (apenas fechar ou transferir).
  Este script fecha (state=closed) todas as issues antigas com o comentario
  "Substituida pela reorganizacao de issues por funcionalidade entregavel."
  Se voce tiver permissao de admin e quiser deletar via API, use o parametro -Deletar.

.PARAMETER DryRun
  Imprime as acoes sem executa-las.

.PARAMETER Deletar
  Deleta as issues via GraphQL (requer permissao de admin no repositorio).
  Por padrao o script apenas fecha as issues.

.EXAMPLE
  .\scripts\limpar_issues_antigas.ps1 -DryRun
  .\scripts\limpar_issues_antigas.ps1
  .\scripts\limpar_issues_antigas.ps1 -Deletar
#>

[CmdletBinding()]
param(
  [switch]$DryRun,
  [switch]$Deletar
)

$ErrorActionPreference = "Stop"

function Invoke-Gh {
  param([string[]]$Arguments)
  $cmd = "gh " + ($Arguments -join " ")
  if ($DryRun) {
    Write-Host "[DRY] $cmd" -ForegroundColor Yellow
    return $null
  }
  Write-Host "> $cmd" -ForegroundColor Cyan
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & gh @Arguments 2>$null
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $prev
  if ($exitCode -ne 0) {
    throw "Falhou: $cmd (exit $exitCode)"
  }
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
Write-Host "== Pre-flight ==" -ForegroundColor Green

$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& gh --version *>$null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh CLI nao instalado. Veja https://cli.github.com/" }
& gh auth status *>$null
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh nao autenticado. Rode: gh auth login" }
$ErrorActionPreference = $prevEAP
Write-Host "Auth OK." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Listar todas as issues abertas e fechadas
# ---------------------------------------------------------------------------
Write-Host "`n== Listando todas as issues (abertas e fechadas) ==" -ForegroundColor Green

$issuesJson = gh issue list --state all --limit 500 --json number,title,state 2>$null
if (-not $issuesJson) {
  Write-Host "Nenhuma issue encontrada." -ForegroundColor Yellow
  exit 0
}
$todasIssues = $issuesJson | ConvertFrom-Json
Write-Host "  Total de issues encontradas: $($todasIssues.Count)" -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# Filtrar: identificar issues antigas (subtarefas tecnicas) para remover
# Preservar: bugs "[CTF-" e qualquer coisa que nao seja padrao de tarefa antiga
# ---------------------------------------------------------------------------

# Classificacao das issues:
#
# PRESERVAR (bugs originais, formato com colchetes):
#   [Bug em CTF-XXX-YY] Titulo       (#2-#6 - criados manualmente por Kika)
#   [BUG em CTF-XXX-YY] Titulo       (variacao de maiusculas)
#
# REMOVER — tarefas tecnicas antigas:
#   [REQ-001] T-01 -- Titulo         (req001, req002, req013, req015)
#   [T-A1] Titulo                    (req016 sprint03 - sem prefixo REQ)
#   [REQ-016] T-A1 -- Titulo         (req016 formato unificado)
#
# REMOVER — bugs duplicados (criados pelo bootstrap, sem colchetes):
#   BUG em CTF-XXX-YY - Titulo       (#55-#59)
#
# REMOVER — issues administrativas avulsas por numero fixo:
#   #26 [Criacao de issues no projeto GitHub]

$numerosAdministrativos = @(26)

$issuesParaRemover = $todasIssues | Where-Object {
  $titulo = $_.title
  $numero = $_.number

  # PRESERVAR: bugs originais com colchetes (ex: "[Bug em CTF-001-03]" ou "[BUG em CTF-002-03]")
  if ($titulo -match '^\[Bug\s+em\s+CTF-'    ) { return $false }
  if ($titulo -match '^\[BUG\s+em\s+CTF-'    ) { return $false }

  # REMOVER: bugs duplicados sem colchetes (ex: "BUG em CTF-001-03 -")
  if ($titulo -match '^BUG\s+em\s+CTF-'      ) { return $true }

  # REMOVER: tarefas [T-AX] sem prefixo REQ (ex: "[T-A1] Migration...")
  if ($titulo -match '^\[T-A\d+[a-z]?\]'     ) { return $true }

  # REMOVER: tarefas [REQ-XXX] T-YY -- (req001, req002, req013, req015, req016)
  if ($titulo -match '^\[REQ-\d+\]\s+T-'     ) { return $true }

  # REMOVER: issues reorganizadas [REQ-XXX] F0N -- (criadas pelo criar_issues_reorganizadas.ps1)
  if ($titulo -match '^\[REQ-\d+\]\s+F\d+'   ) { return $true }

  # REMOVER: issues administrativas por numero
  if ($numerosAdministrativos -contains $numero) { return $true }

  return $false
}

$issuesPreservadas = $todasIssues | Where-Object { $_.number -notin ($issuesParaRemover | ForEach-Object { $_.number }) }

Write-Host "`n== Issues a remover ($($issuesParaRemover.Count)) ==" -ForegroundColor Red
foreach ($i in $issuesParaRemover | Sort-Object number) {
  Write-Host "  #$($i.number) [$($i.state)] $($i.title)" -ForegroundColor Red
}

Write-Host "`n== Issues preservadas ($($issuesPreservadas.Count)) ==" -ForegroundColor Green
foreach ($i in $issuesPreservadas | Sort-Object number) {
  Write-Host "  #$($i.number) [$($i.state)] $($i.title)" -ForegroundColor DarkGray
}

if ($issuesParaRemover.Count -eq 0) {
  Write-Host "`nNenhuma issue antiga encontrada. Nada a fazer." -ForegroundColor Green
  exit 0
}

# ---------------------------------------------------------------------------
# Confirmacao (somente em modo real)
# ---------------------------------------------------------------------------
if (-not $DryRun) {
  $acao = if ($Deletar) { "DELETAR PERMANENTEMENTE" } else { "FECHAR" }
  Write-Host "`n[ATENCAO] Prestes a $acao $($issuesParaRemover.Count) issues." -ForegroundColor Yellow
  $confirm = Read-Host "Digite 'SIM' para continuar"
  if ($confirm -ne "SIM") {
    Write-Host "Operacao cancelada pelo usuario." -ForegroundColor Yellow
    exit 0
  }
}

# ---------------------------------------------------------------------------
# Executar: fechar ou deletar
# ---------------------------------------------------------------------------
$comentario = "Substituida pela reorganizacao de issues por funcionalidade entregavel. Ver: artefatos/gerente_de_projetos/proposta_reorganizacao_issues.md"

if ($Deletar) {
  Write-Host "`n== Deletando issues antigas via GraphQL ==" -ForegroundColor Red

  # Obter o node ID do repositorio
  $repoNodeId = $null
  if (-not $DryRun) {
    $repoData = gh api graphql -f query='{ viewer { login } }' | ConvertFrom-Json
    $repoJson = gh repo view --json id | ConvertFrom-Json
    $repoNodeId = $repoJson.id
  }

  foreach ($issue in $issuesParaRemover | Sort-Object number) {
    Write-Host "  Deletando #$($issue.number) - $($issue.title)" -ForegroundColor Red

    if ($DryRun) {
      Write-Host "[DRY] gh api graphql deletar issue #$($issue.number)" -ForegroundColor Yellow
      continue
    }

    # Obter node ID da issue
    $issueDetail = gh api "/repos/{owner}/{repo}/issues/$($issue.number)" | ConvertFrom-Json
    $nodeId = $issueDetail.node_id

    $mutationQuery = 'mutation { deleteIssue(input: { issueId: "' + $nodeId + '" }) { repository { name } } }'
    $result = gh api graphql -f "query=$mutationQuery" 2>&1
    if ($LASTEXITCODE -ne 0) {
      Write-Host "  AVISO: nao foi possivel deletar #$($issue.number) (pode exigir permissao de admin): $result" -ForegroundColor Yellow
    } else {
      Write-Host "  Deletada #$($issue.number)" -ForegroundColor Green
    }
  }

} else {
  Write-Host "`n== Fechando issues antigas ==" -ForegroundColor Yellow

  foreach ($issue in $issuesParaRemover | Sort-Object number) {
    Write-Host "  Fechando #$($issue.number) - $($issue.title)" -ForegroundColor Yellow

    if ($issue.state -ne "CLOSED") {
      # Adiciona comentario explicativo antes de fechar
      Invoke-Gh @("issue", "comment", "$($issue.number)", "--body", $comentario) | Out-Null
      Invoke-Gh @("issue", "close", "$($issue.number)", "--reason", "not planned") | Out-Null
    } else {
      Write-Host "  (ja esta fechada - pulando)" -ForegroundColor DarkGray
    }
  }
}

# ---------------------------------------------------------------------------
# Resumo final
# ---------------------------------------------------------------------------
Write-Host "`n== Concluido ==" -ForegroundColor Green
$acao = if ($Deletar) { "deletadas" } else { "fechadas" }
$totalRemovidas = $issuesParaRemover.Count
$totalPreservadas = $issuesPreservadas.Count
Write-Host "  Issues ${acao}: $totalRemovidas" -ForegroundColor White
Write-Host "  Issues preservadas (bugs e outras): $totalPreservadas" -ForegroundColor White

if (-not $Deletar) {
  Write-Host "`n  Dica: para deletar permanentemente (requer admin), rode:" -ForegroundColor DarkGray
  Write-Host "  .\scripts\limpar_issues_antigas.ps1 -Deletar" -ForegroundColor DarkGray
}

Write-Host "`n  Proximo passo: rode os novos scripts de criacao de issues reorganizadas." -ForegroundColor White
