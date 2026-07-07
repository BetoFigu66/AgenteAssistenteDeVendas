# Launcher manual do QA check (pre-commit) no PowerShell.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root "backend\venv\Scripts\python.exe"
$Qa = Join-Path $Root "scripts\qa_check.py"

if (-not (Test-Path $Py)) {
    Write-Error @"
Python do venv nao encontrado em backend\venv\Scripts\python.exe
Crie o venv: cd backend; python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt
"@
}

& $Py $Qa --escopo pre-commit @args
exit $LASTEXITCODE
