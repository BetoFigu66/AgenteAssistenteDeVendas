"""
Launcher cross-platform para o hook pre-commit do QA Engineer.

Resolve o Python do venv local (Windows ou Unix) sem depender do PATH
nem de caminhos fixos no .pre-commit-config.yaml.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QA_CHECK = ROOT / "scripts" / "qa_check.py"
ARGS = ["--escopo", "pre-commit", "--sem-cor"]


def _venv_python_candidates() -> list[Path]:
    return [
        ROOT / "backend" / "venv" / "Scripts" / "python.exe",
        ROOT / "backend" / "venv" / "bin" / "python3",
        ROOT / "backend" / "venv" / "bin" / "python",
    ]


def resolve_python() -> Path:
    for candidate in _venv_python_candidates():
        if candidate.is_file():
            return candidate
    return Path(sys.executable)


def main() -> int:
    python = resolve_python()
    return subprocess.call([str(python), str(QA_CHECK), *ARGS])


if __name__ == "__main__":
    raise SystemExit(main())
