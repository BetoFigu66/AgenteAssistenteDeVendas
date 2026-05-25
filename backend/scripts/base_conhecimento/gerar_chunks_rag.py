"""
Gera chunks dos documentos consolidados da RAG.

Entrada padrao:
    backend/data/rag/documentos_consolidados.jsonl

Saidas padrao:
    backend/data/rag/chunks_conhecimento.jsonl
    backend/data/rag/chunking_resumo.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
ENTRADA_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "documentos_consolidados.jsonl"
SAIDA_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "chunks_conhecimento.jsonl"
RESUMO_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "chunking_resumo.json"

TOKENS_RE = re.compile(r"\S+")
FAQ_TITULO_RE = re.compile(r"^\s*(perguntas frequentes|faq)\s*$", re.IGNORECASE)


def carregar_jsonl(caminho: Path) -> list[dict[str, Any]]:
    documentos = []
    with caminho.open("r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if linha:
                documentos.append(json.loads(linha))
    return documentos


def salvar_jsonl(registros: list[dict[str, Any]], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="\n") as arquivo:
        for registro in registros:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def salvar_json(dados: dict[str, Any], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def contar_tokens(texto: str) -> int:
    return len(TOKENS_RE.findall(texto))


def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def normalizar_bloco(texto: str) -> str:
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def separar_linhas(texto: str) -> list[str]:
    return [linha.strip() for linha in texto.splitlines()]


def separar_secao_faq(conteudo: str) -> tuple[str, str]:
    linhas = separar_linhas(conteudo)
    for indice, linha in enumerate(linhas):
        if FAQ_TITULO_RE.match(linha):
            antes = "\n".join(linhas[:indice])
            faq = "\n".join(linhas[indice + 1 :])
            return normalizar_bloco(antes), normalizar_bloco(faq)
    return conteudo, ""


def extrair_faq_chunks(secao_faq: str) -> list[str]:
    if not secao_faq:
        return []

    linhas = [linha for linha in separar_linhas(secao_faq) if linha]
    chunks = []
    pergunta_atual: str | None = None
    resposta_atual: list[str] = []

    def fechar_atual() -> None:
        nonlocal pergunta_atual, resposta_atual
        if not pergunta_atual:
            return
        partes = [pergunta_atual, *resposta_atual]
        texto = normalizar_bloco("\n".join(partes))
        if texto:
            chunks.append(texto)
        pergunta_atual = None
        resposta_atual = []

    for linha in linhas:
        if linha.endswith("?"):
            fechar_atual()
            pergunta_atual = linha
            resposta_atual = []
        elif pergunta_atual:
            resposta_atual.append(linha)

    fechar_atual()
    return chunks


def split_texto_longo(texto: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    tokens = TOKENS_RE.findall(texto)
    if len(tokens) <= max_tokens:
        return [texto]

    chunks = []
    inicio = 0
    passo = max(1, max_tokens - overlap_tokens)
    while inicio < len(tokens):
        fim = min(len(tokens), inicio + max_tokens)
        chunks.append(" ".join(tokens[inicio:fim]))
        if fim == len(tokens):
            break
        inicio += passo
    return chunks


def chunk_por_paragrafos(
    texto: str,
    alvo_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    texto = normalizar_bloco(texto)
    if not texto:
        return []

    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    if not paragrafos:
        return []

    chunks = []
    atual: list[str] = []
    atual_tokens = 0

    def adicionar_chunk(partes: list[str]) -> None:
        bloco = normalizar_bloco("\n\n".join(partes))
        if not bloco:
            return
        chunks.extend(split_texto_longo(bloco, max_tokens, overlap_tokens))

    for paragrafo in paragrafos:
        qtd_tokens = contar_tokens(paragrafo)
        if atual and atual_tokens + qtd_tokens > max_tokens:
            adicionar_chunk(atual)
            overlap_partes = []
            overlap_total = 0
            for parte in reversed(atual):
                tokens_parte = contar_tokens(parte)
                if overlap_total + tokens_parte > overlap_tokens and overlap_partes:
                    break
                overlap_partes.insert(0, parte)
                overlap_total += tokens_parte
            atual = overlap_partes
            atual_tokens = overlap_total

        atual.append(paragrafo)
        atual_tokens += qtd_tokens

        if atual_tokens >= alvo_tokens:
            adicionar_chunk(atual)
            atual = []
            atual_tokens = 0

    if atual:
        adicionar_chunk(atual)

    return chunks


def gerar_chunks_documento(
    documento: dict[str, Any],
    alvo_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[dict[str, Any]]:
    conteudo = documento.get("conteudo", "")
    antes_faq, secao_faq = separar_secao_faq(conteudo)

    blocos: list[tuple[str, str]] = []
    for chunk in chunk_por_paragrafos(antes_faq, alvo_tokens, max_tokens, overlap_tokens):
        blocos.append(("conteudo", chunk))

    for faq_chunk in extrair_faq_chunks(secao_faq):
        for chunk in split_texto_longo(faq_chunk, max_tokens, overlap_tokens):
            blocos.append(("faq", chunk))

    if not blocos and conteudo.strip():
        for chunk in split_texto_longo(normalizar_bloco(conteudo), max_tokens, overlap_tokens):
            blocos.append(("conteudo", chunk))

    total = len(blocos)
    chunks = []
    for indice, (tipo_chunk, texto) in enumerate(blocos, start=1):
        texto = normalizar_bloco(texto)
        chunk_hash = hash_texto(texto)
        metadata = dict(documento.get("metadata", {}))
        metadata["chunking"] = {
            "chunk_index": indice,
            "total_chunks_documento": total,
            "tipo_chunk": tipo_chunk,
            "tokens_aproximados": contar_tokens(texto),
            "alvo_tokens": alvo_tokens,
            "max_tokens": max_tokens,
            "overlap_tokens": overlap_tokens,
        }

        chunks.append(
            {
                "id_chunk": f"{documento['id_documento']}:chunk-{indice:04d}:{chunk_hash[:12]}",
                "id_documento": documento["id_documento"],
                "id_fonte": documento["id_fonte"],
                "tipo": documento["tipo"],
                "titulo": documento["titulo"],
                "conteudo": texto,
                "conteudo_hash": chunk_hash,
                "metadata": metadata,
            }
        )

    return chunks


def gerar_chunks(
    documentos: list[dict[str, Any]],
    alvo_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    chunks = []
    chunks_por_documento = {}

    for documento in documentos:
        chunks_doc = gerar_chunks_documento(documento, alvo_tokens, max_tokens, overlap_tokens)
        chunks.extend(chunks_doc)
        chunks_por_documento[documento["id_documento"]] = len(chunks_doc)

    por_tipo_doc = Counter(chunk["tipo"] for chunk in chunks)
    por_tipo_chunk = Counter(chunk["metadata"]["chunking"]["tipo_chunk"] for chunk in chunks)
    tokens = [chunk["metadata"]["chunking"]["tokens_aproximados"] for chunk in chunks]

    resumo = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total_documentos": len(documentos),
        "total_chunks": len(chunks),
        "configuracao": {
            "alvo_tokens": alvo_tokens,
            "max_tokens": max_tokens,
            "overlap_tokens": overlap_tokens,
        },
        "por_tipo_documento": dict(sorted(por_tipo_doc.items())),
        "por_tipo_chunk": dict(sorted(por_tipo_chunk.items())),
        "tokens_aproximados": {
            "min": min(tokens) if tokens else 0,
            "max": max(tokens) if tokens else 0,
            "media": round(sum(tokens) / len(tokens), 1) if tokens else 0,
        },
        "chunks_por_documento": chunks_por_documento,
    }
    return chunks, resumo


def caminho_absoluto_ou_raiz(caminho: Path) -> Path:
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera chunks para ingestao da RAG.")
    parser.add_argument("--entrada", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--resumo", type=Path, default=RESUMO_PADRAO)
    parser.add_argument("--alvo-tokens", type=int, default=700)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--overlap-tokens", type=int, default=100)
    args = parser.parse_args()

    if args.alvo_tokens <= 0 or args.max_tokens <= 0 or args.overlap_tokens < 0:
        raise SystemExit("Tokens devem ser positivos, exceto overlap que pode ser zero.")
    if args.alvo_tokens > args.max_tokens:
        raise SystemExit("--alvo-tokens deve ser menor ou igual a --max-tokens.")
    if args.overlap_tokens >= args.max_tokens:
        raise SystemExit("--overlap-tokens deve ser menor que --max-tokens.")

    entrada = caminho_absoluto_ou_raiz(args.entrada)
    saida = caminho_absoluto_ou_raiz(args.saida)
    resumo_saida = caminho_absoluto_ou_raiz(args.resumo)

    documentos = carregar_jsonl(entrada)
    chunks, resumo = gerar_chunks(
        documentos=documentos,
        alvo_tokens=args.alvo_tokens,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap_tokens,
    )
    salvar_jsonl(chunks, saida)
    salvar_json(resumo, resumo_saida)

    print(f"Chunks gerados: {saida}")
    print(f"Resumo: {resumo_saida}")
    print(f"Total de documentos: {resumo['total_documentos']}")
    print(f"Total de chunks: {resumo['total_chunks']}")
    print(f"Por tipo de chunk: {resumo['por_tipo_chunk']}")
    print(f"Tokens aproximados: {resumo['tokens_aproximados']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
