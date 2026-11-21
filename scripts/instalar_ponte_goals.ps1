<#
.SYNOPSIS
    Registra (ou remove) a tarefa agendada da ponte reports -> goals do Claude.

.DESCRIPTION
    A cada N minutos chama, no WSL, scripts/ponte_goals.sh, que transforma em goal os reports
    marcados com "Correcao automatica pelo Claude" e dispara o executor (claude --bg). Enquanto
    houver goal de report executando, o processo continua vivo, o que mantem o WSL ligado; por
    isso MultipleInstances IgnoreNew e limite de execucao de 5 h.
    Log em logs\ponte_goals.log. Nao precisa de PowerShell como administrador.

.PARAMETER NivelQuota
    Trava de quota: so despacha se o uso semanal estiver ate NivelQuota x o ritmo proporcional
    (cada hora util, 8h-18h, desde o reinicio semanal soma 1/70). 1 = 100% do proporcional.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar_ponte_goals.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar_ponte_goals.ps1 -NivelQuota 0.8
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar_ponte_goals.ps1 -Remover
#>
[CmdletBinding()]
param(
    [int]$IntervaloMinutos = 10,
    [string]$Distro = "Ubuntu",
    [double]$NivelQuota = 1.0,
    [switch]$Remover,
    [string]$Nome = "PonteGoals-AssistenteVendas"
)

$ErrorActionPreference = "Stop"

if ($Remover) {
    if (Get-ScheduledTask -TaskName $Nome -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
        Write-Host "Tarefa '$Nome' removida." -ForegroundColor Yellow
    } else {
        Write-Host "Tarefa '$Nome' nao existe - nada a remover."
    }
    exit 0
}

# Caminho do script no WSL, a partir da pasta deste .ps1 (C:\... -> /mnt/c/...).
$raiz = Split-Path $PSScriptRoot -Parent
$script = "/mnt/" + $raiz.Substring(0,1).ToLower() + ($raiz.Substring(2) -replace '\\','/') + "/scripts/ponte_goals.sh"

$acao = New-ScheduledTaskAction -Execute "wsl.exe" -Argument ("-d $Distro -e bash `"$script`" --nivel-quota " + $NivelQuota.ToString([Globalization.CultureInfo]::InvariantCulture))

$gatilhoRepete = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervaloMinutos)
$gatilhoLogon  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$config = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 5) `
    -Hidden

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
    -Description "Transforma reports marcados para correcao automatica em goals do Claude a cada $IntervaloMinutos min." | Out-Null

Write-Host "Tarefa '$Nome' registrada: a cada $IntervaloMinutos min, $script no WSL ($Distro), nivel de quota $NivelQuota." -ForegroundColor Green
