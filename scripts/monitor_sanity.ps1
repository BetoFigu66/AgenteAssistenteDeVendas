<#
.SYNOPSIS
    Executa o sanity_check.sh (no WSL) e alerta no Windows quando algo cai.

.DESCRIPTION
    Chamado pela tarefa agendada criada por instalar_monitor_sanity.ps1.
    Roda o sanity_check.sh em modo --json, grava o resultado em
    logs\sanity_check.log e dispara uma notificacao do Windows quando o
    estado muda para FALHA (e outra quando volta ao ar).

    Nao notifica a cada execucao: so em mudanca de estado, mais um lembrete
    a cada -RepetirAvisoMin enquanto o problema persistir. Sem isso, 15 em 15
    minutos o alerta viraria ruido e voce pararia de olhar.

.PARAMETER Distro
    Nome da distro WSL. Default: Ubuntu.

.PARAMETER RepetirAvisoMin
    Enquanto continuar em falha, repete o alerta a cada N minutos. Default: 60.

.PARAMETER NotificarAvisos
    Tambem notifica em AVISO (por padrao avisos so vao para o log).

.PARAMETER Profundo
    Passa --profundo ao sanity_check.sh (envia mensagem real pelo /webhook e
    apaga o dado de teste depois). Use com parcimonia em execucao agendada.

.PARAMETER Teste
    Forca uma notificacao de exemplo, para conferir se o alerta aparece.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\monitor_sanity.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\monitor_sanity.ps1 -Teste
#>
[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu",
    [int]$RepetirAvisoMin = 60,
    [switch]$NotificarAvisos,
    [switch]$Profundo,
    [switch]$Teste
)

$ErrorActionPreference = "Stop"

$Raiz       = Split-Path -Parent $PSScriptRoot
$DirLogs    = Join-Path $Raiz "logs"
$Log        = Join-Path $DirLogs "sanity_check.log"
$Estado     = Join-Path $DirLogs ".sanity_estado.json"
$LimiteLog  = 5MB

if (-not (Test-Path $DirLogs)) { New-Item -ItemType Directory -Path $DirLogs -Force | Out-Null }

# ---------------------------------------------------------------------------
# Notificacao (toast nativo do Windows; PowerShell 5.1, sem modulo extra)
# ---------------------------------------------------------------------------

function Enviar-Notificacao {
    param([string]$Titulo, [string]$Texto)
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType=WindowsRuntime] | Out-Null
        # AppID do proprio PowerShell: evita ter que registrar um atalho no Menu Iniciar.
        $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        $t = [System.Security.SecurityElement]::Escape($Titulo)
        $x = [System.Security.SecurityElement]::Escape($Texto)
        $xml = "<toast><visual><binding template='ToastGeneric'><text>$t</text><text>$x</text></binding></visual></toast>"
        $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
        $doc.LoadXml($xml)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $doc
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
        return $true
    } catch {
        # Fallback: balao na area de notificacao (funciona sem WinRT).
        try {
            Add-Type -AssemblyName System.Windows.Forms
            $icone = New-Object System.Windows.Forms.NotifyIcon
            $icone.Icon = [System.Drawing.SystemIcons]::Warning
            $icone.BalloonTipTitle = $Titulo
            $icone.BalloonTipText  = $Texto
            $icone.Visible = $true
            $icone.ShowBalloonTip(15000)
            Start-Sleep -Seconds 12
            $icone.Dispose()
            return $true
        } catch { return $false }
    }
}

function Escrever-Log {
    param([string]$Linha)
    if ((Test-Path $Log) -and ((Get-Item $Log).Length -gt $LimiteLog)) {
        Move-Item $Log "$Log.1" -Force
    }
    "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Linha |
        Out-File -FilePath $Log -Append -Encoding utf8
}

if ($Teste) {
    $enviou = Enviar-Notificacao "Sanity check - teste" "Se voce esta vendo isso, o alerta esta funcionando."
    Write-Host ("Notificacao de teste: " + $(if ($enviou) { "enviada" } else { "FALHOU" }))
    exit 0
}

# ---------------------------------------------------------------------------
# Execucao do sanity_check.sh dentro do WSL
# ---------------------------------------------------------------------------

# Converte C:\Beto\... -> /mnt/c/Beto/... na mao: passar o caminho com
# contrabarras para o wsl.exe faz ele comer os separadores.
function ConvertTo-CaminhoWsl {
    param([string]$Caminho)
    $p = $Caminho -replace '\\', '/'
    if ($p -match '^([A-Za-z]):(/.*)$') {
        return "/mnt/" + $Matches[1].ToLower() + $Matches[2]
    }
    return $p
}

$caminhoWsl = ConvertTo-CaminhoWsl $Raiz

