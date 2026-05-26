"""Regenera artefatos/gerente_de_projetos/cobertura_evolucao.yaml.

Lê todos os arquivos sprint_NN_*_interno.yaml em
artefatos/gerente_de_projetos/reports/ e reconstrói o histórico
longitudinal de cobertura dos REQs a partir do bloco
`cobertura_sprint.por_req` de cada report.

Uso:
    python agentes/scripts/gerente_de_projetos/atualiza_cobertura_evolucao.py

Comportamento:
- Para cada sprint com yaml de report, extrai cobertura_sprint.por_req
  como snapshot oficial do fim daquela sprint (origem: snapshot_formal).
- REQs que não avançaram naquela sprint herdam o valor da sprint anterior.
- Sprints sem yaml de report (ex: Sprint 1 reconstruída retroativamente)
  são preservadas se já existem no cobertura_evolucao.yaml atual com
  origem: reconstrucao_retroativa.
- Recalcula media_projeto e o bloco resumo.
- Idempotente: rodar duas vezes sem mudanças no input não altera o output.

Diretriz relacionada: G06 (artefatos/gerente_de_projetos/diretrizes.md).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "artefatos" / "gerente_de_projetos" / "reports"
EVOLUCAO_PATH = PROJECT_ROOT / "artefatos" / "gerente_de_projetos" / "cobertura_evolucao.yaml"

CABECALHO = """\
# Histórico longitudinal de cobertura dos REQs por sprint.
#
# OBJETIVO: fonte única para visualização da evolução do projeto sprint a sprint.
# Cada entrada `sprints[i]` é um snapshot ao final daquela sprint.
#
# CAMPOS DE TOPO:
#   - peso_reqs: tamanho relativo de cada REQ no projeto (em %, soma=100).
#       Estimativa subjetiva baseada em escopo técnico (complexidade,
#       integrações, UI, NFRs). NÃO é contagem de subitens. Mantido
#       manualmente no YAML — script preserva e reordena, mas não recalcula.
#       Útil para projeção ponderada:
#         cobertura_ponderada = sum(peso_reqs[req] * por_req[req]) / 100
#       Revisar a cada replanejamento de escopo significativo.
#
# CAMPOS DE SPRINT:
#   - numero: número da sprint
#   - data_fim: data de fechamento (YYYY-MM-DD)
#   - origem: como o snapshot foi obtido
#       * "snapshot_formal" = veio do cobertura_sprint.por_req do yaml do report
#       * "reconstrucao_retroativa" = estimado a posteriori (menos confiável)
#   - media_projeto: média simples dos % dos REQs acompanhados na sprint
#   - por_req: mapa REQ → % estimado ao final da sprint
#
# METODOLOGIA: percentuais derivados da contagem ponderada de subitens
# (✅=1.0, 🟡=0.5, 🔴=0.0) — ver cobertura_reqs_sprint02.md §1.1 para detalhes
# e limitações. Tratar números como ordem de grandeza, não métrica precisa.
#
# COMO ATUALIZAR: NÃO editar manualmente sprints com origem snapshot_formal.
# Em vez disso, rodar:
#     python agentes/scripts/gerente_de_projetos/atualiza_cobertura_evolucao.py
# que regera este arquivo a partir dos sprint_NN_*_interno.yaml em reports/.
# Diretriz aplicável: G06 (artefatos/gerente_de_projetos/diretrizes.md).
#
# ARQUIVO GERADO POR SCRIPT — edições manuais em sprints snapshot_formal serão sobrescritas.

"""

REGEX_SPRINT_FILE = re.compile(r"^sprint_(\d{2})_\d{8}_interno\.yaml$")


def parse_pct(valor: Any) -> float:
    """Converte '~25%' / '25%' / '0%' / 25 em float (pontos percentuais)."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace("~", "").replace("%", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def fmt_pct(valor: float) -> str:
    """Formata float em pontos percentuais como '~XX%' (ou '0%' quando 0)."""
    if valor <= 0.0:
        return "0%"
    return f"~{int(round(valor))}%"


