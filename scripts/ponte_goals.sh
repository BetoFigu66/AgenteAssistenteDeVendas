#!/usr/bin/env bash
# Chamado pela tarefa agendada do Windows (scripts/instalar_ponte_goals.ps1) via wsl.exe.
# Despacha os reports marcados para correção automática e fica vivo enquanto um goal de report
# estiver executando: o WSL desliga quando nenhum processo iniciado pelo wsl.exe continua rodando,
# e isso levaria junto a sessão `claude --bg` do executor.
set -euo pipefail
cd "$(dirname "$0")/../backend"
export PATH="$HOME/bin:$HOME/.local/bin:$PATH"
exec venv/bin/python -m scripts.ponte_reports_goals despachar --aguardar "$@" >> ../logs/ponte_goals.log 2>&1
