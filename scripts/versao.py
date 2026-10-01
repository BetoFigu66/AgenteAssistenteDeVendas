#!/usr/bin/env python3
"""Versão do backend e do frontend, por data e hora da última mudança de cada lado.

Cada lado tem o seu arquivo `VERSAO` (`backend/VERSAO`, `frontend/VERSAO`), com uma linha
no formato `AAAA.MM.DD-HHMM` (horário de Brasília). Mudança só num lado não mexe no outro.

Conta como mudança do lado só o que muda o sistema (decisão do Beto, 01/10/2026): código,
migrações e configuração de build. Não contam testes, documentação (`*.md`), scripts de
apoio (`backend/scripts/`), logs e os textos de ajuda das telas (`frontend/src/ajuda/`).

Uso (da raiz do repositório):
    python scripts/versao.py atualizar           # lados com mudança staged; grava e faz git add
    python scripts/versao.py atualizar --lado back
    python scripts/versao.py mostrar
    python scripts/versao.py verificar           # o que o check de pre-commit roda

O check `versao-atualizada` (agentes/qa_engineer.py) bloqueia o commit que muda um lado sem
atualizar o `VERSAO` dele.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Horário de Brasília fixo (sem horário de verão desde 2019). Não usa `zoneinfo` porque o
# hook também roda no Python do Windows, que não traz a base de fusos sem o pacote `tzdata`.
FUSO = timezone(timedelta(hours=-3))
FORMATO = re.compile(r"^\d{4}\.\d{2}\.\d{2}-\d{4}$")

LADOS = {
    "back": {
        "pasta": "backend/",
        "arquivo": "backend/VERSAO",
        "fora": ("backend/tests/", "backend/scripts/", "backend/logs/"),
    },
    "front": {
        "pasta": "frontend/",
        "arquivo": "frontend/VERSAO",
        "fora": ("frontend/src/ajuda/", "frontend/node_modules/", "frontend/dist/"),
    },
}


def lado_do_arquivo(caminho: str):
    """Lado cujo sistema o arquivo muda, ou None se não muda nenhum."""
    caminho = caminho.replace("\\", "/")
    if caminho.endswith(".md"):
        return None
    for nome, lado in LADOS.items():
        if caminho == lado["arquivo"]:
            return None
        if caminho.startswith(lado["pasta"]) and not caminho.startswith(lado["fora"]):
            return nome
    return None


def _git(*args: str) -> list[str]:
    saida = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    return [linha for linha in saida.splitlines() if linha.strip()]


def arquivos_staged() -> list[str]:
    return _git("diff", "--cached", "--name-only", "--diff-filter=ACMRD")


def lados_alterados(arquivos: list[str]) -> set[str]:
    return {lado for lado in map(lado_do_arquivo, arquivos) if lado}


def versao_agora() -> str:
    return datetime.now(FUSO).strftime("%Y.%m.%d-%H%M")


def ler(lado: str) -> str:
    arquivo = RAIZ / LADOS[lado]["arquivo"]
    return arquivo.read_text(encoding="utf-8").strip() if arquivo.exists() else ""


def verificar() -> list[str]:
    """Problemas que impedem o commit: lado mudado sem `VERSAO` staged, ou formato inválido."""
    staged = arquivos_staged()
    problemas = []
    for lado in sorted(lados_alterados(staged)):
        arquivo = LADOS[lado]["arquivo"]
        if arquivo not in staged:
            problemas.append(f"{lado}: há mudança em {LADOS[lado]['pasta']} e {arquivo} não foi atualizado")
    for lado, dados in LADOS.items():
        if dados["arquivo"] in staged and not FORMATO.match(ler(lado)):
            problemas.append(f"{lado}: {dados['arquivo']} fora do formato AAAA.MM.DD-HHMM ({ler(lado)!r})")
    return problemas


def atualizar(lados: set[str]) -> None:
    versao = versao_agora()
    for lado in sorted(lados):
        arquivo = LADOS[lado]["arquivo"]
        (RAIZ / arquivo).write_text(versao + "\n", encoding="utf-8")
        _git("add", arquivo)
        print(f"{lado}: {versao}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_atualizar = sub.add_parser("atualizar")
    p_atualizar.add_argument("--lado", choices=["back", "front", "ambos"])
    sub.add_parser("mostrar")
    sub.add_parser("verificar")
    args = parser.parse_args()

    if args.comando == "mostrar":
        for lado in LADOS:
            print(f"{lado}: {ler(lado) or '(sem VERSAO)'}")
        return 0
    if args.comando == "verificar":
        problemas = verificar()
        for problema in problemas:
            print(problema)
        return 1 if problemas else 0

    if args.lado:
        lados = set(LADOS) if args.lado == "ambos" else {args.lado}
    else:
        lados = lados_alterados(arquivos_staged())
    if not lados:
        print("Nenhuma mudança staged que altere o sistema; nada a atualizar.")
        return 0
    atualizar(lados)
    return 0


if __name__ == "__main__":
    sys.exit(main())