def fmt_delta(valor: float) -> str:
    sinal = "+" if valor >= 0 else ""
    return f"{sinal}{int(round(valor))}"


def calcular_cobertura_ponderada(por_req: dict, peso_reqs: dict) -> float:
    """Calcula cobertura ponderada pelo tamanho relativo de cada REQ.

    Formula: sum(peso_reqs[req] * parse_pct(por_req[req])) / 100
    Se peso_reqs nao existir, retorna 0.0 (fallback).
    """
    if not peso_reqs:
        return 0.0
    total = 0.0
    peso_usado = 0.0
    for req, peso in peso_reqs.items():
        if not isinstance(peso, (int, float)):
            continue
        pct = parse_pct(por_req.get(req, "0%"))
        total += peso * pct
        peso_usado += peso
    if peso_usado <= 0:
        return 0.0
    return total / 100.0


def carregar_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def listar_reports_internos() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    arquivos = []
    for p in REPORTS_DIR.iterdir():
        if not p.is_file():
            continue
        if REGEX_SPRINT_FILE.match(p.name):
            arquivos.append(p)
    arquivos.sort(key=lambda p: p.name)
    return arquivos


def numero_da_sprint(path: Path) -> int:
    m = REGEX_SPRINT_FILE.match(path.name)
    assert m is not None
    return int(m.group(1))


def coletar_reqs_acompanhados(reports: list[Path], evolucao_atual: dict) -> list[str]:
    """Une todos os REQs vistos em qualquer sprint, mantendo ordem REQ-001, REQ-002, ..."""
    reqs: set[str] = set()
    for entry in evolucao_atual.get("sprints", []) or []:
        reqs.update((entry.get("por_req") or {}).keys())
    for path in reports:
        data = carregar_yaml(path)
        por_req = (data.get("cobertura_sprint") or {}).get("por_req") or {}
        reqs.update(por_req.keys())
    return sorted(reqs, key=lambda s: (s[:4], int(s.split("-")[-1]) if s.split("-")[-1].isdigit() else 0))


def construir_sprint_snapshot(
    numero: int,
    data_fim: str,
    por_req_avancado: dict,
    sprint_anterior_por_req: dict,
    reqs_acompanhados: list[str],
    peso_reqs: dict,
) -> dict:
    """Constrói o snapshot completo de uma sprint herdando valores não-avançados da anterior."""
    por_req: dict[str, str] = {}
    for req in reqs_acompanhados:
        if req in por_req_avancado:
            por_req[req] = str(por_req_avancado[req].get("depois", "0%"))
        elif req in sprint_anterior_por_req:
            por_req[req] = str(sprint_anterior_por_req[req])
        else:
            por_req[req] = "0%"

    valores = [parse_pct(v) for v in por_req.values()]
    media = sum(valores) / len(valores) if valores else 0.0
    ponderada = calcular_cobertura_ponderada(por_req, peso_reqs)

    return {
        "numero": numero,
        "data_fim": data_fim,
        "origem": "snapshot_formal",
        "media_projeto": fmt_pct(media),
        "cobertura_ponderada": fmt_pct(ponderada),
        "por_req": por_req,
    }


