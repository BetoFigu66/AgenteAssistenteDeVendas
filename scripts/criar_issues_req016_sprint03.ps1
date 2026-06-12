<#
.SYNOPSIS
  Cria as 7 issues do Sprint 03 referentes ao REQ-016 (Renomeacao Negociacao -> Atendimento)
  no repositorio AgenteAssistenteDeVendas.

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/backlog_req016_atendimentos.md (v0.2)
  Tarefas cobertas neste script (Sprint 03):
    T-A1   Migration Alembic: rename de tabelas, colunas e FKs negociacoes -> atendimentos
    T-A1b  Migration Alembic: drop dos estados antigos com remapeamento
    T-A2   Refactor de models, schemas e servicos (Python)
    T-A3   Coluna ultima_mensagem_at + atualizacao em cada mensagem
    T-A4   Logica de criacao automatica de atendimento integrada ao classificador
    T-A8   Parametro janela_continuacao_atendimento_horas em parametros (REQ-014.2C)
    T-A11  Renomeacoes de UI no frontend (labels, badges, breadcrumbs)

  As tarefas T-A5, T-A6, T-A7, T-A9, T-A10, T-A12 ficam para Sprint 04 (script proprio).

  Pre-requisitos:
    - gh CLI instalado e autenticado (gh auth status)
    - Labels e milestone Sprint 03 ja criados (scripts/bootstrap_github_projects.ps1)
    - Label REQ-016 criada (este script cria se nao existir)

  Itens NAO cobertos por este script:
    - Adicionar as issues criadas ao Project v2 "Assistente de Vendas - Board" (UI / bulk add)
    - Definir Sprint, Prioridade e Estimativa nos campos customizados do Project

.PARAMETER DryRun
  Se especificado, imprime os comandos que seriam executados sem chama-los.

.EXAMPLE
  .\scripts\criar_issues_req016_sprint03.ps1 -DryRun
  .\scripts\criar_issues_req016_sprint03.ps1
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
# Garantir labels extras (alem das do bootstrap)
# ---------------------------------------------------------------------------
Write-Host "`n== Garantir labels extras (REQ-016, area:db) ==" -ForegroundColor Green

$extraLabels = @(
  @{ name = "REQ-016";  color = "ededed"; desc = "Identificacao e numeracao de atendimentos (renomeacao de negociacao)" }
  @{ name = "area:db";  color = "5319e7"; desc = "Banco de dados, migrations Alembic, schema" }
)
$existingLabelsJson = gh label list --limit 200 --json name 2>$null
$existingLabelNames = @()
if ($existingLabelsJson) {
  $existingLabelNames = ($existingLabelsJson | ConvertFrom-Json) | ForEach-Object { $_.name }
}
foreach ($lbl in $extraLabels) {
  if ($existingLabelNames -contains $lbl.name) {
    Write-Host "  label '$($lbl.name)' ja existe - pulando" -ForegroundColor DarkGray
  } else {
    Invoke-Gh @("label", "create", $lbl.name, "--color", $lbl.color, "--description", $lbl.desc)
  }
}

# Validar milestone Sprint 03
$msTitle = "Sprint 03"
$milestonesJson = gh api '/repos/{owner}/{repo}/milestones?state=open' 2>$null
$msExists = $null
if ($milestonesJson) {
  $msMatch = ($milestonesJson | ConvertFrom-Json) | Where-Object { $_.title -eq $msTitle } | Select-Object -First 1
  if ($msMatch) { $msExists = $msMatch.number }
}
if (-not $msExists) {
  throw "Milestone '$msTitle' nao encontrado. Rode primeiro: .\scripts\bootstrap_github_projects.ps1"
}
Write-Host "Milestone '$msTitle' OK (#$msExists)." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Issues do Sprint 03 - REQ-016
# ---------------------------------------------------------------------------
Write-Host "`n== Criando issues do Sprint 03 (REQ-016) ==" -ForegroundColor Green

$repoNameWithOwner = (gh repo view --json nameWithOwner | ConvertFrom-Json).nameWithOwner
$repoUrlBase = "https://github.com/$repoNameWithOwner/blob/master/artefatos/gerente_de_projetos"
$backlogUrl  = "$repoUrlBase/backlog_req016_atendimentos.md"

# Coletar issues existentes (abertas e fechadas) para idempotencia por titulo
$existingIssues = @()
$existingIssuesJson = gh issue list --state all --limit 500 --json number,title 2>$null
if ($existingIssuesJson) {
  $existingIssues = $existingIssuesJson | ConvertFrom-Json
}

