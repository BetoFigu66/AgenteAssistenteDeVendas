#!/usr/bin/env python3
"""
Verifica se há atividades periódicas do projeto em atraso.

Uso:
    python scripts/verificar_atividades.py                          # aviso, sempre exit 0
    python scripts/verificar_atividades.py --strict                 # exit 1 se houver atraso
    python scripts/verificar_atividades.py --registrar <id>         # registra execução
    python scripts/verificar_atividades.py --registrar <id> \\
        --responsavel "Beto" --notas "tudo ok"

Arquivos:
    artefatos/gerente_de_projetos/atividades_periodicas.yaml  — configuração das atividades
    artefatos/gerente_de_projetos/log_atividades.yaml          — histórico de execuções
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

PROJETO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJETO_ROOT / "artefatos" / "gerente_de_projetos" / "atividades_periodicas.yaml"
LOG_PATH = PROJETO_ROOT / "artefatos" / "gerente_de_projetos" / "log_atividades.yaml"


def carregar_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar_log():
    if not LOG_PATH.exists():
        return {"registros": []}
    with open(LOG_PATH, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    return dados if dados else {"registros": []}


def salvar_log(log):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(log, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _parse_date(valor) -> date | None:
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor)
        except ValueError:
            return None
    return None


def ultimo_registro(log, atividade_id) -> date | None:
    """Retorna a data do último registro de uma atividade, ou None."""
    datas = [
        _parse_date(r.get("data")) for r in (log.get("registros") or []) if r.get("id") == atividade_id and _parse_date(r.get("data")) is not None
    ]
    return max(datas) if datas else None


def verificar_atrasos(config, log, hoje: date | None = None) -> list[dict]:
    """
    Retorna atividades em atraso ordenadas por dias_atraso decrescente.
    """
    hoje = hoje or date.today()

    frequencias: dict[str, int] = config.get("frequencias", {"semanal": 7, "sprint": 14, "mensal": 30})

    atrasos = []
    for ativ in config.get("atividades", []):
        aid = ativ["id"]
        freq_nome = ativ.get("frequencia", "mensal")
        freq_dias = frequencias.get(freq_nome, 30)

        ultimo = ultimo_registro(log, aid)
        if ultimo is None:
            prazo = hoje - timedelta(days=1)
            dias_atraso = freq_dias
        else:
            prazo = ultimo + timedelta(days=freq_dias)
            dias_atraso = (hoje - prazo).days

        if dias_atraso > 0:
            atrasos.append(
                {
                    "id": aid,
                    "descricao": ativ.get("descricao", aid),
                    "frequencia": freq_nome,
                    "freq_dias": freq_dias,
                    "ultimo_registro": ultimo.isoformat() if ultimo else "nunca",
                    "prazo": prazo.isoformat(),
                    "dias_atraso": dias_atraso,
                    "tipo": ativ.get("tipo", ""),
                    "comando": ativ.get("comando", ""),
                    "agente": ativ.get("agente", ""),
                    "prompt": ativ.get("prompt", "").strip(),
                    "arquivos": ativ.get("arquivos", []),
                }
            )

    return sorted(atrasos, key=lambda x: -x["dias_atraso"])


def formatar_saida(atrasos: list[dict]) -> str:
    if not atrasos:
        return "✅  Nenhuma atividade periódica em atraso.\n"

    linhas = [f"⚠️   {len(atrasos)} atividade(s) periódica(s) em atraso:\n"]
    for a in atrasos:
        linhas.append(f"  🔴 [{a['id']}]")
        linhas.append(f"     {a['descricao']}")
        linhas.append(
            f"     Frequência: {a['frequencia']} ({a['freq_dias']}d)  |  "
            f"Último registro: {a['ultimo_registro']}  |  "
            f"Prazo era: {a['prazo']}  |  Atraso: {a['dias_atraso']}d"
        )
        if a["tipo"] == "script" and a["comando"]:
            linhas.append(f"     ▶ Executar: {a['comando']}")
        elif a["tipo"] == "prompt_agente" and a["agente"]:
            linhas.append(f"     ▶ No chat: [{a['agente']}] {a['prompt']}")
        elif a["tipo"] == "revisao_manual" and a["arquivos"]:
            linhas.append(f"     ▶ Revisar manualmente: {', '.join(a['arquivos'])}")
        linhas.append("")

    linhas.append(
        'Para registrar uma execução após concluir:\n  python scripts/verificar_atividades.py --registrar <id> [--responsavel <nome>] [--notas "..."]'
    )
    return "\n".join(linhas)


def registrar_execucao(log: dict, atividade_id: str, responsavel: str, notas: str):
    registros = log.setdefault("registros", [])
    entrada = {
        "id": atividade_id,
        "data": date.today().isoformat(),
        "responsavel": responsavel,
        "notas": notas,
    }
    registros.append(entrada)
    salvar_log(log)
    print(f"✅  Execução registrada: {atividade_id} em {entrada['data']}")


def main():
    parser = argparse.ArgumentParser(
        description="Verifica atividades periódicas do projeto em atraso.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Retorna exit code 1 se houver atividades em atraso (para pre-commit com falha).",
    )
    parser.add_argument(
        "--registrar",
        metavar="ID",
        help="Registra a execução de uma atividade pelo seu ID.",
    )
    parser.add_argument(
        "--responsavel",
        default="",
        metavar="NOME",
        help="Nome do responsável (usado com --registrar).",
    )
    parser.add_argument(
        "--notas",
        default="",
        metavar="TEXTO",
        help="Notas sobre a execução (usado com --registrar).",
    )
    args = parser.parse_args()

    config = carregar_config()
    log = carregar_log()

    if args.registrar:
        ids_validos = {a["id"] for a in config.get("atividades", [])}
        if args.registrar not in ids_validos:
            print(f"❌  ID '{args.registrar}' não encontrado.\nIDs válidos: {', '.join(sorted(ids_validos))}")
            sys.exit(1)
        registrar_execucao(log, args.registrar, args.responsavel, args.notas)
        return

    atrasos = verificar_atrasos(config, log)
    print(formatar_saida(atrasos))

    if args.strict and atrasos:
        sys.exit(1)


if __name__ == "__main__":
    main()