def construir_resumo(sprints: list[dict], peso_reqs: dict) -> dict:
    deltas: dict[str, str] = {}
    deltas_ponderados: dict[str, str] = {}
    por_req_anterior: dict[str, float] = {}
    ponderada_anterior: float = 0.0

    for sprint in sprints:
        n = sprint["numero"]
        chave = f"sprint_{n}"
        media_atual = parse_pct(sprint.get("media_projeto"))
        ponderada_atual = parse_pct(sprint.get("cobertura_ponderada", "0%"))

        if not por_req_anterior:
            deltas[chave] = "n/a (sem baseline anterior formalizada)"
            deltas_ponderados[chave] = "n/a"
        else:
            media_anterior = sum(por_req_anterior.values()) / len(por_req_anterior)
            delta_pp = media_atual - media_anterior
            deltas[chave] = (
                f"{fmt_delta(delta_pp)} pp "
                f"({fmt_pct(media_anterior)} → {fmt_pct(media_atual)})"
            )
            delta_pond = ponderada_atual - ponderada_anterior
            deltas_ponderados[chave] = (
                f"{fmt_delta(delta_pond)} pp "
                f"({fmt_pct(ponderada_anterior)} → {fmt_pct(ponderada_atual)})"
            )

        por_req_anterior = {k: parse_pct(v) for k, v in (sprint.get("por_req") or {}).items()}
        ponderada_anterior = ponderada_atual

    if sprints:
        ultimo = sprints[-1].get("por_req") or {}
        valores = [parse_pct(v) for v in ultimo.values()]
        acima_50 = [k for k, v in ultimo.items() if parse_pct(v) >= 50]
        entre_25_49 = [k for k, v in ultimo.items() if 25 <= parse_pct(v) < 50]
        abaixo_25 = [k for k, v in ultimo.items() if parse_pct(v) < 25]
        concluidos = [k for k, v in ultimo.items() if parse_pct(v) >= 100]
    else:
        acima_50 = entre_25_49 = abaixo_25 = concluidos = []

    return {
        "delta_por_sprint": deltas,
        "delta_ponderado_por_sprint": deltas_ponderados,
        "reqs_concluidos": len(concluidos),
        "reqs_acima_50pct": len(acima_50),
        "reqs_25_a_49pct": len(entre_25_49),
        "reqs_abaixo_25pct": len(abaixo_25),
    }


