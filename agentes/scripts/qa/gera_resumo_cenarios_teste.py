"""Gera o resumo de execucao a partir do plano de testes manual.

Le `artefatos/qa/cenarios_teste_sprint02.md`, conta os cenarios por REQ
e por status (`[ ]`, `[OK]`, `[FAIL]`, `[N/A]`) e:

  1. Imprime a tabela no terminal.
  2. Atualiza a tabela "## 4. Resumo de execucao" do proprio markdown
     com os contadores (in-place).

Uso:
    python agentes/scripts/qa/gera_resumo_cenarios_teste.py
    python agentes/scripts/qa/gera_resumo_cenarios_teste.py --no-write   # so imprime

Convencoes parseadas:
  - Cabecalhos de cenario: linhas comecando com `#### CT-<REQ>-<NN>` ou `#### CT-E2E-<NN>`.
  - Status do cenario: ultima linha `**Status:** [<flag>]` antes do proximo cenario.
    Flags reconhecidos: ` ` (vazio), `OK`, `FAIL`, `N/A` (case-insensitive).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLANO_PATH = ROOT / "artefatos" / "qa" / "cenarios_teste_sprint02.md"

CT_HEADER_RE = re.compile(r"^####\s+CTF?-(?P<grupo>\w+)-(?P<num>\d+)\s+", re.MULTILINE)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*\[(?P<flag>[^\]]*)\]\s*$", re.MULTILINE)

STATUS_KEYS = ("OK", "FAIL", "N/A", "PENDENTE")


def _classificar_flag(flag: str) -> str:
    f = flag.strip().upper()
    if f == "OK":
        return "OK"
    if f == "FAIL":
        return "FAIL"
    if f in ("N/A", "NA"):
        return "N/A"
    return "PENDENTE"


def _grupo_label(grupo: str) -> str:
    if grupo.upper() == "E2E":
        return "E2E"
    if re.fullmatch(r"\d+", grupo):
        return f"REQ-{int(grupo):03d}"
    return grupo


def parsear(conteudo: str) -> "OrderedDict[str, dict]":
    """Retorna OrderedDict[grupo_label] = {OK, FAIL, N/A, PENDENTE, total}."""
    matches = list(CT_HEADER_RE.finditer(conteudo))
    resumo: "OrderedDict[str, dict]" = OrderedDict()

    for i, m in enumerate(matches):
        grupo = _grupo_label(m.group("grupo"))
        inicio = m.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(conteudo)
        bloco = conteudo[inicio:fim]
        sm = STATUS_RE.search(bloco)
        flag = _classificar_flag(sm.group("flag")) if sm else "PENDENTE"
        if grupo not in resumo:
            resumo[grupo] = {k: 0 for k in STATUS_KEYS}
            resumo[grupo]["total"] = 0
        resumo[grupo][flag] += 1
        resumo[grupo]["total"] += 1

    # ordena: REQs por numero, E2E por ultimo
    def _sort_key(label: str):
        if label.startswith("REQ-"):
            try:
                return (0, int(label.split("-")[1]))
            except ValueError:
                return (0, 9999)
        return (1, 0) if label == "E2E" else (2, 0)

    return OrderedDict(sorted(resumo.items(), key=lambda kv: _sort_key(kv[0])))


def montar_tabela_md(resumo: "OrderedDict[str, dict]") -> str:
    linhas = [
        "| REQ | Cenários | OK | FAIL | N/A |",
        "|-----|---------:|---:|----:|----:|",
    ]
    totais = defaultdict(int)
    for grupo, c in resumo.items():
        linhas.append(
            f"| {grupo} | {c['total']} | {c['OK']} | {c['FAIL']} | {c['N/A']} |"
        )
        for k in STATUS_KEYS + ("total",):
            totais[k] += c[k]
    linhas.append(
        f"| **Total** | **{totais['total']}** | "
        f"{totais['OK']} | {totais['FAIL']} | {totais['N/A']} |"
    )
    return "\n".join(linhas)


def imprimir_terminal(resumo: "OrderedDict[str, dict]") -> None:
    print(f"{'Grupo':<10} {'Total':>6} {'OK':>4} {'FAIL':>5} {'N/A':>4} {'Pend':>5}")
    print("-" * 40)
    totais = defaultdict(int)
    for grupo, c in resumo.items():
        print(f"{grupo:<10} {c['total']:>6} {c['OK']:>4} {c['FAIL']:>5} {c['N/A']:>4} {c['PENDENTE']:>5}")
        for k in STATUS_KEYS + ("total",):
            totais[k] += c[k]
    print("-" * 40)
    print(f"{'TOTAL':<10} {totais['total']:>6} {totais['OK']:>4} "
          f"{totais['FAIL']:>5} {totais['N/A']:>4} {totais['PENDENTE']:>5}")


# Marcadores para a substituicao in-place da tabela §4.
TABELA_BLOCO_RE = re.compile(
    r"(## 4\. Resumo de execu[\u00e7c]\u00e3o[\s\S]*?\n)"
    r"\|\s*REQ\s*\|[\s\S]*?\n\|\s*\*\*Total\*\*[^\n]*\n",
    re.MULTILINE,
)


def atualizar_arquivo(conteudo: str, tabela_md: str) -> str:
    novo_bloco = (
        "## 4. Resumo de execução\n\n"
        "> Atualizado automaticamente por `agentes/scripts/qa/gera_resumo_cenarios_teste.py`.\n\n"
        f"{tabela_md}\n"
    )
    if not TABELA_BLOCO_RE.search(conteudo):
        raise RuntimeError("Tabela de resumo (## 4) nao encontrada para atualizacao.")
    return TABELA_BLOCO_RE.sub(novo_bloco, conteudo, count=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true",
                        help="apenas imprime no terminal, nao altera o arquivo")
    parser.add_argument("--arquivo", type=Path, default=PLANO_PATH,
                        help=f"caminho do plano (padrao: {PLANO_PATH.relative_to(ROOT)})")
    args = parser.parse_args()

    if not args.arquivo.exists():
        print(f"[ERRO] Plano nao encontrado: {args.arquivo}", file=sys.stderr)
        return 1

    conteudo = args.arquivo.read_text(encoding="utf-8")
    resumo = parsear(conteudo)
    if not resumo:
        print("[AVISO] Nenhum cenario CT-* encontrado.", file=sys.stderr)
        return 1

    imprimir_terminal(resumo)
    if args.no_write:
        return 0

    tabela_md = montar_tabela_md(resumo)
    novo = atualizar_arquivo(conteudo, tabela_md)
    if novo != conteudo:
        args.arquivo.write_text(novo, encoding="utf-8")
        print(f"\nOK - tabela §4 atualizada em {args.arquivo.relative_to(ROOT)}")
    else:
        print("\n(nenhuma mudanca na tabela §4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
