"""
CLI simples para testar o `QAService` a partir da linha de comando.

Uso:
    python -m scripts.buscar_qa "Qual relogio de ponto serve para restaurante?"
    python -m scripts.buscar_qa "catraca com biometria" --contexto catraca
    python -m scripts.buscar_qa "controle de ponto" --score-minimo 0.7 --top-k 5
    python -m scripts.buscar_qa "leitor facial" --nao-apenas-aprovados --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.rag import get_qa_service  # noqa: E402


async def _executar(args: argparse.Namespace) -> int:
    servico = get_qa_service()
    resultados = await servico.buscar(
        query=args.query,
        contexto=args.contexto,
        top_k=args.top_k,
        score_minimo=args.score_minimo,
        apenas_aprovados=not args.nao_apenas_aprovados,
    )

    print(f"Query   : {args.query!r}")
    print(
        f"Filtros : contexto={args.contexto!r}  score_min={args.score_minimo}  apenas_aprovados={not args.nao_apenas_aprovados}  top_k={args.top_k}"
    )
    print(f"Encontrados: {len(resultados)}")

    for i, r in enumerate(resultados, start=1):
        print()
        print(f"[{i}] score={r.score:.4f}  dist={r.distancia:.4f}  contexto={r.contexto}")
        print(f"    id_externo : {r.id_externo}")
        print(f"    pergunta   : {r.pergunta}")
        preview = r.resposta.strip().replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        print(f"    resposta   : {preview}")
        if r.tags:
            print(f"    tags       : {r.tags}")

    if args.json:
        print()
        print(json.dumps([r.to_dict() for r in resultados], ensure_ascii=False, indent=2))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca semantica na base Q&A (teste manual).")
    parser.add_argument("query", help="Pergunta/texto a buscar")
    parser.add_argument(
        "--contexto",
        default=None,
        help="Filtra por contexto (ex: catraca, relogio_ponto, facial, geral).",
    )
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--score-minimo", type=float, default=None)
    parser.add_argument(
        "--nao-apenas-aprovados",
        action="store_true",
        help="Inclui pares nao aprovados na busca.",
    )
    parser.add_argument("--json", action="store_true", help="Imprime resultado completo em JSON.")
    args = parser.parse_args()
    return asyncio.run(_executar(args))


if __name__ == "__main__":
    raise SystemExit(main())
