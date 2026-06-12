<#
.SYNOPSIS
  Cria as 11 issues do backlog REQ-002 (Fluxo Conversacional Guiado)
  no repositorio AgenteAssistenteDeVendas.

.DESCRIPTION
  Base: artefatos/gerente_de_projetos/backlog_req002_tarefas.md (v0.3)

  Pre-requisitos:
    - gh CLI instalado e autenticado (gh auth status)
    - Labels e milestone Sprint 03 ja criados (scripts/bootstrap_github_projects.ps1)
    - Labels REQ-002, REQ-003, REQ-008, REQ-015 criadas (este script cria se nao existir)

  Itens NAO cobertos por este script:
    - Adicionar as issues criadas ao Project v2 "Assistente de Vendas - Board" (UI / bulk add)
    - Definir Sprint, Prioridade e Estimativa nos campos customizados do Project

.PARAMETER DryRun
  Se especificado, imprime os comandos que seriam executados sem chama-los.

.EXAMPLE
  .\scripts\criar_issues_req002.ps1 -DryRun
  .\scripts\criar_issues_req002.ps1
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
# Labels adicionais do REQ-002
# ---------------------------------------------------------------------------
Write-Host "`n== Labels adicionais ==" -ForegroundColor Green

$extraLabels = @(
  @{ name = "REQ-002"; color = "ededed"; desc = "Fluxo conversacional guiado" }
  @{ name = "REQ-003"; color = "ededed"; desc = "Base de respostas automaticas (Q&A / RAG)" }
  @{ name = "REQ-008"; color = "ededed"; desc = "Integracao WhatsApp (Twilio/Meta)" }
  @{ name = "REQ-015"; color = "ededed"; desc = "Validacao de CPF e consulta de debitos" }
)

$existingLabelsJson = gh label list --limit 200 --json name 2>$null
$existingLabelNames = @()
if ($existingLabelsJson) {
  $existingLabelNames = ($existingLabelsJson | ConvertFrom-Json) | ForEach-Object { $_.name }
}

foreach ($l in $extraLabels) {
  if ($existingLabelNames -contains $l.name) {
    Write-Host "  label '$($l.name)' ja existe - pulando" -ForegroundColor DarkGray
    continue
  }
  Invoke-Gh @("label", "create", $l.name, "--color", $l.color, "--description", $l.desc)
}

# ---------------------------------------------------------------------------
# Milestone Sprint 03
# ---------------------------------------------------------------------------
Write-Host "`n== Milestone Sprint 03 ==" -ForegroundColor Green

$msTitle = "Sprint 03"
$milestonesJson = gh api '/repos/{owner}/{repo}/milestones?state=open' 2>$null
$msExists = $null
if ($milestonesJson) {
  $msMatch = ($milestonesJson | ConvertFrom-Json) | Where-Object { $_.title -eq $msTitle } | Select-Object -First 1
  if ($msMatch) { $msExists = $msMatch.number }
}
if ($msExists) {
  Write-Host "  milestone '$msTitle' ja existe (#$msExists)" -ForegroundColor DarkGray
} else {
  throw "Milestone '$msTitle' nao encontrado. Rode primeiro: .\scripts\bootstrap_github_projects.ps1"
}

# ---------------------------------------------------------------------------
# Idempotencia: lista issues existentes
# ---------------------------------------------------------------------------
Write-Host "`n== Idempotencia ==" -ForegroundColor Green

$existingIssuesJson = gh issue list --state all --limit 200 --json title 2>$null
$existingIssueTitles = @()
if ($existingIssuesJson) {
  $existingIssueTitles = ($existingIssuesJson | ConvertFrom-Json) | ForEach-Object { $_.title }
}

# ---------------------------------------------------------------------------
# Issues do backlog REQ-002
# ---------------------------------------------------------------------------
Write-Host "`n== Criando issues do backlog REQ-002 ==" -ForegroundColor Green

