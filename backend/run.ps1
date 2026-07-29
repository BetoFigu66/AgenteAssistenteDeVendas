$ErrorActionPreference = "Stop"

& "$PSScriptRoot\venv\Scripts\Activate.ps1"
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
