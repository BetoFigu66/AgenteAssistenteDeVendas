"""
Deduplica e consolida documentos normalizados da RAG.

Entrada padrao:
    backend/data/rag/documentos_normalizados.jsonl

Saidas padrao:
    backend/data/rag/documentos_consolidados.jsonl
    backend/data/rag/consolidacao_resumo.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
ENTRADA_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "documentos_normalizados.jsonl"
SAIDA_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "documentos_consolidados.jsonl"
RESUMO_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "consolidacao_resumo.json"

TIPOS_COMPARAVEIS = {"produto", "categoria_produto", "indice_produto", "solucao"}
STOPWORDS = {
    "a",
    "as",
    "o",
    "os",
    "um",
    "uma",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "em",
    "para",
    "por",
    "com",
    "que",
    "se",
    "sua",
    "seu",
    "são",
    "sao",
    "mais",
    "como",
    "no",
    "na",
    "nos",
    "nas",
}


def carregar_jsonl(caminho: Path) -> list[dict[str, Any]]:
    documentos = []
    with caminho.open("r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if linha:
                documentos.append(json.loads(linha))
    return documentos


def salvar_jsonl(documentos: list[dict[str, Any]], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="\n") as arquivo:
        for documento in documentos:
            arquivo.write(json.dumps(documento, ensure_ascii=False) + "\n")


def salvar_json(dados: dict[str, Any], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalizar_tokens(texto: str) -> set[str]:
    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", texto.lower())
    return {token for token in tokens if token not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersecao = len(a & b)
    uniao = len(a | b)
    return intersecao / uniao if uniao else 0.0


def possui_faq(documento: dict[str, Any]) -> bool:
    conteudo = documento.get("conteudo", "").lower()
    return "perguntas frequentes" in conteudo or "faq" in conteudo


def score_precedencia(documento: dict[str, Any]) -> tuple[int, int, int, int, str]:
    metadata = documento.get("metadata", {})
    origem = metadata.get("origem")
    tipo = documento.get("tipo")
    conteudo = documento.get("conteudo", "")

    if origem == "webscraping" and tipo == "produto" and metadata.get("url"):
        base = 50
    elif origem == "folder_produto" and tipo == "produto":
        base = 40
    elif tipo == "categoria_produto":
        base = 25
    elif tipo == "indice_produto":
        base = 15
    elif tipo in {"solucao", "blog"}:
        base = 10
    else:
        base = 5

    return (
        base,
        1 if possui_faq(documento) else 0,
        1 if metadata.get("url") else 0,
        min(len(conteudo), 100_000),
        documento.get("id_documento", ""),
    )


def escolher_representante(documentos: list[dict[str, Any]]) -> dict[str, Any]:
    return max(documentos, key=score_precedencia)


def criar_grupos_exatos(documentos: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grupos = defaultdict(list)
    for documento in documentos:
        grupos[documento["conteudo_hash"]].append(documento)
    return {hash_: grupo for hash_, grupo in grupos.items() if len(grupo) > 1}


def remover_duplicatas_exatas(
    documentos: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    grupos = criar_grupos_exatos(documentos)
    representante_por_hash = {hash_: escolher_representante(grupo) for hash_, grupo in grupos.items()}
    removidos = []
    representantes = {}

    for hash_, representante in representante_por_hash.items():
        representantes[hash_] = representante["id_documento"]
        duplicatas = [
            {
                "id_documento": doc["id_documento"],
                "arquivo": doc.get("metadata", {}).get("arquivo"),
                "origem": doc.get("metadata", {}).get("origem"),
                "tipo": doc.get("tipo"),
                "titulo": doc.get("titulo"),
            }
            for doc in grupos[hash_]
            if doc["id_documento"] != representante["id_documento"]
        ]
        representante.setdefault("metadata", {}).setdefault("consolidacao", {})
        representante["metadata"]["consolidacao"].update(
            {
                "status": "representante_duplicata_exata",
                "grupo_duplicata_exata": hash_[:12],
                "duplicatas_exatas": duplicatas,
            }
        )
        removidos.extend(duplicatas)

    consolidados = []
    ids_removidos = {item["id_documento"] for item in removidos}
    for documento in documentos:
        if documento["id_documento"] in ids_removidos:
            continue
        documento.setdefault("metadata", {}).setdefault("consolidacao", {})
        documento["metadata"]["consolidacao"].setdefault("status", "unico")
        documento["metadata"]["consolidacao"].setdefault("precisa_revisao", False)
        consolidados.append(documento)

    return consolidados, removidos, representantes


def gerar_assinaturas(documentos: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        documento["id_documento"]: normalizar_tokens(
            f"{documento.get('titulo', '')}\n{documento.get('conteudo', '')}") for documento in documentos
    }


def candidato_similar(doc_a: dict[str, Any], doc_b: dict[str, Any]) -> bool:
    if doc_a["id_documento"] == doc_b["id_documento"]:
        return False
    if doc_a.get("tipo") not in TIPOS_COMPARAVEIS or doc_b.get("tipo") not in TIPOS_COMPARAVEIS:
        return False
    origem_a = doc_a.get("metadata", {}).get("origem")
    origem_b = doc_b.get("metadata", {}).get("origem")
    if origem_a == origem_b and doc_a.get("tipo") != doc_b.get("tipo"):
        return False
    return True


def detectar_similares(
    documentos: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
    assinaturas = gerar_assinaturas(documentos)
    similares = []

    for i, doc_a in enumerate(documentos):
        for doc_b in documentos[i + 1 :]:
            if not candidato_similar(doc_a, doc_b):
                continue
            score = jaccard(assinaturas[doc_a["id_documento"]], assinaturas[doc_b["id_documento"]])
            if score >= threshold:
                vencedor = escolher_representante([doc_a, doc_b])
                outro = doc_b if vencedor["id_documento"] == doc_a["id_documento"] else doc_a
                similares.append(
                    {
                        "score": round(score, 3),
                        "representante_sugerido": vencedor["id_documento"],
                        "outro_documento": outro["id_documento"],
                        "documentos": [
                            {
                                "id_documento": doc_a["id_documento"],
                                "titulo": doc_a.get("titulo"),
                                "tipo": doc_a.get("tipo"),
                                "origem": doc_a.get("metadata", {}).get("origem"),
                                "arquivo": doc_a.get("metadata", {}).get("arquivo"),
                            },
                            {
                                "id_documento": doc_b["id_documento"],
                                "titulo": doc_b.get("titulo"),
                                "tipo": doc_b.get("tipo"),
                                "origem": doc_b.get("metadata", {}).get("origem"),
                                "arquivo": doc_b.get("metadata", {}).get("arquivo"),
                            },
                        ],
                    }
                )

    return sorted(similares, key=lambda item: item["score"], reverse=True)


def marcar_similares(documentos: list[dict[str, Any]], similares: list[dict[str, Any]]) -> None:
    por_id = {doc["id_documento"]: doc for doc in documentos}
    for indice, grupo in enumerate(similares, start=1):
        grupo_id = f"similar-{indice:04d}"
        for item in grupo["documentos"]:
            documento = por_id[item["id_documento"]]
            consolidacao = documento.setdefault("metadata", {}).setdefault("consolidacao", {})
            consolidacao["status"] = (
                "representante_duplicata_exata"
                if consolidacao.get("status") == "representante_duplicata_exata"
                else "similar_precisa_revisao"
            )
            consolidacao["precisa_revisao"] = True
            consolidacao.setdefault("grupos_similares", []).append(
                {
                    "grupo_id": grupo_id,
                    "score": grupo["score"],
                    "representante_sugerido": grupo["representante_sugerido"],
                }
            )


ResultadoConsolidacao = tuple[list[dict[str, Any]], dict[str, Any]]

def consolidar(documentos: list[dict[str, Any]], similaridade_minima: float) -> ResultadoConsolidacao:
    consolidados, duplicatas_removidas, representantes_exatos = remover_duplicatas_exatas(documentos)
    similares = detectar_similares(consolidados, similaridade_minima)
    marcar_similares(consolidados, similares)

    por_tipo = Counter(doc["tipo"] for doc in consolidados)
    por_origem = Counter(doc["metadata"]["origem"] for doc in consolidados)
    por_status = Counter(doc["metadata"]["consolidacao"]["status"] for doc in consolidados)

    resumo = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "similaridade_minima": similaridade_minima,
        "total_entrada": len(documentos),
        "total_saida": len(consolidados),
        "duplicatas_exatas_removidas": len(duplicatas_removidas),
        "grupos_duplicata_exata": len(representantes_exatos),
        "pares_similares_para_revisao": len(similares),
        "por_tipo_documento": dict(sorted(por_tipo.items())),
        "por_origem": dict(sorted(por_origem.items())),
        "por_status_consolidacao": dict(sorted(por_status.items())),
        "duplicatas_exatas": duplicatas_removidas,
        "similares_para_revisao": similares,
    }
    return consolidados, resumo


def caminho_absoluto_ou_raiz(caminho: Path) -> Path:
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplica e consolida documentos da RAG.")
    parser.add_argument("--entrada", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--resumo", type=Path, default=RESUMO_PADRAO)
    parser.add_argument(
        "--similaridade-minima",
        type=float,
        default=0.82,
        help="Score Jaccard minimo para marcar documentos como similares.",
    )
    args = parser.parse_args()

    entrada = caminho_absoluto_ou_raiz(args.entrada)
    saida = caminho_absoluto_ou_raiz(args.saida)
    resumo_saida = caminho_absoluto_ou_raiz(args.resumo)

    if not 0 < args.similaridade_minima <= 1:
        raise SystemExit("--similaridade-minima deve estar entre 0 e 1.")

    documentos = carregar_jsonl(entrada)
    consolidados, resumo = consolidar(documentos, args.similaridade_minima)
    salvar_jsonl(consolidados, saida)
    salvar_json(resumo, resumo_saida)

    print(f"Documentos consolidados: {saida}")
    print(f"Resumo: {resumo_saida}")
    print(f"Total entrada: {resumo['total_entrada']}")
    print(f"Total saida: {resumo['total_saida']}")
    print(f"Duplicatas exatas removidas: {resumo['duplicatas_exatas_removidas']}")
    print(f"Pares similares para revisao: {resumo['pares_similares_para_revisao']}")
    print(f"Por status: {resumo['por_status_consolidacao']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