$issues = @(
  @{
    title = "[REQ-002] T-01 -- Alinhar classificador as 4 categorias canonicas + nivel de confianca"
    body = @(
      "## Subitens REQ", "", "- REQ-002.1 -- Classificacao e roteamento das mensagens do cliente", "- REQ-002.1A -- Fallback condicional para classificacao ambigua ou de baixa confianca", ""
      "## Contexto", "", "`services/classificador.py` retorna `Intencao` (15 valores), `confianca` (float) e `confianca_nivel` (`alta`/`media`/`baixa`) -- este ultimo ja implementado com thresholds padrao 0.70/0.40. Nao ha ainda o campo `categoria` (1-4) nem `justificativa_curta`. O roteamento no `processador.py` ainda e por `Intencao`, nao por categoria.", ""
      "## Escopo", "", "- Adicionar campo `categoria` (enum 1-4) em `ResultadoClassificacao`, derivado da intencao atual ou de uma classificacao direta no prompt da LLM.", "- Consumir limiares de REQ-014 (`classificador_conf_alta_min`, `classificador_conf_baixa_max`) em vez de hardcoded.", "- Adicionar coluna `justificativa_curta` (opcional, string) para auditoria.", "- Adaptar `_decidir_resposta` no processador para rotear por **categoria** antes de qualquer outra decisao.", ""
      "## Validacao no painel", "", "- Painel exibe a categoria e o nivel de confianca no detalhe da mensagem (REQ-005.6).", "- Enviar 4 mensagens-tipo (uma por categoria) e conferir o roteamento.", ""
      "## Dependencias", "", "REQ-014 ja tem os limiares definidos; so precisa expor.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/classificador-categorias-confianca", "commit:  feat(REQ-002/T-01): adiciona categoria 1-4 e justificativa_curta ao classificador", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002"
  },
  @{
    title = "[REQ-002] T-02 -- Fallback condicional ao REQ-003 (Caso 2) e tratamento composto (Caso 3)"
    body = @(
      "## Subitens REQ", "", "- REQ-002.1A -- Caso 2 (confianca baixa -> fallback REQ-003) + Caso 3 (mensagem composta)", ""
      "## Contexto", "", "Nenhum fallback condicional implementado; mensagens compostas nao sao detectadas.", ""
      "## Escopo", "", "- **Caso 2**: quando `confianca_nivel = baixa` ou `categoria = nao_identificado`, consultar REQ-003 (Q&A/RAG) antes de devolver fallback generico. Registrar `fallback_req003 = true` em `ProcessamentoMensagem`.", "- **Caso 3**: detectar mensagem composta (resposta a pergunta anterior + pergunta embutida) e classificar a pergunta embutida via REQ-002.1, combinando a resposta.", "- Persistir `resultado_fallback` (`resposta_entregue` / `pediu_esclarecimento` / `escalou`).", ""
      "## Validacao no painel", "", "- `Quais produtos a Inforrel vende?` deve voltar com resposta da base mesmo se o classificador hesitar.", "- `5, mas voces tem modelo com biometria facial?` deve registrar `quantidade=5` E responder sobre facial.", ""
      "## Dependencias", "", "T-01 (classificador com categoria e confianca_nivel).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/fallback-condicional-mensagem-composta", "commit:  feat(REQ-002/T-02): implementa fallback REQ-003 e tratamento de mensagem composta", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002,REQ-003"
  },
  @{
    title = "[REQ-002] T-03 -- Roteamento pre-identificacao para perguntas de produto/empresa"
    body = @(
      "## Subitens REQ", "", "- REQ-002.1B -- Perguntas sobre produto/empresa antes da identificacao fiscal", ""
      "## Contexto", "", "Hoje o processador exige contato/empresa identificados antes de delegar a RAG. E a causa-raiz documentada em DEC-003 (`decisoes_requisitos.md`).", ""
      "## Escopo", "", "- Criar contato e atendimento **anonimos** (`empresa_id=null`, `tipo_documento=indefinido`) quando categoria 3 com confianca alta vier sem CNPJ/CPF.", "- Delegar a REQ-003 normalmente.", "- Quando o cliente informar documento fiscal posteriormente, **promover** o contato/atendimento preservando historico.", ""
      "## Validacao no painel", "", "- Telefone novo envia `Quais relogios de ponto voces vendem?` -> painel deve mostrar contato anonimo + resposta da base.", "- Em mensagem subsequente, cliente envia CNPJ -> contato e vinculado a empresa, conversa anterior preservada.", ""
      "## Dependencias", "", "T-01 (classificador com categoria).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/roteamento-pre-identificacao-rag", "commit:  feat(REQ-002/T-03): permite perguntas produto/empresa antes de identificacao fiscal", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002"
  },
  @{
    title = "[REQ-002] T-04 -- Identificacao PF/PJ e roteamento do documento fiscal"
    body = @(
      "## Subitens REQ", "", "- REQ-002.2A -- Identificar tipo de cliente (PF ou PJ)", "- REQ-002.10 -- Reuso de documento fiscal ja validado (parte PF<->PJ)", ""
      "## Contexto", "", "Fluxo PF ja existe no codigo: `FORNECER_CPF` no classificador, `_processar_cpf_fornecido` no processador, validacao de CPF (REQ-015.2), persistencia em `Pessoa` e `Negociacao` com `tipo_documento=CPF`. O fluxo PJ (CNPJ via REQ-001) tambem existe. O que falta e a **inferencia automatica** PF/PJ a partir da mensagem inicial e o roteamento dirigido antes de pedir o documento.", ""
      "## Escopo", "", "- Adicionar inferencia PF/PJ a partir da mensagem inicial (palavras-chave + heuristica do classificador / LLM).", "- Pergunta direta quando ambiguo: `E para uma empresa (CNPJ) ou pessoa fisica (CPF)?`.", "- Roteamento dirigido: detectado PJ -> REQ-001; detectado PF -> REQ-015; ambiguo -> pergunta.", "- Tratar troca de tipo no meio da conversa (preservar campos comuns, redefinir documento fiscal).", "- Reuso: se telefone ja tem PJ validada e cliente menciona CPF -> confirmacao pontual.", ""
      "## Validacao no painel", "", "- Mensagem `Quero orcamento para minha casa` -> pergunta dirigida ou inferencia PF.", "- Mensagem com CNPJ explicito -> fluxo PJ.", ""
      "## Dependencias", "", "REQ-015 ja implementado (validacao de CPF + consulta de debitos). T-01.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/identificacao-pf-pj-roteamento", "commit:  feat(REQ-002/T-04): adiciona inferencia PF/PJ e roteamento do documento fiscal", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002,REQ-015"
  },
  @{
    title = "[REQ-002] T-05 -- Estado dos campos do atendimento e mecanismo de perguntas dinamicas"
    body = @(
      "## Subitens REQ", "", "- REQ-002.3 -- Controle de estado dos campos de qualificacao", "- REQ-002.4 -- Mecanismo geral de definicao de perguntas dinamicas", ""
      "## Contexto", "", "`NegociacaoInfo` (ainda nao renomeado para `AtendimentoInfo` -- depende de REQ-016 T-A2) existe com `chave/valor/pendente/origem`. `_atualizar_infos_negociacao` no `processador.py` ja grava nome, email, tipo_produto e quantidade. Nao ha ainda catalogo canonico de campos nem calculo de `proxima pergunta`.", ""
      "## Escopo", "", "- Definir o **catalogo canonico de campos** por tipo de cliente (PF/PJ) e tipo de produto, marcando obrigatorios/opcionais/nao-aplicaveis.", "- Implementar servico `proxima_pergunta(atendimento)` que devolve o campo prioritario pendente, com base em ordem natural (tipo -> modelo -> quantidade -> software -> contato -> endereco).", "- Atualizar processador para chamar `proxima_pergunta` ao final de cada turno (quando categoria = 1 ou 2 e qualificacao nao concluida).", "- Suportar marcacao `nao_aplicavel` (ex.: catraca com software -> quantidade opcional).", ""
      "## Validacao no painel", "", "- Painel mostra a lista de campos com status (capturado / pendente / nao-aplicavel) na tela da conversa.", "- Cada resposta do cliente atualiza o estado e a proxima pergunta muda.", ""
      "## Dependencias", "", "T-04 (PF/PJ define o conjunto de campos); REQ-016 T-A2 (rename de `NegociacaoInfo` -> `AtendimentoInfo`).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/estado-campos-perguntas-dinamicas", "commit:  feat(REQ-002/T-05): implementa catalogo de campos e mecanismo de perguntas dinamicas", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,area:frontend,REQ-002"
  },
  @{
    title = "[REQ-002] T-06 -- Captura adaptativa por etapa (tipo, modelo, dados adicionais, endereco)"
    body = @(
      "## Subitens REQ", "", "- REQ-002.2 -- Identificar dados iniciais do cliente e armazena-los", "- REQ-002.3A -- Identificar tipo de produto/servico", "- REQ-002.3B -- Identificar modelo do produto", "- REQ-002.3C -- Coletar informacoes adicionais para orcamento", "- REQ-002.3D -- Coletar informacoes de endereco de entrega/instalacao", ""
      "## Contexto", "", "`EntidadesExtraidas` no `classificador.py` ja extrai tipo_produto, quantidade, nome e email via regex/LLM. Modelo, endereco completo, software e telefone ainda nao sao extraidos.", ""
      "## Escopo (subtarefas possiveis)", "", "- **T-06.1** -- Tipo de produto/servico (REQ-002.3A): expandir lista alem de catraca/relogio (CFTV, roteador, software, cancela, assistencia).", "- **T-06.2** -- Modelo (REQ-002.3B): catalogo de modelos por tipo (catraca: Fit/Box/Pedestal/Giratoria; relogio: cartografico/biometrico/facial; etc.).", "- **T-06.3** -- Dados adicionais (REQ-002.3C): nome do solicitante, quantidade/faixa, software existente, contato (e-mail/telefone). Atencao ao nome para PF (obrigatorio).", "- **T-06.4** -- Endereco (REQ-002.3D): logradouro, numero, bairro, cidade, UF, CEP, indicador instalacao/entrega/retirada.", ""
      "## Validacao no painel", "", "- Mensagem inicial rica (`orcamento de catraca biometrica para 10 pessoas em SP`) deve preencher multiplos campos de uma vez.", "- Painel permite ver e corrigir manualmente cada campo coletado.", ""
      "## Dependencias", "", "T-05 (catalogo de campos e perguntas dinamicas).", ""
      "## Branch sugerida", "", "``````", "branch:  feature/captura-adaptativa-etapas", "commit:  feat(REQ-002/T-06): expande captura de tipo, modelo, dados adicionais e endereco", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:alta,area:backend,REQ-002"
  },
  @{
    title = "[REQ-002] T-07 -- Validacoes de respostas capturadas"
    body = @(
      "## Subitens REQ", "", "- REQ-002.6 -- Validacao de respostas capturadas", ""
      "## Contexto", "", "Validacao de CNPJ via `validar_cnpj` ja existe. Demais validacoes (CPF, email, telefone, modelo, endereco, quantidade/faixa) ainda nao foram implementadas.", ""
      "## Escopo", "", "- Validar formato e digitos verificadores de **CPF** (referencia REQ-015.2).", "- Validar formato de **e-mail** e **telefone**.", "- Validar **modelo de produto** contra catalogo (T-06.2).", "- Validar **endereco completo** (campos obrigatorios minimos).", "- Validar **quantidade/faixa** aceitando numero exato, `ate N`, `N-M`, `N+`.", "- Quando invalido -> marcar campo como pendente e gerar pergunta de esclarecimento (T-09).", ""
      "## Validacao no painel", "", "- Submeter respostas invalidas (CPF errado, e-mail malformado, `umas tantas` como quantidade) e ver mensagem de esclarecimento.", ""
      "## Dependencias", "", "T-05, T-06.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/validacoes-respostas-capturadas", "commit:  feat(REQ-002/T-07): adiciona validacoes de CPF, email, telefone, modelo, endereco e quantidade", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-002"
  },
  @{
    title = "[REQ-002] T-08 -- Confirmacao dos dados extraidos e sumarizacao"
    body = @(
      "## Subitens REQ", "", "- REQ-002.5 -- Sumarizacao de dados de orcamento", "- REQ-002.16 -- Confirmacao dos dados extraidos da mensagem inicial", ""
      "## Contexto", "", "Nenhum mecanismo de eco consolidado ou sumarizacao implementado.", ""
      "## Escopo", "", "- Quando a mensagem inicial extrair multiplos campos, gerar um **eco consolidado** (`Entendi: catraca facial, 10 unidades, SP. Confere?`).", "- Para CNPJ usar a confirmacao do REQ-001.4; demais campos vao no eco do REQ-002.16.", "- Ao final da qualificacao, gerar **sumarizacao** (REQ-002.5) com todos os campos, separados por tipo de cliente, antes de encaminhar para orcamento.", ""
      "## Validacao no painel", "", "- Mensagem inicial com 4 dados -> uma unica mensagem de confirmacao.", "- Cliente confirma -> sistema avanca; cliente corrige -> campo correspondente volta para pendente.", ""
      "## Dependencias", "", "T-05, T-06, T-07.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/confirmacao-dados-sumarizacao", "commit:  feat(REQ-002/T-08): implementa eco consolidado e sumarizacao final da qualificacao", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-002"
  },
  @{
    title = "[REQ-002] T-09 -- Tratamento de ambiguidade com retry e RAG durante qualificacao"
    body = @(
      "## Subitens REQ", "", "- REQ-002.17 -- Consulta a base de respostas automaticas durante a qualificacao", "- REQ-002.21 -- Tratamento de respostas ambiguas", ""
      "## Contexto", "", "RAG existe mas sem retomada da qualificacao apos responder duvida. Retry de esclarecimento e contador de tentativas nao implementados.", ""
      "## Escopo", "", "- Contador de tentativas de esclarecimento por campo (ate 2 retries; 3 interacoes no total).", "- Reformulacao dirigida com opcoes enumeradas quando aplicavel.", "- Apos esgotar tentativas -> escalar via REQ-004.9 preservando dados validos.", "- Distinguir resposta ambigua de **pergunta sobre produto camuflada**: aplicar REQ-002.17 (delega a RAG) sem consumir tentativa.", "- REQ-002.17: apos responder duvida via RAG, **retomar** a pergunta pendente (reapresentar a ultima pergunta de qualificacao).", "- Auditoria por evento (REQ-005).", ""
      "## Validacao no painel", "", "- Painel mostra contador de tentativas no campo.", "- `Qual a diferenca entre biometrico e facial?` no meio do fluxo -> resposta + retomada da pergunta anterior.", ""
      "## Dependencias", "", "T-05, T-06, T-07.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/ambiguidade-retry-rag-qualificacao", "commit:  feat(REQ-002/T-09): implementa retry, retomada RAG e tratamento de ambiguidade", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:media,area:backend,REQ-002,REQ-003"
  },
  @{
    title = "[REQ-002] T-10 -- Abandono de conversa e reengajamento"
    body = @(
      "## Subitens REQ", "", "- REQ-002.22 -- Tratamento de abandono de conversa pelo cliente", ""
      "## Contexto", "", "Nenhum job/scheduler de inatividade implementado.", ""
      "## Escopo", "", "- Job/scheduler que detecta inatividade de 24h da ultima mensagem do cliente.", "- Enviar mensagem unica de reengajamento.", "- Apos 72h totais sem resposta -> finalizar conversa (status `Finalizacao` com motivo `abandono`), preservar dados.", "- Ao receber nova mensagem do mesmo telefone apos finalizacao -> nova conversa pelo classificador, oferecendo retomada do contexto anterior.", ""
      "## Validacao no painel", "", "- Painel permite simular passagem do tempo (ex.: botao `envelhecer 24h` em modo dev) ou expor as datas de checkpoint na conversa.", ""
      "## Dependencias", "", "T-05.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/abandono-conversa-reengajamento", "commit:  feat(REQ-002/T-10): adiciona deteccao de abandono e mensagem de reengajamento", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:baixa,area:backend,area:infra,REQ-002"
  },
  @{
    title = "[REQ-002] T-11 -- Integracao WhatsApp (agregadora -- apos maturidade do painel)"
    body = @(
      "## Subitens REQ", "", "- REQ-002.19 -- Tempo de resposta < 2s", "- REQ-002.20 -- Naturalidade da conversa", "- Comportamentos sensiveis ao formato WhatsApp", ""
      "## Contexto", "", "A integracao com WhatsApp (Twilio/Meta Cloud API, REQ-008) existe como esqueleto mas nao foi validada no canal real.", ""
      "## Escopo (agregador)", "", "- Integracao com Twilio/Meta Cloud API (REQ-008).", "- Validacao dos comportamentos do REQ-002 no canal real.", "- Ajustes de UX especificos (limite de caracteres, listas com botoes, midia).", "- Metricas de tempo de resposta (REQ-002.19).", "- Reteste dos cenarios CTF que dependem do canal.", ""
      "## Quando abrir como issues efetivas", "", "Quando T-01 a T-09 estiverem em status Done no painel administrativo.", ""
      "## Dependencias", "", "Todas as anteriores.", ""
      "## Branch sugerida", "", "``````", "branch:  feature/integracao-whatsapp-validacao-canal", "commit:  feat(REQ-002/T-11): integra e valida fluxo no canal WhatsApp", "``````"
    ) -join "`n"
    labels = "tipo:feature,prio:baixa,area:integracao,REQ-002,REQ-008"
  }
)

foreach ($i in $issues) {
  if ($existingIssueTitles -contains $i.title) {
    Write-Host "  issue '$($i.title)' ja existe - pulando" -ForegroundColor DarkGray
    continue
  }

  Invoke-Gh @(
    "issue", "create",
    "--title", $i.title,
    "--body", $i.body,
    "--label", $i.labels,
    "--milestone", $msTitle
  )
}

Write-Host "`n== Concluido ==" -ForegroundColor Green
Write-Host "Proximos passos manuais:" -ForegroundColor White
Write-Host "  1. Adicionar as issues criadas ao Project v2 'Assistente de Vendas - Board' (bulk add)" -ForegroundColor White
Write-Host "  2. Definir Sprint, Prioridade e Estimativa nos campos customizados do Project" -ForegroundColor White
