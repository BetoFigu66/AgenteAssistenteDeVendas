"""
Ingere chunks da RAG na tabela `documentos_conhecimento`.

Pipeline:
    1. Le `backend/data/rag/chunks_conhecimento.jsonl` (saida do Passo 4).
    2. Para cada chunk, usa `id_chunk` como `id_externo` na tabela.
    3. Decide entre inserir, atualizar ou ignorar com base em `conteudo_hash`:
        - se nao existe no banco -> inserir;
        - se existe e hash mudou (ou estava inativo) -> atualizar;
        - se existe e hash e o mesmo -> ignorar.
    4. Gera embeddings em lote apenas para os chunks novos/atualizados.
    5. Opcionalmente marca como `ativo=False` os chunks que existem no banco
       mas desapareceram da entrada (soft-delete).
    6. Grava `backend/data/rag/ingestao_resumo.json` com as estatisticas.

Uso:
    python -m scripts.ingerir_conhecimento_rag
    python -m scripts.ingerir_conhecimento_rag --dry-run
    python -m scripts.ingerir_conhecimento_rag --entrada caminho.jsonl

Executar a partir de `backend/` com o .env configurado (EMBEDDING_API_KEY etc.).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

# Permite rodar tanto como `python -m scripts.ingerir_conhecimento_rag`
# quanto como `python scripts/ingerir_conhecimento_rag.py` a partir de backend/.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings  # noqa: E402
from models import DocumentoConhecimento  # noqa: E402
from services.embeddings import EmbeddingProvider, get_embedding_provider  # noqa: E402
from sqlalchemy import create_engine, select, update  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

RAIZ_PROJETO = BACKEND_DIR.parent
ENTRADA_PADRAO = BACKEND_DIR / "data" / "rag" / "chunks_conhecimento.jsonl"
RESUMO_PADRAO = BACKEND_DIR / "data" / "rag" / "ingestao_resumo.json"
LOTE_EMBEDDINGS_PADRAO = 64


@dataclass
class EstatisticasIngestao:
    """Contadores finais da execucao."""

    total_lidos: int = 0
    duplicados_na_entrada: int = 0
    novos: int = 0
    atualizados: int = 0
    ignorados: int = 0
    desativados: int = 0
    reativados: int = 0
    embeddings_gerados: int = 0
    lotes_embeddings: int = 0
    tokens_input: int = 0
    dimensoes: int = 0
    provider: str = ""
    modelo: str = ""
    dry_run: bool = False
    entrada: str = ""
    inicio: str = ""
    fim: str = ""
    duracao_segundos: float = 0.0


def caminho_absoluto_ou_raiz(caminho: Path) -> Path:
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho


def carregar_chunks(caminho: Path) -> list[dict[str, Any]]:
    """Le o JSONL de chunks gerado no Passo 4."""
    registros: list[dict[str, Any]] = []
    with caminho.open("r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if linha:
                registros.append(json.loads(linha))
    return registros


def lotes(iteravel: Iterable[Any], tamanho: int) -> Iterator[list[Any]]:
    """Agrupa itens em blocos de tamanho maximo `tamanho`."""
    bloco: list[Any] = []
    for item in iteravel:
        bloco.append(item)
        if len(bloco) >= tamanho:
            yield bloco
            bloco = []
    if bloco:
        yield bloco


async def gerar_embeddings_em_lote(
    textos: list[str],
    provider: EmbeddingProvider,
    tamanho_lote: int,
    stats: EstatisticasIngestao,
) -> list[list[float]]:
    """Gera embeddings em lotes e atualiza estatisticas."""
    resultado: list[list[float]] = []
    for bloco in lotes(textos, tamanho_lote):
        resposta = await provider.embed(bloco)
        resultado.extend(resposta.embeddings)
        stats.embeddings_gerados += len(resposta.embeddings)
        stats.lotes_embeddings += 1
        if resposta.tokens_input:
            stats.tokens_input += resposta.tokens_input
    return resultado


def _deduplicar_chunks(
    chunks: list[dict[str, Any]],
    stats: EstatisticasIngestao,
) -> dict[str, dict[str, Any]]:
    """Garante um chunk por `id_chunk`; se houver duplicatas, mantem a ultima."""
    por_id: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        id_externo = chunk["id_chunk"]
        if id_externo in por_id:
            stats.duplicados_na_entrada += 1
        por_id[id_externo] = chunk
    return por_id


async def ingerir(
    entrada: Path,
    resumo_saida: Path,
    dry_run: bool,
    desativar_removidos: bool,
    tamanho_lote: int,
) -> EstatisticasIngestao:
    inicio = datetime.now(timezone.utc)
    stats = EstatisticasIngestao(
        dry_run=dry_run,
        entrada=str(entrada),
        inicio=inicio.isoformat(),
    )

    chunks = carregar_chunks(entrada)
    stats.total_lidos = len(chunks)

    if not chunks:
        print(f"[ingestao] nenhum chunk encontrado em {entrada}")
        _finalizar_stats(stats, inicio)
        _salvar_resumo(resumo_saida, stats)
        return stats

    chunk_por_id = _deduplicar_chunks(chunks, stats)
    ids_entrada = set(chunk_por_id.keys())

    provider: EmbeddingProvider | None = None
    if not dry_run:
        provider = get_embedding_provider()
        stats.provider = provider.nome
        stats.modelo = provider.modelo
        stats.dimensoes = provider.dimensoes

    engine = create_engine(settings.DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionLocal() as session:
        # Snapshot dos registros existentes em um unico SELECT.
        existentes: dict[str, dict[str, Any]] = {}
        stmt = select(
            DocumentoConhecimento.id,
            DocumentoConhecimento.id_externo,
            DocumentoConhecimento.conteudo_hash,
            DocumentoConhecimento.ativo,
        )
        for row in session.execute(stmt).all():
            existentes[row.id_externo] = {
                "id": row.id,
                "conteudo_hash": row.conteudo_hash,
                "ativo": row.ativo,
            }

        para_inserir: list[dict[str, Any]] = []
        para_atualizar: list[dict[str, Any]] = []

        for id_externo, chunk in chunk_por_id.items():
            hash_novo = chunk["conteudo_hash"]
            prev = existentes.get(id_externo)
            if prev is None:
                para_inserir.append(chunk)
            elif prev["conteudo_hash"] == hash_novo and prev["ativo"]:
                stats.ignorados += 1
            else:
                if prev["conteudo_hash"] == hash_novo and not prev["ativo"]:
                    stats.reativados += 1
                para_atualizar.append(chunk)

        total_embed = len(para_inserir) + len(para_atualizar)
        print(
            f"[ingestao] lidos={stats.total_lidos} "
            f"novos={len(para_inserir)} atualizar={len(para_atualizar)} "
            f"ignorados={stats.ignorados} duplicados_entrada={stats.duplicados_na_entrada}"
        )

        if dry_run:
            print("[ingestao] dry-run ativo: nao gera embeddings nem grava no banco.")
            _finalizar_stats(stats, inicio)
            _salvar_resumo(resumo_saida, stats)
            return stats

        embeddings: list[list[float]] = []
        if total_embed > 0:
            print(f"[ingestao] gerando {total_embed} embedding(s) em lotes de " 
                f"{tamanho_lote} (provider={provider.nome} modelo={provider.modelo})")
            textos = [c["conteudo"] for c in para_inserir + para_atualizar]
            embeddings = await gerar_embeddings_em_lote(textos, provider, tamanho_lote, stats)

            if len(embeddings) != total_embed:
                raise RuntimeError("Quantidade de embeddings retornada difere do esperado:" 
                    f" {len(embeddings)} != {total_embed}")

        offset = 0
        for chunk in para_inserir:
            vetor = embeddings[offset]
            offset += 1
            doc = DocumentoConhecimento(
                id_externo=chunk["id_chunk"],
                id_documento_origem=chunk["id_documento"],
                id_fonte=chunk.get("id_fonte"),
                tipo=chunk["tipo"],
                titulo=chunk["titulo"],
                conteudo=chunk["conteudo"],
                metadados=chunk.get("metadata") or {},
                conteudo_hash=chunk["conteudo_hash"],
                embedding=vetor,
                ativo=True,
            )
            session.add(doc)
            stats.novos += 1

        for chunk in para_atualizar:
            vetor = embeddings[offset]
            offset += 1
            session.execute(
                update(DocumentoConhecimento)
                .where(DocumentoConhecimento.id_externo == chunk["id_chunk"])
                .values(
                    id_documento_origem=chunk["id_documento"],
                    id_fonte=chunk.get("id_fonte"),
                    tipo=chunk["tipo"],
                    titulo=chunk["titulo"],
                    conteudo=chunk["conteudo"],
                    metadados=chunk.get("metadata") or {},
                    conteudo_hash=chunk["conteudo_hash"],
                    embedding=vetor,
                    ativo=True,
                )
            )
            stats.atualizados += 1

        if desativar_removidos:
            a_desativar = [
                id_externo 
                for id_externo, prev in existentes.items() 
                if id_externo not in ids_entrada and prev["ativo"]
            ]
            if a_desativar:
                session.execute(update(DocumentoConhecimento).where(DocumentoConhecimento.id_externo.in_(a_desativar)).values(ativo=False))
                stats.desativados = len(a_desativar)

        session.commit()

    _finalizar_stats(stats, inicio)
    _salvar_resumo(resumo_saida, stats)
    return stats


def _finalizar_stats(stats: EstatisticasIngestao, inicio: datetime) -> None:
    fim = datetime.now(timezone.utc)
    stats.fim = fim.isoformat()
    stats.duracao_segundos = round((fim - inicio).total_seconds(), 3)


def _salvar_resumo(caminho: Path, stats: EstatisticasIngestao) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(asdict(stats), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingere chunks da RAG na tabela documentos_conhecimento.")
    parser.add_argument("--entrada", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--resumo", type=Path, default=RESUMO_PADRAO)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nao gera embeddings nem grava no banco; apenas mostra o plano.",
    )
    parser.add_argument(
        "--nao-desativar-removidos",
        action="store_true",
        help="Nao marca como inativos chunks ausentes da entrada.",
    )
    parser.add_argument(
        "--lote",
        type=int,
        default=LOTE_EMBEDDINGS_PADRAO,
        help=f"Tamanho do lote ao chamar o provider de embeddings (padrao {LOTE_EMBEDDINGS_PADRAO}).",
    )
    args = parser.parse_args()

    if args.lote <= 0:
        raise SystemExit("--lote deve ser positivo.")

    entrada = caminho_absoluto_ou_raiz(args.entrada)
    if not entrada.exists():
        raise SystemExit(f"Arquivo de entrada nao encontrado: {entrada}")
    resumo = caminho_absoluto_ou_raiz(args.resumo)

    stats = asyncio.run(
        ingerir(
            entrada=entrada,
            resumo_saida=resumo,
            dry_run=args.dry_run,
            desativar_removidos=not args.nao_desativar_removidos,
            tamanho_lote=args.lote,
        )
    )

    print()
    print("Resumo da ingestao:")
    print(json.dumps(asdict(stats), ensure_ascii=False, indent=2))
    print(f"Resumo salvo em: {resumo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
