<#
.SYNOPSIS
  Cria as 9 issues do backlog REQ-015 (Validacao CPF + Consulta Debitos).

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/backlog_req015_tarefas.md (v0.1)
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
  @{ name = "REQ-015"; color = "ededed"; desc = "Validacao CPF + Consulta Debitos" },
  @{ name = "REQ-004"; color = "ededed"; desc = "Escalonamento humano" },
  @{ name = "REQ-005"; color = "ededed"; desc = "Registro de interacoes / auditoria" },
  @{ name = "REQ-010"; color = "ededed"; desc = "Painel administrativo" },
  @{ name = "area:negocio"; color = "fbca04"; desc = "Decisoes de negocio / planejamento" }
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

Write-Host "`n== Criando issues do backlog REQ-015 ==" -ForegroundColor Green

$issues = @(
  @{
    title = "[REQ-015] T-01 -- Eco/confirmacao do CPF capturado"
    body = @(
      "## Subitens REQ", "", "- REQ-015.4 -- Confirmacao dos dados pelo cliente", ""
      "## Contexto", "", "Sistema valida CPF e persiste, mas nao ecoa para confirmacao. Igual a T-01 do REQ-001 mas para CPF.", ""
      "## Escopo", "", "- Apos `_processar_cpf_fornecido` validar, gerar template `CONFIRMA_CPF` com CPF formatado.", "- Estado `aguardando_confirmacao_cpf`.", "- Em `N`, reabrir captura; em `S`, marcar `pessoa.confirmado=true` e avancar.", ""
      "## Validacao no painel", "", "- CPF valido -> mensagem de confirmacao enviada.", "- Cliente `Sim` -> avanca; `Nao` -> loop.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-eco-confirmacao-cpf", "commit:  feat(REQ-015/T-01): implementa eco e confirmacao do CPF capturado", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-015"
  },
  @{
    title = "[REQ-015] T-02 -- Politica de 3 tentativas + escalonamento para CPF invalido"
    body = @(
      "## Subitens REQ", "", "- REQ-015.6 -- Tratamento de CPF invalido", ""
      "## Contexto", "", "Mesma politica do REQ-001.6 aplicada a CPF. Maximo 3 tentativas; apos esgotar, escalar com resumo dos CPFs **mascarados**.", ""
      "## Escopo", "", "- Contador `tentativas_cpf` em `NegociacaoInfo`.", "- Mensagem de erro indicando motivo (formato / digitos / sequencia trivial).", "- 3a falha -> escalonamento via REQ-004.9 com resumo mascarado.", "- Reset do contador ao iniciar nova negociacao.", ""
      "## Validacao no painel", "", "- 3 CPFs invalidos -> escalonamento + `aguardando_humano`.", ""
      "## Dependencias", "", "REQ-004, T-06 (mascaramento).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-politica-tentativas-cpf", "commit:  feat(REQ-015/T-02): implementa politica de 3 tentativas com escalonamento para CPF", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-015,REQ-004"
  },
  @{
    title = "[REQ-015] T-03 -- Tratamento de PF que recusa fornecer CPF"
    body = @(
      "## Subitens REQ", "", "- REQ-015.8 -- Tratamento de PF que nao fornece CPF", ""
      "## Contexto", "", "Cliente PF que nao quer informar CPF: sistema deve prosseguir com os campos nao dependentes (nome, telefone, endereco) e escalar antes de finalizar orcamento.", ""
      "## Escopo", "", "- Detectar recusa (`RECUSAR_CPF`) ou silencio apos 2 perguntas.", "- Marcar negociacao com `cpf_pendente=true`, `motivo='cliente_nao_forneceu'`.", "- Prosseguir qualificacao sem CPF.", "- Antes de gerar orcamento, status -> `aguardando_revisao_humana`.", "- Limite de 2 insistencias antes de respeitar recusa.", ""
      "## Validacao no painel", "", "- Conversa onde cliente diz `nao vou passar CPF` -> sistema segue, gera negociacao com flag.", ""
      "## Dependencias", "", "REQ-004.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-recusa-cpf", "commit:  feat(REQ-015/T-03): trata recusa de fornecer CPF com escalonamento antes do orcamento", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-015,REQ-004"
  },
  @{
    title = "[REQ-015] T-04 -- Decisao e integracao do provedor de consulta de debitos"
    body = @(
      "## Subitens REQ", "", "- REQ-015.3 -- Consulta a servico externo de debitos", ""
      "## Contexto", "", "Marcado como PENDENTE no REQ. Candidatos: Serasa Experian, SPC Brasil, Boa Vista (Equifax), Quod. Decisao depende de custo, cobertura e contrato.", ""
      "## Escopo", "", "- Levantar com `[planejador]` custo por consulta e cobertura dos 4 provedores.", "- Validar com Rita (Inforrel).", "- Implementar `services/debitos.py` com interface `ConsultorDebitos` + factory.", "- Mock local para dev.", "- Documentar credenciais em `.env.example`.", ""
      "## Validacao no painel", "", "- Em dev, mock retorna restricao configuravel.", "- Em prod (futuro), provedor real chamado via factory.", ""
      "## Dependencias", "", "ADR do `[planejador]` + `[arquiteto]`.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-provedor-debitos-decisao", "commit:  feat(REQ-015/T-04): adiciona ConsultorDebitos factory + mock para dev", "``````"
    ) -join "`n"
    labels = "tipo:task,prio:alta,area:backend,area:negocio,REQ-015"
  },
  @{
    title = "[REQ-015] T-05 -- Tratamento de restricao financeira com escalonamento humano"
    body = @(
      "## Subitens REQ", "", "- REQ-015.7 -- Tratamento de CPF com restricao (LGPD art. 20)", ""
      "## Contexto", "", "Quando consulta retorna restricao, sistema **nao** nega automaticamente; registra, sinaliza no painel e escala antes de finalizar orcamento.", ""
      "## Escopo", "", "- Apos `consultar_debitos`, registrar `restricao_financeira` em `NegociacaoInfo`.", "- **Nunca** mencionar restricao ao cliente.", "- Continuar qualificacao normalmente.", "- Ao gerar orcamento, se `restricao=sim`, status -> `aguardando_revisao_humana` com motivo `restricao_financeira`.", ""
      "## Validacao no painel", "", "- Mock com restricao -> conversa segue sem revelar; painel mostra badge.", "- Ao gerar orcamento -> status muda para revisao humana.", ""
      "## Dependencias", "", "T-04, T-08, REQ-004.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-tratamento-restricao", "commit:  feat(REQ-015/T-05): trata restricao financeira com revisao humana antes do orcamento", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-015,REQ-004"
  },
  @{
    title = "[REQ-015] T-06 -- Tratamento LGPD do CPF (mascaramento, finalidade, retencao)"
    body = @(
      "## Subitens REQ", "", "- REQ-015.13 -- Tratamento LGPD do CPF", ""
      "## Contexto", "", "REQ explicito sobre LGPD. Hoje CPF aparece em texto pleno em logs, modal de raciocinio e auditoria -- risco real.", ""
      "## Escopo", "", "- Funcao `mascarar_cpf(cpf)` -> `***.456.789-**`.", "- Logs, `ProcessamentoMensagem`, eventos REQ-005 e reports REQ-012 usam CPF mascarado.", "- CPF completo so em telas de cadastro e detalhe de orcamento.", "- Texto de finalidade na primeira solicitacao de CPF.", "- Job de anonimizacao periodica (default 24 meses).", "- Endpoint `DELETE /api/clientes/{telefone}/dados-pessoais`.", "- Bloquear indexacao de CPF pelo RAG (REQ-003).", ""
      "## Validacao no painel", "", "- Painel admin nunca mostra CPF completo fora do detalhe do cliente.", "- Modal de raciocinio mostra CPF mascarado.", ""
      "## Dependencias", "", "REQ-005, REQ-003.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-lgpd-cpf", "commit:  feat(REQ-015/T-06): aplica mascaramento LGPD do CPF em logs e auditoria", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-015,REQ-005"
  },
  @{
    title = "[REQ-015] T-07 -- Auditoria das consultas de debito"
    body = @(
      "## Subitens REQ", "", "- REQ-015.14 -- Auditoria das consultas de debito", ""
      "## Contexto", "", "Cada consulta de debitos deve gerar evento de auditoria com CPF mascarado. Nao persistir resultado completo em texto pleno.", ""
      "## Escopo", "", "- Tabela `auditoria_consulta_debitos` (cpf_mascarado, provedor, resultado_agregado_json, identificador_transacao, criado_em, criado_por).", "- Hook em `services/debitos.py` apos cada consulta.", "- Endpoint `/api/auditoria/debitos` (acesso restrito).", ""
      "## Validacao no painel", "", "- Tela admin `Auditoria de Consultas` lista com CPF mascarado.", ""
      "## Dependencias", "", "T-04, T-06, REQ-005.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-auditoria-debitos", "commit:  feat(REQ-015/T-07): adiciona auditoria de consultas de debito", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-015,REQ-005"
  },
  @{
    title = "[REQ-015] T-08 -- Sinalizacao visual de restricao no painel"
    body = @(
      "## Subitens REQ", "", "- REQ-015.5 -- Disponibilizacao para orcamento com destaque", "- REQ-015.7 -- Tratamento de restricao", "- REQ-010 -- Painel administrativo", ""
      "## Contexto", "", "Painel precisa destacar conversas/negociacoes onde o CPF tem restricao, sem expor o CPF completo.", ""
      "## Escopo", "", "- Badge `Restricao Financeira` no card de conversa e detalhe da negociacao.", "- Tooltip explicando.", "- Filtro na listagem por `com restricao / sem restricao / pendente / indisponivel`.", ""
      "## Validacao no painel", "", "- Negociacoes com `restricao=sim` mostram badge em vermelho.", ""
      "## Dependencias", "", "T-04, T-05.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-sinalizacao-restricao-painel", "commit:  feat(REQ-015/T-08): adiciona sinalizacao visual de restricao no painel", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:frontend,REQ-015,REQ-010"
  },
  @{
    title = "[REQ-015] T-09 -- Reuso de CPF ja validado em conversas futuras"
    body = @(
      "## Subitens REQ", "", "- REQ-015.10 -- Reuso de CPF ja validado", ""
      "## Contexto", "", "Cliente que ja validou CPF em conversa anterior (mesmo telefone) nao deve precisar fornecer de novo. Analogo a REQ-002.10 para CNPJ.", ""
      "## Escopo", "", "- Ao iniciar nova negociacao para telefone com `Pessoa` validada, herdar CPF.", "- Se cliente mencionar CPF diferente, perguntar antes de trocar (`CONFIRMA_TROCA_CPF`).", "- Se cliente pedir troca explicitamente, executar.", ""
      "## Validacao no painel", "", "- 2a conversa do mesmo telefone PF -> nao pede CPF.", "- CPF diferente -> sistema confirma antes de gravar.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/REQ-015-reuso-cpf-validado", "commit:  feat(REQ-015/T-09): reusa CPF ja validado em conversas futuras do mesmo telefone", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-015"
  }
)

foreach ($i in $issues) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray; continue
  }
  Invoke-Gh @("issue", "create", "--title", $i.title, "--body", $i.body, "--label", $i.labels, "--milestone", $msTitle)
}

Write-Host "`n== Concluido ==" -ForegroundColor Green
