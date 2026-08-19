#!/usr/bin/env bash
# Launcher do hook pre-commit — mesmo padrao do run_qa_check_precommit.sh
# (nao precisa do venv do backend: sync_skill_windsurf.py so usa stdlib).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/sync_skill_windsurf.py"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT"
fi
exec python "$SCRIPT"