$tarefas = @(
  @{
    id = "T-A1"
    titulo = "Migration Alembic: rename negociacoes -> atendimentos (tabelas, colunas, FKs)"
    prio = "alta"
    areas = @("area:backend", "area:db")
    reqs  = @("REQ-016")
    branch = "feature/migration-rename-atendimentos"
    commit = "feat(REQ-016): migration de rename negociacoes -> atendimentos"
    escopo = @(
      "Tabelas: negociacoes -> atendimentos; negociacao_infos -> atendimento_infos.",
      "FKs em orcamentos, conversas, mensagens, atendimento_infos: negociacao_id -> atendimento_id.",
      "Coluna numero_negociacao_cliente -> numero_atendimento_cliente.",
      "Indices renomeados (ix_negociacoes_* -> ix_atendimentos_*).",
      "Index unico composto (contato_id, numero_atendimento_cliente) preservado.",
      "Downgrade: rename reverso completo, sem perda de dados.",
      "NAO cobre mudanca de dominio de status nem motivo_encerramento (isso fica em T-A1b)."
    )
    validacao = @(
      "alembic upgrade head e alembic downgrade -1 rodam limpos.",
      "SELECT COUNT(*) antes/depois bate.",
      "\d+ atendimentos no psql mostra todas as FKs."
    )
    deps = "Nenhuma."
  }
  @{
    id = "T-A1b"
    titulo = "Migration Alembic: drop dos estados antigos com remapeamento"
    prio = "alta"
    areas = @("area:backend", "area:db")
    reqs  = @("REQ-016", "REQ-006")
    branch = "feature/migration-estados-atendimento"
    commit = "feat(REQ-016): drop dos estados antigos com remapeamento e motivo_encerramento"
    escopo = @(
      "Restringe status em atendimentos a {ativo, encerrado} via CHECK constraint.",
      "Adiciona coluna motivo_encerramento (string nullable).",
      "Remapeia em uma unica transacao: aberta->ativo; abandonada->encerrado(inatividade); ganha->encerrado(ganha_legado); perdida->encerrado(perdida_legado).",
      "Auditoria: log com contador por transicao.",
      "Downgrade restaura dominio antigo usando motivo_encerramento como pista.",
      "NAO mexe em orcamentos (status do orcamento permanece inalterado, REQ-006 v1.8)."
    )
    validacao = @(
      "upgrade em base com dados sinteticos cobre todos os 4 estados antigos.",
      "downgrade restaura sem perda.",
      "Sanity: nenhum encerrado sem motivo_encerramento."
    )
    deps = "T-A1."
  }
  @{
    id = "T-A2"
    titulo = "Refactor Python: models, schemas, services e rotas para o novo vocabulario"
    prio = "alta"
    areas = @("area:backend")
    reqs  = @("REQ-016")
    branch = "feature/refactor-atendimento-python"
    commit = "refactor(REQ-016): rename Negociacao -> Atendimento em models, services e schemas"
    escopo = @(
      "models.py: Negociacao -> Atendimento; NegociacaoInfo -> AtendimentoInfo; relacionamentos.",
      "services/processador.py: identificar_negociacao -> identificar_atendimento, vars e funcoes.",
      "services/classificador.py: payloads, docstrings e comentarios.",
      "services/respostas/gerador.py e templates.py: tokens e textos.",
      "Schemas Pydantic e rotas: /api/negociacoes/* -> /api/atendimentos/*.",
      "Testes unitarios e fixtures atualizados."
    )
    validacao = @(
      "pytest backend/tests passa.",
      "grep -ri negocia backend/ sem matches relevantes (so historicos explicitos)."
    )
    deps = "T-A1 e T-A1b (model precisa refletir o dominio final com motivo_encerramento)."
  }
  @{
    id = "T-A3"
    titulo = "Coluna ultima_mensagem_at no atendimento + atualizacao a cada mensagem"
    prio = "alta"
    areas = @("area:backend")
    reqs  = @("REQ-016")
    branch = "feature/atendimento-ultima-mensagem-at"
    commit = "feat(REQ-016): coluna ultima_mensagem_at e atualizacao no processador"
    escopo = @(
      "Migration: adicionar ultima_mensagem_at em atendimentos (datetime, nullable).",
      "processador.py: atualizar ultima_mensagem_at em cada mensagem do cliente.",
      "Atualizar tambem ao reabrir um atendimento (preparacao para T-A7)."
    )
    validacao = @(
      "Painel mostra timestamp atualizado na lista de atendimentos.",
      "Envio de mensagem pelo simulador reflete imediatamente no campo."
    )
    deps = "T-A1, T-A2."
  }
  @{
    id = "T-A4"
    titulo = "Logica de criacao automatica de atendimento (services/atendimentos.py)"
    prio = "alta"
    areas = @("area:backend")
    reqs  = @("REQ-016", "REQ-002")
    branch = "feature/criacao-automatica-atendimento"
    commit = "feat(REQ-016): criacao automatica de atendimento com numeracao sequencial"
    escopo = @(
      "Novo modulo services/atendimentos.py com obter_ou_criar_atendimento_para_mensagem.",
      "Contato novo -> cria atendimento ativo numero 1.",
      "Contato com atendimento ativo -> reutiliza.",
      "Contato so com atendimentos encerrados -> placeholder para T-A5 (Sprint 04).",
      "numero_atendimento_cliente = MAX + 1 com lock para evitar race em webhooks."
    )
    validacao = @(
      "Telefone novo gera Atendimento #1.",
      "Segundo atendimento do mesmo telefone vira #2.",
      "Testes de concorrencia simulada (dois inserts proximos) nao geram numeros duplicados."
    )
    deps = "T-A1, T-A2."
  }
  @{
    id = "T-A8"
    titulo = "Parametro janela_continuacao_atendimento_horas em parametros (REQ-014.2C)"
    prio = "alta"
    areas = @("area:backend")
    reqs  = @("REQ-016", "REQ-014")
    branch = "feature/parametro-janela-continuacao"
    commit = "feat(REQ-014.2C): parametro janela_continuacao_atendimento_horas (default 24)"
    escopo = @(
      "Seed em parametros: nome=janela_continuacao_atendimento_horas, valor=24, descricao.",
      "Validacao: inteiro >= 1.",
      "Expor em GET /api/config/rag (ou endpoint dedicado de configuracao).",
      "ParametroService le valor vigente no momento da chegada da mensagem (sem cache de longo prazo)."
    )
    validacao = @(
      "Alterar para 1 via painel/endpoint faz a janela diminuir imediatamente.",
      "GET retorna o valor atual junto com os demais parametros."
    )
    deps = "Pode ser feita em paralelo com T-A1/T-A2 (apenas precisa do REQ-014 ja em base)."
  }
  @{
    id = "T-A11"
    titulo = "Frontend: renomear UI Negociacao -> Atendimento (labels, badges, rotas)"
    prio = "media"
    areas = @("area:frontend")
    reqs  = @("REQ-016", "REQ-010")
    branch = "feature/ui-rename-atendimento"
    commit = "refactor(REQ-016): renomear UI e rotas Negociacao -> Atendimento"
    escopo = @(
      "Substituir labels visiveis: 'Negociacao' -> 'Atendimento', 'N negociacao' -> 'N atendimento'.",
      "Atualizar tooltips, badges (Atendimento #N no cabecalho - REQ-010.7A v1.3) e breadcrumbs.",
      "Rotas frontend: /negociacoes/* -> /atendimentos/*.",
      "Atualizar chaves de traducao (se houver) e snapshots de teste."
    )
    validacao = @(
      "Busca por 'Negocia' no frontend retorna apenas comentarios historicos.",
      "Sem regressao visivel no painel ao navegar pelas paginas principais."
    )
    deps = "T-A2 (endpoints renomeados)."
  }
)