# Confere que o WSL responde e que o script esta la antes de tentar rodar.
$existe = (& wsl.exe -d $Distro -- bash -lc "test -x '$caminhoWsl/sanity_check.sh' && echo sim" 2>&1 | Out-String).Trim()
if ($existe -ne "sim") {
    $msg = "WSL/distro '$Distro' indisponivel, ou sanity_check.sh nao encontrado em $caminhoWsl."
    Escrever-Log "ERRO_MONITOR  $msg"
    Enviar-Notificacao "Sanity check - monitor com problema" $msg | Out-Null
    exit 3
}

$flags = "--json"
if ($Profundo) { $flags = "--json --profundo" }

$saida = & wsl.exe -d $Distro -- bash -lc "cd '$caminhoWsl' && ./sanity_check.sh $flags" 2>&1
$codigo = $LASTEXITCODE

# A ultima linha e o resumo: {"resumo":true,"status":"OK|AVISO|FALHA",...}
$linhaResumo = ($saida | Where-Object { $_ -match '"resumo"\s*:\s*true' } | Select-Object -Last 1)

if ($linhaResumo) {
    $resumo  = $linhaResumo | ConvertFrom-Json
    $status  = $resumo.status
    $detalhe = $resumo.detalhe
    $contagem = "ok=$($resumo.ok) avisos=$($resumo.avisos) falhas=$($resumo.falhas)"
} else {
    $status   = "FALHA"
    $detalhe  = "sanity_check.sh nao devolveu resumo (exit $codigo)"
    $contagem = "ok=? avisos=? falhas=?"
}

Escrever-Log ("{0,-6} {1}{2}" -f $status, $contagem, $(if ($detalhe) { "  | $detalhe" } else { "" }))

# Detalhe de cada check falho tambem vai para o log - e o que voce le depois.
if ($status -ne "OK") {
    # -cmatch: sensivel a maiusculas de proposito. Sem isso a linha de resumo
    # ("status":"FALHA") tambem casaria e viraria um check fantasma sem nome.
    $saida | Where-Object { $_ -cmatch '"status"\s*:\s*"(falha|aviso)"' } | ForEach-Object {
        try {
            $c = $_ | ConvertFrom-Json
            Escrever-Log ("       - [{0}] {1}: {2}{3}" -f $c.status.ToUpper(), $c.check, $c.detalhe,
                          $(if ($c.dica) { "  ({0})" -f $c.dica } else { "" }))
        } catch { Escrever-Log ("       - " + $_) }
    }
}

# ---------------------------------------------------------------------------
# Decisao de notificar (so em mudanca de estado, ou lembrete periodico)
# ---------------------------------------------------------------------------

$anterior = $null
if (Test-Path $Estado) {
    try { $anterior = Get-Content $Estado -Raw | ConvertFrom-Json } catch { $anterior = $null }
}
$statusAnterior = if ($anterior) { $anterior.status } else { "OK" }
$ultimoAviso    = if ($anterior -and $anterior.ultimoAviso) { [datetime]$anterior.ultimoAviso } else { [datetime]::MinValue }

$ruim = ($status -eq "FALHA") -or ($NotificarAvisos -and $status -eq "AVISO")
$eraRuim = ($statusAnterior -eq "FALHA") -or ($NotificarAvisos -and $statusAnterior -eq "AVISO")

$notificar = $false
$titulo = ""; $texto = ""

if ($ruim -and -not $eraRuim) {
    $notificar = $true
    $titulo = "Assistente de Vendas fora do ar"
    $texto  = if ($detalhe) { $detalhe } else { "Falha detectada no sanity check." }
} elseif ($ruim -and $eraRuim -and ((Get-Date) - $ultimoAviso).TotalMinutes -ge $RepetirAvisoMin) {
    $notificar = $true
    $titulo = "Assistente de Vendas ainda fora do ar"
    $texto  = if ($detalhe) { $detalhe } else { "Falha continua." }
} elseif (-not $ruim -and $eraRuim) {
    $notificar = $true
    $titulo = "Assistente de Vendas voltou ao ar"
    $texto  = "Todos os checks passaram ($contagem)."
}

if ($notificar) {
    if ($texto.Length -gt 240) { $texto = $texto.Substring(0, 237) + "..." }
    Enviar-Notificacao $titulo "$texto`nDetalhes: logs\sanity_check.log" | Out-Null
    $ultimoAviso = Get-Date
}

@{ status = $status; ultimoAviso = $ultimoAviso.ToString("o"); em = (Get-Date).ToString("o") } |
    ConvertTo-Json | Out-File -FilePath $Estado -Encoding utf8

Write-Host "$status  $contagem  $detalhe"
exit $codigo
