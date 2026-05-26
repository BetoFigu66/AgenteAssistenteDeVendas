"""
CLI do QA Engineer — executa os checks registrados e reporta.

Uso:
    python scripts/qa_check.py                      # roda todos os checks
    python scripts/qa_check.py --escopo pre-commit  # so checks do escopo
    python scripts/qa_check.py --check gitkeep-redundantes
    python scripts/qa_check.py --listar             # lista checks registrados

Codigos de saida:
    0 -> tudo passou OU so ha warnings/infos (nao bloqueia commit)
    1 -> ao menos um check com severidade `error` falhou (bloqueia commit)
"""

from __future__ import annotations

import argparse

# Importa QAEngineer diretamente do arquivo, sem carregar agentes/__init__.py
# (evita dependencias pesadas como python-pptx usadas por outros agentes)
import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Pre-registra base_agente em sys.modules para que o import relativo do
# qa_engineer.py nao dispare o agentes/__init__.py (que carrega deps pesadas)
_base_path = RAIZ / "agentes" / "base_agente.py"
_base_spec = importlib.util.spec_from_file_location("agentes.base_agente", _base_path)
_base_module = importlib.util.module_from_spec(_base_spec)
_base_module.__package__ = "agentes"
sys.modules["agentes.base_agente"] = _base_module
_base_spec.loader.exec_module(_base_module)

_qa_path = RAIZ / "agentes" / "qa_engineer.py"
_spec = importlib.util.spec_from_file_location("agentes.qa_engineer", _qa_path)
_qa_module = importlib.util.module_from_spec(_spec)
_qa_module.__package__ = "agentes"
sys.modules["agentes.qa_engineer"] = _qa_module
_spec.loader.exec_module(_qa_module)
QAEngineer = _qa_module.QAEngineer


CORES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "dim": "\033[2m",
}


def _c(texto: str, cor: str, usar_cor: bool) -> str:
    if not usar_cor:
        return texto
    return f"{CORES[cor]}{texto}{CORES['reset']}"


def _emoji_resultado(passou: bool, severidade: str) -> str:
    if passou:
        return "[OK]"
    if severidade == "error":
        return "[ERRO]"
    if severidade == "warning":
        return "[AVISO]"
    return "[INFO]"


def imprimir_listagem(qa: QAEngineer, escopo: str | None, usar_cor: bool) -> None:
    checks = qa.listar_checks(escopo=escopo)
    if not checks:
        print("Nenhum check registrado para o escopo informado.")
        return
    print(_c(f"Checks registrados ({len(checks)}):", "bold", usar_cor))
    for c in checks:
        escopos = ",".join(c["escopos"])
        print(f"  - {c['id']:<30} [{c['severidade']:<7}] escopos={escopos}\n    {c['titulo']}")


def imprimir_relatorio(relatorio: dict, usar_cor: bool) -> None:
    print(_c("=" * 70, "dim", usar_cor))
    print(_c("QA Engineer — relatorio de checks", "bold", usar_cor))
    print(_c("=" * 70, "dim", usar_cor))

    for r in relatorio["resultados"]:
        cor = "green" if r["passou"] else ("red" if r["severidade"] == "error" else "yellow")
        status = _emoji_resultado(r["passou"], r["severidade"])
        severidade_tag = "" if r["passou"] else f" [{r['severidade']}]"
        print(f"\n{_c(status, cor, usar_cor)} {_c(r['id'], 'bold', usar_cor)}{severidade_tag} — {r['titulo']}")
        print(f"    {r['mensagem']}")
        if r["findings"]:
            for f in r["findings"][:50]:
                print(f"      - {f}")
            if len(r["findings"]) > 50:
                print(f"      ... (+{len(r['findings']) - 50} ocultados)")
        if not r["passou"] and r["dica_correcao"]:
            print(f"    {_c('Dica:', 'dim', usar_cor)} {r['dica_correcao']}")
        if r["comandos_uteis"]:
            print("    Comandos uteis:")
            for f in r["comandos_uteis"][:50]:
                print(f"      - {f}")
            if len(r["comandos_uteis"]) > 50:
                print(f"      ... (+{len(r['findings']) - 50} ocultados)")

    print(_c("\n" + "-" * 70, "dim", usar_cor))
    total = relatorio["total"]
    passaram = relatorio["passaram"]
    falharam_e = relatorio["falharam_error"]
    falharam_w = relatorio["falharam_warning"]
    print(
        f"Total: {total}  "
        f"| {_c(f'Passaram: {passaram}', 'green', usar_cor)}  "
        f"| {_c(f'Errors: {falharam_e}', 'red', usar_cor)}  "
        f"| {_c(f'Warnings: {falharam_w}', 'yellow', usar_cor)}"
    )
    if relatorio["bloqueia_commit"]:
        print(_c("\nCommit BLOQUEADO: ha checks com severidade `error`.", "red", usar_cor))
    elif falharam_w > 0:
        print(_c("\nCommit PERMITIDO, mas ha warnings para revisar.", "yellow", usar_cor))
    else:
        print(_c("\nTudo certo.", "green", usar_cor))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa checks do QA Engineer.",
    )
    parser.add_argument(
        "--escopo",
        choices=["sempre", "pre-commit", "pre-push", "release"],
        help="Filtra checks pelo escopo (padrao: roda todos os registrados).",
    )
    parser.add_argument(
        "--check",
        help="Executa apenas o check com o id informado.",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Apenas lista os checks registrados e sai.",
    )
    parser.add_argument(
        "--sem-cor",
        action="store_true",
        help="Desabilita cores ANSI na saida.",
    )
    args = parser.parse_args()

    usar_cor = (not args.sem_cor) and sys.stdout.isatty()
    qa = QAEngineer(projeto_root=str(RAIZ))

    if args.listar:
        imprimir_listagem(qa, args.escopo, usar_cor)
        return 0

    try:
        relatorio = qa.executar_checks(escopo=args.escopo, check_id=args.check)
    except KeyError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    imprimir_relatorio(relatorio, usar_cor)
    return 1 if relatorio["bloqueia_commit"] else 0


if __name__ == "__main__":
    sys.exit(main())
