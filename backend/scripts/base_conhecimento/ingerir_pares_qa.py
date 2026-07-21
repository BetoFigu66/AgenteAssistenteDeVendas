"""
Ingere pares Q&A curados na tabela `pares_qa`.

Pipeline:
    1. Le `backend/data/seed_pares_qa.json` (ou arquivo passado via --arquivo).
    2. Para cada par, usa `id_externo` do JSON ou calcula hash da `pergunta`.
    3. Decide entre inserir, atualizar ou ignorar com base no hash da pergunta:
        - se nao existe no banco -> inserir;
        - se existe e hash mudou -> atualizar (re-gera embedding);
        - se existe e hash e o mesmo e ativo -> ignorar.
    4. Gera embeddings em lote apenas para os pares novos/atualizados.
    5. Grava `backend/data/ingestao_pares_qa_resumo.json` com as estatisticas.

Uso:
    python -m scripts.base_conhecimento.ingerir_pares_qa
    python -m scripts.base_conhecimento.ingerir_pares_qa --dry-run
    python -m scripts.base_conhecimento.ingerir_pares_qa --aprovar-automaticamente
    python -m scripts.base_conhecimento.ingerir_pares_qa --arquivo caminho/outro.json

Executar a partir de `backend/` com o .env configurado (EMBEDDING_API_KEY etc. — só
necessário se algum par for ficar aprovado=True nesta execução; ver lazy embedding
acima).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings  # noqa: E402
from models import ParQA  # noqa: E402
from services.embeddings import EmbeddingProvider, get_embedding_provider  # noqa: E402
from sqlalchemy import create_engine, select, update  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

ENTRADA_PADRAO = BACKEND_DIR / "data" / "seed_pares_qa.json"
RESUMO_PADRAO = BACKEND_DIR / "data" / "ingestao_pares_qa_resumo.json"
LOTE_EMBEDDINGS_PADRAO = 32


@dataclass
class EstatisticasIngestao:
    """Contadores finais da execucao."""

    total_lidos: int = 0
    duplicados_na_entrada: int = 0
    novos: int = 0
    atualizados: int = 0
    ignorados: int = 0
    embeddings_gerados: int = 0
    lotes_embeddings: int = 0
    tokens_input: int = 0
    dimensoes: int = 0
    provider: str = ""
    modelo: str = ""
    dry_run: bool = False
    aprovar_automaticamente: bool = False
    arquivo: str = ""
    inicio: str = ""
    fim: str = ""
    duracao_segundos: float = 0.0


def _hash_pergunta(pergunta: str) -> str:
    """SHA-256 truncado em 16 hex da pergunta normalizada."""
    return hashlib.sha256(pergunta.strip().lower().encode()).hexdigest()[:16]


def _id_externo_de(par: dict[str, Any]) -> str:
    """Retorna `id_externo` do JSON ou gera um a partir do hash da pergunta."""
    if par.get("id_externo"):
        return par["id_externo"]
    contexto = par.get("contexto", "geral")
    h = _hash_pergunta(par["pergunta"])
    return f"qa:{contexto}:{h}"


def carregar_pares(caminho: Path) -> list[dict[str, Any]]:
    """Le o JSON de pares Q&A."""
    with caminho.open("r", encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, list):
        raise ValueError(f"Esperado uma lista JSON em {caminho}, encontrado {type(dados).__name__}")
    return dados


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


def _deduplicar_pares(
    pares: list[dict[str, Any]],
    stats: EstatisticasIngestao,
) -> dict[str, dict[str, Any]]:
    """Garante um par por `id_externo`; se houver duplicatas, mantem o ultimo."""
    por_id: dict[str, dict[str, Any]] = {}
    for par in pares:
        id_ext = _id_externo_de(par)
        if id_ext in por_id:
            stats.duplicados_na_entrada += 1
        par["_id_externo_resolvido"] = id_ext
        par["_pergunta_hash"] = _hash_pergunta(par["pergunta"])
        por_id[id_ext] = par
    return por_id


async def ingerir(
    entrada: Path,
    resumo_saida: Path,
    dry_run: bool,
    aprovar_automaticamente: bool,
    tamanho_lote: int,
) -> EstatisticasIngestao:
    inicio = datetime.now(timezone.utc)
    stats = EstatisticasIngestao(
        dry_run=dry_run,
        aprovar_automaticamente=aprovar_automaticamente,
        arquivo=str(entrada),
        inicio=inicio.isoformat(),
    )

    pares = carregar_pares(entrada)
    stats.total_lidos = len(pares)

    if not pares:
        print(f"[ingestao_qa] nenhum par encontrado em {entrada}")
        _finalizar_stats(stats, inicio)
        _salvar_resumo(resumo_saida, stats)
        return stats

    par_por_id = _deduplicar_pares(pares, stats)

    # Lazy embedding (mesmo principio do POST /api/pares-qa manual): so vale a pena
    # pagar o custo de embedding para pares que vao ficar aprovados=True imediatamente
    # apos esta ingestao — os demais ficam como rascunho (embedding=None) e so geram
    # embedding quando alguem aprovar via painel/API.
    gerar_embeddings_agora = not dry_run and aprovar_automaticamente

    provider: EmbeddingProvider | None = None
    if gerar_embeddings_agora:
        provider = get_embedding_provider()
        stats.provider = provider.nome
        stats.modelo = provider.modelo
        stats.dimensoes = provider.dimensoes

    engine = create_engine(settings.DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionLocal() as session:
        existentes: dict[str, dict[str, Any]] = {}
        stmt = select(
            ParQA.id,
            ParQA.id_externo,
            ParQA.ativo,
        )
        for row in session.execute(stmt).all():
            existentes[row.id_externo] = {
                "id": row.id,
                "ativo": row.ativo,
            }

        para_inserir: list[dict[str, Any]] = []
        para_atualizar: list[dict[str, Any]] = []

        for id_externo, par in par_por_id.items():
            prev = existentes.get(id_externo)
            if prev is None:
                para_inserir.append(par)
            elif not prev["ativo"]:
                para_atualizar.append(par)
            else:
                stats.ignorados += 1

        total_embed = len(para_inserir) + len(para_atualizar)
        print(
            f"[ingestao_qa] lidos={stats.total_lidos} "
            f"novos={len(para_inserir)} atualizar={len(para_atualizar)} "
            f"ignorados={stats.ignorados} duplicados_entrada={stats.duplicados_na_entrada}"
        )

        if dry_run:
            print("[ingestao_qa] dry-run ativo: nao gera embeddings nem grava no banco.")
            _finalizar_stats(stats, inicio)
            _salvar_resumo(resumo_saida, stats)
            return stats

        embeddings: list[list[float]] = []
        if total_embed > 0 and gerar_embeddings_agora:
            print(f"[ingestao_qa] gerando {total_embed} embedding(s) em lotes de {tamanho_lote}"
                f" (provider={provider.nome} modelo={provider.modelo})")
            textos = [p["pergunta"] for p in para_inserir + para_atualizar]
            embeddings = await gerar_embeddings_em_lote(textos, provider, tamanho_lote, stats)
            if len(embeddings) != total_embed:
                raise RuntimeError("Quantidade de embeddings retornada difere do esperado:"
                    f" {len(embeddings)} != {total_embed}")
        elif total_embed > 0:
            print(
                f"[ingestao_qa] {total_embed} par(es) novo(s)/atualizado(s) sem aprovação "
                "automática — embedding não gerado agora (lazy embedding); será gerado na "
                "aprovação manual via painel/API."
            )

        offset = 0
        for par in para_inserir:
            vetor = embeddings[offset] if gerar_embeddings_agora else None
            if gerar_embeddings_agora:
                offset += 1
            novo = ParQA(
                id_externo=par["_id_externo_resolvido"],
                pergunta=par["pergunta"],
                resposta=par["resposta"],
                contexto=par.get("contexto"),
                tags=par.get("tags") or [],
                embedding=vetor,
                ativo=True,
                aprovado=aprovar_automaticamente,
                criado_por=par.get("criado_por", "seed"),
            )
            session.add(novo)
            stats.novos += 1

        for par in para_atualizar:
            vetor = embeddings[offset] if gerar_embeddings_agora else None
            if gerar_embeddings_agora:
                offset += 1
            session.execute(
                update(ParQA)
                .where(ParQA.id_externo == par["_id_externo_resolvido"])
                .values(
                    pergunta=par["pergunta"],
                    resposta=par["resposta"],
                    contexto=par.get("contexto"),
                    tags=par.get("tags") or [],
                    embedding=vetor,
                    ativo=True,
                    aprovado=aprovar_automaticamente or False,
                    criado_por=par.get("criado_por", "seed"),
                )
            )
            stats.atualizados += 1

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
    parser = argparse.ArgumentParser(description="Ingere pares Q&A curados na tabela pares_qa.")
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=ENTRADA_PADRAO,
        help=f"Caminho do JSON de entrada (padrao: {ENTRADA_PADRAO}).",
    )
    parser.add_argument(
        "--resumo",
        type=Path,
        default=RESUMO_PADRAO,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nao gera embeddings nem grava no banco; apenas mostra o plano.",
    )
    parser.add_argument(
        "--aprovar-automaticamente",
        action="store_true",
        help="Marca os pares ingeridos com aprovado=True (use so em ambientes de teste).",
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

    entrada = args.arquivo if args.arquivo.is_absolute() else Path.cwd() / args.arquivo
    if not entrada.exists():
        raise SystemExit(f"Arquivo de entrada nao encontrado: {entrada}")
    resumo = args.resumo if args.resumo.is_absolute() else Path.cwd() / args.resumo

    stats = asyncio.run(
        ingerir(
            entrada=entrada,
            resumo_saida=resumo,
            dry_run=args.dry_run,
            aprovar_automaticamente=args.aprovar_automaticamente,
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