foreach ($t in $tarefas) {
  $issueTitle = "[$($t.id)] $($t.titulo)"

  $jaExiste = $existingIssues | Where-Object { $_.title -eq $issueTitle } | Select-Object -First 1
  if ($jaExiste) {
    Write-Host "  issue #$($jaExiste.number) ja existe para '$($t.id)' - pulando" -ForegroundColor DarkGray
    continue
  }

  $bodyLines = @(
    "## Identificacao",
    "",
    "- **Tarefa do backlog:** ``$($t.id)``",
    "- **REQ(s):** " + (($t.reqs | ForEach-Object { "``$_``" }) -join ", "),
    "- **Prioridade:** $($t.prio)",
    "- **Sprint:** Sprint 03",
    "- **Backlog completo:** [backlog_req016_atendimentos.md]($backlogUrl)",
    "",
    "## Escopo"
  )
  foreach ($linha in $t.escopo) {
    $bodyLines += "- $linha"
  }
  $bodyLines += @(
    "",
    "## Criterios de validacao"
  )
  foreach ($linha in $t.validacao) {
    $bodyLines += "- $linha"
  }
  $bodyLines += @(
    "",
    "## Dependencias",
    "",
    "$($t.deps)",
    "",
    "## Branch e commit sugeridos",
    "",
    "``````",
    "branch:  $($t.branch)",
    "commit:  $($t.commit)",
    "``````"
  )
  $body = $bodyLines -join "`n"

  $labelList = @("tipo:task", "prio:$($t.prio)") + $t.areas + $t.reqs
  $labels = $labelList -join ","

  Invoke-Gh @(
    "issue", "create",
    "--title", $issueTitle,
    "--body", $body,
    "--label", $labels,
    "--milestone", $msTitle
  )
}

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
Write-Host "`n== Criacao concluida. Proximos passos manuais ==" -ForegroundColor Green
Write-Host "  1. Adicionar as 7 issues criadas ao Project 'Assistente de Vendas - Board' (bulk add via UI)" -ForegroundColor White
Write-Host "  2. Preencher campos customizados do Project: Sprint=Sprint 03, Tipo=Task, Estimativa (em pontos), Status=Todo" -ForegroundColor White
Write-Host "  3. Confirmar ordem de execucao: T-A1 -> T-A1b -> T-A2 -> (T-A3 / T-A4 / T-A8 / T-A11)" -ForegroundColor White
Write-Host "  4. Quando concluir Sprint 03, rodar o script equivalente para Sprint 04 (T-A5..T-A12)" -ForegroundColor White
