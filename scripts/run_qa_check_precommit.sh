#!/usr/bin/env bash
# Launcher do hook pre-commit — encontra o Python do venv sem depender do PATH.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QA="$ROOT/scripts/qa_check.py"

if [[ -x "$ROOT/backend/venv/bin/python" ]]; then
  exec "$ROOT/backend/venv/bin/python" "$QA" --escopo pre-commit --sem-cor
fi

if [[ -f "$ROOT/backend/venv/Scripts/python.exe" ]]; then
  exec "$ROOT/backend/venv/Scripts/python.exe" "$QA" --escopo pre-commit --sem-cor
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/scripts/run_qa_check_precommit.py"
fi

exec python "$ROOT/scripts/run_qa_check_precommit.py"
