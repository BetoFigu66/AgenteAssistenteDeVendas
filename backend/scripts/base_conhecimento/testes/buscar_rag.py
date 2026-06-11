"""
CLI simples para testar o `RetrievalService` a partir da linha de comando.

Uso:
    python -m scripts.buscar_rag "Qual relogio de ponto serve para restaurante com 25 funcionarios?"
    python -m scripts.buscar_rag "catraca com QR Code" --top-k 6 --tipo produto
    python -m scripts.buscar_rag "facial para cozinha" --tipos produto,faq --score-minimo 0.6
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

from services.rag import get_retrieval_service  # noqa: E402


async def _executar(args: argparse.Namespace) -> int:
    servico = get_retrieval_service()
    tipos = None
    if args.tipos:
        tipos = [t.strip() for t in args.tipos.split(",") if t.strip()]
    resultados = await servico.buscar(
        query=args.query,
        top_k=args.top_k,
        tipo=args.tipo if not tipos else None,
        tipos=tipos,
        score_minimo=args.score_minimo,
    )

    print(f"Encontrados: {len(resultados)}")
    for i, r in enumerate(resultados, start=1):
        print()
        print(f"[{i}] score={r.score:.4f} dist={r.distancia:.4f} tipo={r.tipo}")
        print(f"    titulo: {r.titulo}")
        print(f"    id_externo: {r.id_externo}")
        url = (r.metadados or {}).get("url")
        if url:
            print(f"    url: {url}")
        preview = r.conteudo.strip().replace("\n", " ")
        if len(preview) > 240:
            preview = preview[:240] + "..."
        print(f"    trecho: {preview}")

    if args.json:
        print()
        print(json.dumps([r.to_dict() for r in resultados], ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca semantica na RAG (teste manual).")
    parser.add_argument("query", help="Pergunta/texto a buscar")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument(
        "--tipo",
        default="produto",
        help="Filtra por um unico tipo. Use --tipo '' para nao filtrar.",
    )
    parser.add_argument(
        "--tipos",
        default=None,
        help="Lista de tipos separados por virgula (tem precedencia sobre --tipo).",
    )
    parser.add_argument("--score-minimo", type=float, default=None)
    parser.add_argument("--json", action="store_true", help="Imprime resultado em JSON.")
    args = parser.parse_args()

    if args.tipo == "":
        args.tipo = None

    return asyncio.run(_executar(args))


if __name__ == "__main__":
    raise SystemExit(main())
