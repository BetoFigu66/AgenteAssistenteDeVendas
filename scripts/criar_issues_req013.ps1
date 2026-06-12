<#
.SYNOPSIS
  Cria as 8 issues do backlog REQ-013 (Pares Q&A Curados).

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/backlog_req013_tarefas.md (v0.1)

.PARAMETER DryRun
  Imprime os comandos sem chama-los.
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
if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw "gh nao autenticado." }
$ErrorActionPreference = $prevEAP

Write-Host "`n== Labels adicionais ==" -ForegroundColor Green
$extraLabels = @(
  @{ name = "REQ-013"; color = "ededed"; desc = "Pares Q&A curados" },
  @{ name = "REQ-012"; color = "ededed"; desc = "Reports de problema" },
  @{ name = "REQ-014"; color = "ededed"; desc = "Configuracao runtime camadas conhecimento" },
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
if (-not $msExists) { throw "Milestone '$msTitle' nao encontrado." }

Write-Host "`n== Idempotencia ==" -ForegroundColor Green
$existingIssuesJson = gh issue list --state all --limit 200 --json title 2>$null
$existingIssueTitles = @()
if ($existingIssuesJson) {
  $existingIssueTitles = ($existingIssuesJson | ConvertFrom-Json) | ForEach-Object { $_.title }
}

Write-Host "`n== Criando issues do backlog REQ-013 ==" -ForegroundColor Green

$issues = @(
  @{
    title = "[REQ-013] T-01 -- Criacao de par Q&A a partir de report"
    body = @(
      "## Subitens REQ", "", "- REQ-013.7 -- Criacao a partir de report de problema", ""
      "## Contexto", "", "Hoje so e possivel criar par Q&A a partir de mensagem reprovada (REQ-013.6). Falta a integracao analoga com a tela de detalhe de report quando categoria for `resposta_inadequada` ou `template`.", ""
      "## Escopo", "", "- Botao `Criar par Q&A` no detalhe de report nas categorias suportadas.", "- Pre-preenche `pergunta` <- mensagem do cliente.", "- `id_externo` <- `report:<report_id>`.", "- Vincular `report_id` ao novo `ParQA` (FK opcional ou referencia por `id_externo`).", ""
      "## Validacao no painel", "", "- Abrir report categoria `resposta_inadequada` -> botao visivel.", "- Clicar -> modal com campos pre-preenchidos.", "- Par criado aparece em `QABasePage` como rascunho com origem do report.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-criar-par-qa-from-report", "commit:  feat(REQ-013/T-01): cria par Q&A a partir de detalhe de report", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-013,REQ-012"
  },
  @{
    title = "[REQ-013] T-02 -- Filtro por contexto na busca em producao"
    body = @(
      "## Subitens REQ", "", "- REQ-013.12 -- Filtro por contexto na busca", ""
      "## Contexto", "", "A busca atual em `/api/pares-qa/buscar` nao aceita filtro por `contexto`. REQ pede que o filtro exista como parametro opcional, desabilitado por default no POC.", ""
      "## Escopo", "", "- Parametro `contexto: str | None` no endpoint de busca.", "- Filtrar query SQLAlchemy por `ParQA.contexto == contexto` quando informado.", "- Index parcial no Postgres em `pares_qa.contexto`.", "- Documentar no swagger.", ""
      "## Validacao no painel", "", "- Tela admin de debug do RAG aceita filtrar resultado por contexto.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-filtro-contexto-busca", "commit:  feat(REQ-013/T-02): adiciona filtro opcional por contexto na busca Q&A", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-013"
  },
  @{
    title = "[REQ-013] T-03 -- Auditoria de uso de Q&A em ProcessamentoMensagem"
    body = @(
      "## Subitens REQ", "", "- REQ-013.14 -- Auditabilidade do uso", "- REQ-005.6 -- Decisoes do processamento", ""
      "## Contexto", "", "Quando uma resposta e entregue via Q&A curada, `ProcessamentoMensagem` deve registrar o caminho, o id do par e o score. Hoje so diz se RAG foi usado.", ""
      "## Escopo", "", "- Campos novos em `ProcessamentoMensagem`: `caminho_resposta` (`qa_curada` / `rag_documental` / `llm_generico` / `template`), `par_qa_id`, `qa_score`.", "- Atualizar `_decidir_resposta` para gravar.", "- Migration Alembic.", ""
      "## Validacao no painel", "", "- Detalhe da mensagem mostra caminho + id do par + score.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-auditoria-uso-qa", "commit:  feat(REQ-013/T-03): registra caminho de resposta e id do par Q&A em ProcessamentoMensagem", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-013,REQ-005"
  },
  @{
    title = "[REQ-013] T-04 -- Deteccao de duplicatas na criacao"
    body = @(
      "## Subitens REQ", "", "- REQ-013.17 -- Deteccao de duplicatas na criacao", ""
      "## Contexto", "", "Ao criar par novo, sistema nao alerta sobre perguntas similares ja existentes. Risco de duplicacao.", ""
      "## Escopo", "", "- No `POST /api/pares-qa`, gerar embedding temporario e buscar top-3 com score >= 0.85.", "- Retornar 200 com `duplicatas_candidatas` quando houver, sem bloquear.", "- UI exibe modal de confirmacao com lista de candidatos antes de salvar.", ""
      "## Validacao no painel", "", "- Tentar criar par com pergunta similar -> modal de alerta.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-deteccao-duplicatas", "commit:  feat(REQ-013/T-04): alerta de duplicatas na criacao de par Q&A", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-013"
  },
  @{
    title = "[REQ-013] T-05 -- Estatisticas no cabecalho da QABasePage"
    body = @(
      "## Subitens REQ", "", "- REQ-013.18 -- Estatisticas basicas", ""
      "## Contexto", "", "Painel nao tem contadores rapidos. Curador precisa rolar a lista para entender o estado da base.", ""
      "## Escopo", "", "- Endpoint `GET /api/pares-qa/estatisticas`: total ativos+aprovados, rascunhos pendentes, top N mais usados 7d/30d.", "- Cabecalho de `QABasePage` exibe 4 cards.", ""
      "## Validacao no painel", "", "- Contadores atualizam ao aprovar/desativar pares.", ""
      "## Dependencias", "", "T-03 (uso historico).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-estatisticas-qabase", "commit:  feat(REQ-013/T-05): adiciona estatisticas no cabecalho da QABasePage", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,area:frontend,REQ-013"
  },
  @{
    title = "[REQ-013] T-06 -- Persistencia de configuracao runtime entre reinicios"
    body = @(
      "## Subitens REQ", "", "- REQ-013.13 -- Configuracao dinamica em runtime", ""
      "## Contexto", "", "Configuracao de `QA_ENABLED` e `QA_SCORE_MINIMO` e volatil; reinicio do servidor restaura defaults.", ""
      "## Escopo", "", "- Tabela `configuracoes_runtime` (chave/valor/tipo/atualizado_em/atualizado_por).", "- PATCH `/api/config/rag` persiste no banco.", "- Boot carrega configuracoes antes de aceitar requisicoes.", "- Historico de alteracoes em tabela separada.", ""
      "## Validacao no painel", "", "- Mudar `QA_SCORE_MINIMO`, reiniciar servidor, valor persiste.", ""
      "## Dependencias", "", "REQ-014.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-persistir-config-runtime", "commit:  feat(REQ-013/T-06): persiste configuracao runtime entre reinicios", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-013,REQ-014"
  },
  @{
    title = "[REQ-013] T-07 -- Workflow de aprovacao com notificacao + historico de revisoes"
    body = @(
      "## Subitens REQ", "", "- REQ-013.16 -- Visualizacao de par + acoes", "- REQ-013.2 -- Workflow de aprovacao do par", ""
      "## Contexto", "", "Aprovacao e um toggle simples sem historico. Precisamos saber quem aprovou, quando, e ver revisoes/edicoes.", ""
      "## Escopo", "", "- Tabela `revisoes_par_qa` (par_qa_id, ator, acao, snapshot_antes_json, timestamp).", "- Hook nos endpoints PATCH/POST.", "- UI: timeline de revisoes no detalhe do par.", "- Notificacao in-app quando rascunho pendente ha mais de 7 dias.", ""
      "## Validacao no painel", "", "- Editar pergunta -> timeline mostra snapshot antes + ator + timestamp.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-workflow-aprovacao-historico", "commit:  feat(REQ-013/T-07): adiciona historico de revisoes e notificacao de rascunhos pendentes", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-013,REQ-005"
  },
  @{
    title = "[REQ-013] T-08 -- Ingestao em lote a partir de pastas/CSV"
    body = @(
      "## Subitens REQ", "", "- REQ-013.8 -- Ingestao em lote", ""
      "## Contexto", "", "Cadastro hoje e so manual. Para popular a base rapidamente, falta ingestao estruturada.", ""
      "## Escopo", "", "- Script `scripts/ingerir_pares_qa.py` aceitando markdown/CSV/JSON.", "- Endpoint admin `POST /api/pares-qa/ingestao` para upload via UI.", "- `id_externo` derivado do arquivo.", "- Pares entram como `aprovado=false`, sem embedding.", "- Tela de revisao em massa com selecao multipla + acao `aprovar selecionados`.", ""
      "## Validacao no painel", "", "- Subir CSV de 20 perguntas -> tabela de revisao com checkboxes; aprovar 5 -> embedding gerado.", ""
      "## Dependencias", "", "T-07 (workflow de aprovacao para revisao em massa).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-013-ingestao-lote-qa", "commit:  feat(REQ-013/T-08): adiciona ingestao em lote de pares Q&A", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:baixa,area:backend,area:frontend,REQ-013"
  }
)

foreach ($i in $issues) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray; continue
  }
  Invoke-Gh @("issue", "create", "--title", $i.title, "--body", $i.body, "--label", $i.labels, "--milestone", $msTitle)
}

Write-Host "`n== Concluido ==" -ForegroundColor Green
