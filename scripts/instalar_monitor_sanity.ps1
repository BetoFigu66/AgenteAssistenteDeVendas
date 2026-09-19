<#
.SYNOPSIS
    Registra (ou remove) a tarefa agendada que roda o monitor do sanity check.

.DESCRIPTION
    Cria uma tarefa no Agendador de Tarefas do Windows que executa
    scripts\monitor_sanity.ps1 a cada N minutos. A tarefa roda na sua sessao
    (LogonType Interactive) - condicao para a notificacao do Windows aparecer.
    Nao precisa de PowerShell como administrador.

    Roda tambem no logon, para o monitoramento voltar sozinho depois de reiniciar.

.PARAMETER IntervaloMinutos
    De quanto em quanto tempo verificar. Default: 15.

.PARAMETER Distro
    Distro WSL onde o sanity_check.sh roda. Default: Ubuntu.

.PARAMETER Remover
    Remove a tarefa em vez de criar.

.PARAMETER Nome
    Nome da tarefa. Default: SanityCheck-AssistenteVendas.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar_monitor_sanity.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar_monitor_sanity.ps1 -IntervaloMinutos 5
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar_monitor_sanity.ps1 -Remover
#>
[CmdletBinding()]
param(
    [int]$IntervaloMinutos = 15,
    [string]$Distro = "Ubuntu",
    [switch]$Remover,
    [string]$Nome = "SanityCheck-AssistenteVendas"
)

$ErrorActionPreference = "Stop"

$Monitor = Join-Path $PSScriptRoot "monitor_sanity.ps1"

if ($Remover) {
    if (Get-ScheduledTask -TaskName $Nome -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
        Write-Host "Tarefa '$Nome' removida." -ForegroundColor Yellow
    } else {
        Write-Host "Tarefa '$Nome' nao existe - nada a remover."
    }
    exit 0
}

if (-not (Test-Path $Monitor)) {
    Write-Error "Nao encontrei $Monitor"
    exit 1
}

$acao = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ("-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Monitor`" -Distro $Distro")

# Dois gatilhos: repeticao continua a partir de agora, e mais um no logon para
# o monitoramento se restabelecer sozinho depois de um reboot.
$gatilhoRepete = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervaloMinutos)
$gatilhoLogon  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$config = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -Hidden

# Interactive: a notificacao so aparece se a tarefa rodar na sessao do usuario.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $Nome -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
    Write-Host "Tarefa anterior removida (reinstalando)."
}

Register-ScheduledTask -TaskName $Nome `
    -Action $acao `
    -Trigger @($gatilhoRepete, $gatilhoLogon) `
    -Settings $config `
    -Principal $principal `
    -Description "Verifica a infraestrutura do Assistente de Vendas a cada $IntervaloMinutos min e notifica em caso de falha." | Out-Null

Write-Host ""
Write-Host "Tarefa '$Nome' registrada - a cada $IntervaloMinutos minuto(s)." -ForegroundColor Green
Write-Host ""
Write-Host "  Rodar agora:      Start-ScheduledTask -TaskName '$Nome'"
Write-Host "  Ver estado:       Get-ScheduledTask -TaskName '$Nome' | Get-ScheduledTaskInfo"
Write-Host "  Pausar:           Disable-ScheduledTask -TaskName '$Nome'"
Write-Host "  Reativar:         Enable-ScheduledTask -TaskName '$Nome'"
Write-Host "  Remover:          .\scripts\instalar_monitor_sanity.ps1 -Remover"
Write-Host "  Testar o alerta:  .\scripts\monitor_sanity.ps1 -Teste"
Write-Host "  Log:              logs\sanity_check.log"
Write-Host ""
