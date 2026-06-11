"""Gera grafico de barras horizontais empilhadas da cobertura ponderada por REQ.

Para cada REQ, cada barra tem altura = peso_reqs[req] (% do projeto). A barra e
dividida em duas partes:
  - azul: peso_reqs[req] * por_req[req] / 100  (cobertura realizada)
  - vermelho: peso_reqs[req] - realizado       (cobertura faltante)

A soma das barras = 100% do projeto. Util para visualizar onde esta o esforco
concentrado e quanto falta ponderadamente.

Fonte dos dados:
  - peso_reqs: artefatos/gerente_de_projetos/cobertura_evolucao.yaml (campo de topo)
  - por_req: ultima sprint listada em sprints[]

Uso:
  python gera_grafico_cobertura_ponderada.py [-o saida.png]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("[ERRO] matplotlib nao instalado. Rode: pip install matplotlib", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[3]
EVOLUCAO_PATH = ROOT / "artefatos" / "gerente_de_projetos" / "cobertura_evolucao.yaml"
SAIDA_DIR = ROOT / "artefatos" / "gerente_de_projetos" / "reports"


def _saida_para_sprint(numero: int | str) -> Path:
    return SAIDA_DIR / f"grafico_cobertura_ponderada_sprint{numero}.png"


def parse_pct(valor) -> float:
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = re.sub(r"[~%\s]", "", str(valor))
    try:
        return float(s)
    except ValueError:
        return 0.0


def gerar_grafico(saida: Path, sprint_numero: int | None = None) -> None:
    with EVOLUCAO_PATH.open("r", encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}

    peso_reqs = dados.get("peso_reqs") or {}
    sprints = dados.get("sprints") or []
    if not peso_reqs:
        raise ValueError(f"peso_reqs ausente em {EVOLUCAO_PATH.name}")
    if not sprints:
        raise ValueError(f"sprints vazias em {EVOLUCAO_PATH.name}")

    if sprint_numero is None:
        alvo = sprints[-1]
    else:
        alvo = next((s for s in sprints if s.get("numero") == sprint_numero), None)
        if alvo is None:
            raise ValueError(f"Sprint {sprint_numero} nao encontrada em {EVOLUCAO_PATH.name}")
    por_req = alvo.get("por_req") or {}
    numero_sprint = alvo.get("numero", "?")

    # Sprint anterior (mesma sequencia numerica) para a porcao "ja concluida antes".
    anteriores = [s for s in sprints if isinstance(s.get("numero"), int) and s["numero"] < (numero_sprint or 0)]
    anterior = max(anteriores, key=lambda s: s["numero"]) if anteriores else None
    por_req_anterior = (anterior.get("por_req") if anterior else {}) or {}

    reqs = [r for r in peso_reqs.keys() if isinstance(peso_reqs.get(r), (int, float))]
    pesos = [float(peso_reqs[r]) for r in reqs]
    pcts = [parse_pct(por_req.get(r, 0)) for r in reqs]
    pcts_ant = [parse_pct(por_req_anterior.get(r, 0)) for r in reqs]
    # Se a sprint atual recuou em algum REQ (incomum), trata como 0 delta para nao ter barra negativa.
    pcts_ant = [min(a, c) for a, c in zip(pcts_ant, pcts)]
    anteriores_w = [p * a / 100.0 for p, a in zip(pesos, pcts_ant)]
    delta_w = [p * (c - a) / 100.0 for p, c, a in zip(pesos, pcts, pcts_ant)]
    realizados = [aw + dw for aw, dw in zip(anteriores_w, delta_w)]
    faltantes = [p - r for p, r in zip(pesos, realizados)]

    total_real = sum(realizados)
    total_ant = sum(anteriores_w)
    total_pond = sum(pesos)

    # Ordem visual: REQ-001 no topo
    reqs_inv = list(reversed(reqs))
    anteriores_inv = list(reversed(anteriores_w))
    delta_inv = list(reversed(delta_w))
    faltantes_inv = list(reversed(faltantes))
    pcts_inv = list(reversed(pcts))
    pcts_ant_inv = list(reversed(pcts_ant))
    pesos_inv = list(reversed(pesos))

    fig, ax = plt.subplots(figsize=(10, 6))
    label_anterior = f"Concluido ate Sprint {anterior['numero']}" if anterior else "Concluido em sprints anteriores"
    ax.barh(reqs_inv, anteriores_inv, color="#2ca02c", label=f"{label_anterior} (ponderado)")
    ax.barh(
        reqs_inv, delta_inv, left=anteriores_inv,
        color="#1f77b4", label=f"Avanco na Sprint {numero_sprint} (ponderado)"
    )
    starts_red = [a + d for a, d in zip(anteriores_inv, delta_inv)]
    ax.barh(reqs_inv, faltantes_inv, left=starts_red, color="#d62728", label="Faltante (ponderado)")

    # Rotulos: peso + % anterior -> % atual (delta)
    for i, (peso, pct, pct_ant) in enumerate(zip(pesos_inv, pcts_inv, pcts_ant_inv)):
        ax.text(peso + 0.2, i,
                f"{peso:.0f}% peso | {pct_ant:.0f}% -> {pct:.0f}% cob.",
                va="center", fontsize=8, color="#333")

    ax.set_xlabel("Peso no projeto (%)")
    titulo = (
        f"Cobertura ponderada por REQ - Sprint {numero_sprint}\n"
        f"Total realizado: {total_real:.1f}% de {total_pond:.0f}% (projeto)"
    )
    if anterior:
        titulo += f"   |   anterior: {total_ant:.1f}%   delta: +{(total_real - total_ant):.1f} pp"
    ax.set_title(titulo)
    ax.legend(loc="lower right")
    ax.set_xlim(0, max(pesos) * 1.55)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(saida, dpi=150)
    plt.close(fig)
    print(f"OK - grafico gerado em {saida}")


def _ultima_sprint_numero() -> int:
    with EVOLUCAO_PATH.open("r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    sprints = d.get("sprints") or []
    if not sprints:
        raise ValueError(f"sprints vazias em {EVOLUCAO_PATH.name}")
    return int(sprints[-1].get("numero"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--saida", type=Path, default=None,
                        help="caminho de saida (padrao: reports/grafico_cobertura_ponderada_sprint{N}.png)")
    parser.add_argument("--sprint", type=int, default=None,
                        help="numero da sprint a usar (padrao: ultima)")
    args = parser.parse_args()
    numero = args.sprint if args.sprint is not None else _ultima_sprint_numero()
    saida = args.saida or _saida_para_sprint(numero)
    gerar_grafico(saida, sprint_numero=numero)
    return 0


if __name__ == "__main__":
    sys.exit(main())
