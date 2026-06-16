<#
.SYNOPSIS
  Cria as 6 issues do backlog REQ-001 (Integracao Receita Federal / CNPJ).

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/backlog_req001_tarefas.md (v0.1)

  Pre-requisitos:
    - gh CLI instalado e autenticado
    - Labels e milestone Sprint 03 ja criados (scripts/bootstrap_github_projects.ps1)
    - Label REQ-001 criada (este script cria se nao existir)

.PARAMETER DryRun
  Imprime os comandos sem chama-los.

.EXAMPLE
  .\scripts\criar_issues_req001.ps1 -DryRun
  .\scripts\criar_issues_req001.ps1
#>

[CmdletBinding()]
param([switch]$DryRun)

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
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh nao autenticado. Rode: gh auth login" }
$ErrorActionPreference = $prevEAP
Write-Host "Auth OK." -ForegroundColor Green

Write-Host "`n== Labels adicionais ==" -ForegroundColor Green
$extraLabels = @(
  @{ name = "REQ-001"; color = "ededed"; desc = "Integracao Receita Federal (CNPJ)" },
  @{ name = "REQ-004"; color = "ededed"; desc = "Escalonamento humano" },
  @{ name = "REQ-005"; color = "ededed"; desc = "Registro de interacoes / auditoria" }
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

Write-Host "`n== Milestone Sprint 03 ==" -ForegroundColor Green
$msTitle = "Sprint 03"
$milestonesJson = gh api '/repos/{owner}/{repo}/milestones?state=open' 2>$null
$msExists = $null
if ($milestonesJson) {
  $msMatch = ($milestonesJson | ConvertFrom-Json) | Where-Object { $_.title -eq $msTitle } | Select-Object -First 1
  if ($msMatch) { $msExists = $msMatch.number }
}
if (-not $msExists) { throw "Milestone '$msTitle' nao encontrado. Rode .\scripts\bootstrap_github_projects.ps1" }
Write-Host "  milestone '$msTitle' OK (#$msExists)" -ForegroundColor DarkGray

Write-Host "`n== Idempotencia ==" -ForegroundColor Green
$existingIssuesJson = gh issue list --state all --limit 200 --json title 2>$null
$existingIssueTitles = @()
if ($existingIssuesJson) {
  $existingIssueTitles = ($existingIssuesJson | ConvertFrom-Json) | ForEach-Object { $_.title }
}

Write-Host "`n== Criando issues do backlog REQ-001 ==" -ForegroundColor Green

$issues = @(
  @{
    title = "[REQ-001] T-01 -- Eco/confirmacao dos dados retornados pela Receita"
    body = @(
      "## Subitens REQ", "", "- REQ-001.4 -- Confirmacao dos dados pelo cliente", "- REQ-001.5 -- Disponibilizacao dos dados para orcamento", ""
      "## Contexto", "", "Sistema valida CNPJ e persiste empresa, mas nao ecoa os dados para o cliente confirmar antes de prosseguir. Fluxo esperado: bot mostra razao social, endereco e situacao; cliente responde S/N; sistema avanca ou pede correcao.", ""
      "## Escopo", "", "- Apos `_processar_cnpj_fornecido` validar, gerar template `CONFIRMA_DADOS_EMPRESA`.", "- Estado de conversa: `aguardando_confirmacao_empresa`.", "- Detectar resposta via intencoes `CONFIRMAR`/`NEGAR`.", "- Em `N`, reabrir captura. Em `S`, marcar `empresa.confirmada=true` e avancar para qualificacao.", ""
      "## Validacao no painel", "", "- CNPJ valido -> painel mostra mensagem de confirmacao.", "- Cliente `Sim` -> avanca; `Nao` -> loop.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-001-eco-confirmacao-empresa", "commit:  feat(REQ-001/T-01): implementa eco e confirmacao dos dados da empresa", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-001"
  },
  @{
    title = "[REQ-001] T-02 -- Politica de 3 tentativas + escalonamento para humano"
    body = @(
      "## Subitens REQ", "", "- REQ-001.6 -- Tratamento de CNPJ invalido ou nao encontrado (politica de tentativas)", ""
      "## Contexto", "", "Hoje CNPJ invalido retorna mensagem generica sem contador. Politica formal: maximo 3 tentativas por conversa. Apos esgotar, escalar via REQ-004.9.", ""
      "## Escopo", "", "- Contador `tentativas_cnpj` em `NegociacaoInfo` ou `Negociacao`.", "- Mensagem de erro indica motivo (formato / nao encontrado / inativa).", "- 3a falha -> template `ESCALADO_BAIXA_CONFIANCA` com resumo dos CNPJs tentados.", "- Reset do contador ao iniciar nova negociacao.", ""
      "## Validacao no painel", "", "- Painel mostra contador atual.", "- 3 CNPJs invalidos -> escalonamento + status `aguardando_humano`.", ""
      "## Dependencias", "", "REQ-004 (escalonamento), T-04 (tipagem de erros).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-001-politica-tentativas-cnpj", "commit:  feat(REQ-001/T-02): implementa politica de 3 tentativas com escalonamento", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-001,REQ-004"
  },
  @{
    title = "[REQ-001] T-03 -- Tratamento de falhas da API externa com retry interno"
    body = @(
      "## Subitens REQ", "", "- REQ-001.10 -- Tratamento de falhas da API externa", ""
      "## Contexto", "", "`consultar_cnpj` em `services/receita.py` chama BrasilAPI sem retry estruturado. Timeouts viram erro generico.", ""
      "## Escopo", "", "- Retry com backoff exponencial (3 tentativas: 1s/2s/4s).", "- Distinguir erros: timeout, 5xx, 404, 429.", "- 404 -> consome tentativa do cliente.", "- Timeout/5xx/429 -> nao consome tentativa; apos esgotar retry, escala via REQ-004 com mensagem `consulta indisponivel`.", "- Considerar API alternativa configuravel (receitaws como fallback).", ""
      "## Validacao no painel", "", "- Simular timeout (mock) -> painel mostra retry + escalonamento sem consumir tentativa.", "- CNPJ inexistente -> consome tentativa normalmente.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-001-retry-api-receita", "commit:  feat(REQ-001/T-03): adiciona retry exponencial e fallback na consulta CNPJ", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-001"
  },
  @{
    title = "[REQ-001] T-04 -- Distincao falha de cliente vs. infraestrutura na contagem"
    body = @(
      "## Subitens REQ", "", "- REQ-001.6 (regra critica)", ""
      "## Contexto", "", "Subtarefa de T-02 isolada por ser regra de negocio sensivel: falha de infra **nao** consome tentativa do cliente.", ""
      "## Escopo", "", "- Erro tipado no resultado de `consultar_cnpj`: `{tipo: cliente|infra, motivo: ...}`.", "- `_processar_cnpj_fornecido` so incrementa contador quando `tipo=cliente`.", "- Mensagens de erro distintas para cliente vs. infra.", ""
      "## Validacao no painel", "", "- 3 timeouts de API -> contador continua em 0 + escalonamento por indisponibilidade.", "- 3 CNPJs invalidos -> contador chega a 3 + escalonamento por baixa confianca.", ""
      "## Dependencias", "", "T-02, T-03.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-001-tipagem-erros-receita", "commit:  feat(REQ-001/T-04): tipa erros da consulta CNPJ separando cliente vs. infra", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-001"
  },
  @{
    title = "[REQ-001] T-05 -- Instrumentacao de NFRs (tempo de resposta, disponibilidade, falhas)"
    body = @(
      "## Subitens REQ", "", "- REQ-001.8 -- Tempo de resposta < 3s", "- REQ-001.9 -- Disponibilidade > 99%", ""
      "## Contexto", "", "Nao ha metricas observaveis para tempo de resposta da Receita nem taxa de falha.", ""
      "## Escopo", "", "- Logar latencia de cada consulta CNPJ.", "- Endpoint `/api/metrics/req001` ou tabela `MetricasReceita`: total, sucesso, falha por tipo, p50/p95.", "- Painel admin: grafico simples + alertas quando p95 > 3s ou taxa de erro > 1%.", ""
      "## Validacao no painel", "", "- Aba `Metricas REQ-001` mostra contadores agregados das ultimas 24h/7d/30d.", ""
      "## Dependencias", "", "T-03 (tipos de erro padronizados).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-001-metricas-nfr", "commit:  feat(REQ-001/T-05): instrumenta metricas de latencia e disponibilidade da consulta CNPJ", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-001,REQ-005"
  },
  @{
    title = "[REQ-001] T-06 -- Auditoria de cada tentativa de CNPJ"
    body = @(
      "## Subitens REQ", "", "- REQ-001.6 (ultimo bullet)", "- REQ-005.4 -- Eventos de auditoria", ""
      "## Contexto", "", "Cada tentativa (CNPJ digitado, resultado, motivo) deve gerar evento de auditoria. Hoje so fica em `ProcessamentoMensagem`.", ""
      "## Escopo", "", "- Evento `tentativa_cnpj` em `EventoAuditoria` com: `cnpj`, `resultado`, `motivo`, `numero_tentativa`, `timestamp`.", "- Persistir antes de responder ao cliente.", "- Endpoint `/api/auditoria/cnpj?telefone=...` retorna historico.", ""
      "## Validacao no painel", "", "- Detalhe da conversa mostra timeline de tentativas com resultado.", ""
      "## Dependencias", "", "T-02 (contador), REQ-005 (estrutura de eventos).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-001-auditoria-tentativas-cnpj", "commit:  feat(REQ-001/T-06): registra eventos de auditoria por tentativa de CNPJ", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-001,REQ-005"
  }
)

foreach ($i in $issues) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray; continue
  }
  Invoke-Gh @("issue", "create", "--title", $i.title, "--body", $i.body, "--label", $i.labels, "--milestone", $msTitle)
}

Write-Host "`n== Concluido ==" -ForegroundColor Green
Write-Host "Proximos passos manuais:" -ForegroundColor White
Write-Host "  1. Adicionar issues ao Project v2 'Assistente de Vendas - Board' (bulk add)" -ForegroundColor White
Write-Host "  2. Definir Sprint, Prioridade e Estimativa nos campos customizados" -ForegroundColor White
