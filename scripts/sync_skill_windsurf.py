#!/usr/bin/env python3
"""Espelha .claude/skills/<skill>/*.md para .windsurf/skills/<skill>/*.md.

`.claude/skills/` e a fonte da verdade (editada manualmente, hoje só pelo Beto).
`.windsurf/skills/` e um espelho gerado — Devin Desktop/Windsurf (usado pela Kika)
descobre skills no mesmo formato "Agent Skills" (SKILL.md com frontmatter YAML),
sem precisar adaptar conteudo. Ver `docs/comandos_uteis.md` — secao "Skill de
code review — sincronizacao com Windsurf".

Rodado automaticamente pelo hook pre-commit (`.pre-commit-config.yaml`) sempre que
algo em `.claude/skills/` for commitado; pode tambem ser chamado manualmente:
    python scripts/sync_skill_windsurf.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTE = ROOT / ".claude" / "skills"
DESTINO = ROOT / ".windsurf" / "skills"


def sincronizar() -> list[Path]:
    """Copia cada *.md de .claude/skills/<nome>/ para .windsurf/skills/<nome>/.

    Retorna a lista de arquivos de destino que foram criados ou alterados.
    Unidirecional (fonte → espelho) — nunca lê de `.windsurf/skills/`.
    """
    alterados: list[Path] = []
    if not FONTE.is_dir():
        return alterados
    for skill_dir in sorted(p for p in FONTE.iterdir() if p.is_dir()):
        destino_dir = DESTINO / skill_dir.name
        for origem in sorted(skill_dir.glob("*.md")):
            destino = destino_dir / origem.name
            conteudo = origem.read_text(encoding="utf-8")
            if destino.exists() and destino.read_text(encoding="utf-8") == conteudo:
                continue
            destino_dir.mkdir(parents=True, exist_ok=True)
            destino.write_text(conteudo, encoding="utf-8")
            alterados.append(destino)
    return alterados


def main() -> int:
    alterados = sincronizar()
    if not alterados:
        return 0
    for arq in alterados:
        print(f"[sync-skill-windsurf] atualizado: {arq.relative_to(ROOT)}")
    # Re-adiciona ao index — mesmo padrao de hooks que reformatam (black/isort):
    # sai com erro pedindo pra rodar `git add`/`git commit` de novo, agora com o
    # espelho ja atualizado e incluido no mesmo commit.
    subprocess.run(["git", "add", str(DESTINO)], cwd=ROOT, check=False)
    print("[sync-skill-windsurf] .windsurf/skills atualizado e re-adicionado — rode 'git commit' de novo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