def regenerar() -> dict:
    evolucao_atual = carregar_yaml(EVOLUCAO_PATH)
    reports = listar_reports_internos()

    if not reports:
        print(f"[AVISO] Nenhum report encontrado em {REPORTS_DIR}", file=sys.stderr)

    sprints_existentes_por_numero = {
        s["numero"]: s for s in (evolucao_atual.get("sprints") or [])
    }

    reqs_acompanhados = coletar_reqs_acompanhados(reports, evolucao_atual)

    # Preserva peso_reqs do arquivo existente (estimativa manual, nao recalcula).
    peso_reqs = dict(evolucao_atual.get("peso_reqs") or {})

    sprints_finais: list[dict] = []

    # 1. Preservar sprints retroativas que não tem yaml de report
    numeros_com_report = {numero_da_sprint(p) for p in reports}
    for numero, snapshot in sorted(sprints_existentes_por_numero.items()):
        if numero in numeros_com_report:
            continue
        if snapshot.get("origem") == "reconstrucao_retroativa":
            # completa com REQs novos como 0% se aparecerem depois
            por_req = dict(snapshot.get("por_req") or {})
            for req in reqs_acompanhados:
                por_req.setdefault(req, "0%")
            snapshot = dict(snapshot)
            snapshot["por_req"] = {r: por_req[r] for r in reqs_acompanhados}
            # Recalcula cobertura ponderada caso peso_reqs tenha sido adicionado
            # apos a construcao original da sprint retroativa.
            if "cobertura_ponderada" not in snapshot:
                cp = calcular_cobertura_ponderada(por_req, peso_reqs)
                snapshot["cobertura_ponderada"] = fmt_pct(cp)
            sprints_finais.append(snapshot)
        else:
            print(
                f"[AVISO] Sprint {numero} no arquivo atual sem yaml de report e "
                f"origem != reconstrucao_retroativa. Será descartada.",
                file=sys.stderr,
            )

    # 2. Reconstruir sprints com report formal
    sprints_finais.sort(key=lambda s: s["numero"])
    por_req_anterior = sprints_finais[-1]["por_req"] if sprints_finais else {}

    for path in reports:
        data = carregar_yaml(path)
        numero = numero_da_sprint(path)
        data_fim = str(data.get("data_fim") or "")
        cobertura_sprint = data.get("cobertura_sprint") or {}
        por_req_avancado = cobertura_sprint.get("por_req") or {}

        if not por_req_avancado:
            print(
                f"[AVISO] {path.name} não tem cobertura_sprint.por_req — "
                f"sprint {numero} herdará tudo da anterior.",
                file=sys.stderr,
            )

        snapshot = construir_sprint_snapshot(
            numero=numero,
            data_fim=data_fim,
            por_req_avancado=por_req_avancado,
            sprint_anterior_por_req=por_req_anterior,
            reqs_acompanhados=reqs_acompanhados,
            peso_reqs=peso_reqs,
        )
        sprints_finais.append(snapshot)
        por_req_anterior = snapshot["por_req"]

    sprints_finais.sort(key=lambda s: s["numero"])

    resumo = construir_resumo(sprints_finais, peso_reqs)
    if sprints_finais:
        proxima = max(s["numero"] for s in sprints_finais) + 1
        resumo["proxima_revisao"] = f"fim Sprint {proxima}"

    ultima_atualizacao = sprints_finais[-1]["data_fim"] if sprints_finais else ""

    # Preserva peso_reqs (tamanho relativo de cada REQ no projeto, em %)
    # do arquivo existente. Valor e estimativa subjetiva mantida manualmente
    # — script nao recalcula, apenas reordena para coincidir com a ordem de
    # reqs_acompanhados e avisa se a soma divergir de 100%.
    peso_reqs_atual = evolucao_atual.get("peso_reqs") or {}
    peso_reqs_ordenado: dict = {}
    for req in reqs_acompanhados:
        if req in peso_reqs_atual:
            peso_reqs_ordenado[req] = peso_reqs_atual[req]
    # REQs sem peso definido — manter chave com placeholder None para visibilidade.
    for req in reqs_acompanhados:
        if req not in peso_reqs_ordenado:
            peso_reqs_ordenado[req] = None

    if peso_reqs_atual:
        soma = sum(v for v in peso_reqs_ordenado.values() if isinstance(v, (int, float)))
        if abs(soma - 100) > 1:
            print(
                f"[AVISO] peso_reqs soma {soma}% (esperado ~100%). "
                f"Ajuste em {EVOLUCAO_PATH.name}.",
                file=sys.stderr,
            )

    resultado: dict = {
        "projeto": evolucao_atual.get("projeto", "Assistente de Vendas via WhatsApp com IA"),
        "total_reqs_acompanhados": len(reqs_acompanhados),
    }
    if peso_reqs_atual:
        resultado["peso_reqs"] = peso_reqs_ordenado
    resultado["ultima_atualizacao"] = ultima_atualizacao
    resultado["sprints"] = sprints_finais
    resultado["resumo"] = resumo
    return resultado


def serializar(dados: dict) -> str:
    """Gera a string final do arquivo (cabeçalho + YAML)."""
    corpo = yaml.safe_dump(
        dados,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return CABECALHO + corpo


def gerar_conteudo_esperado() -> str:
    """API pública para o check de QA: retorna o conteúdo que o arquivo deveria ter."""
    return serializar(regenerar())


def ler_conteudo_atual() -> str:
    if not EVOLUCAO_PATH.exists():
        return ""
    return EVOLUCAO_PATH.read_text(encoding="utf-8")


def gravar(dados: dict) -> None:
    EVOLUCAO_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVOLUCAO_PATH.write_text(serializar(dados), encoding="utf-8")


def main() -> int:
    dados = regenerar()
    gravar(dados)
    n_sprints = len(dados["sprints"])
    print(f"OK — {EVOLUCAO_PATH.relative_to(PROJECT_ROOT)} regenerado com {n_sprints} sprint(s).")
    for s in dados["sprints"]:
        print(f"  Sprint {s['numero']:>2} ({s['origem']:<24}) — média {s['media_projeto']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
