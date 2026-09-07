"""
Servico de busca por pares Q&A curados (QAService).

Fluxo de `buscar`:
    1. Gera o embedding da query via `EmbeddingProvider`.
    2. Consulta `pares_qa` usando o operador de distancia cosseno do pgvector (`<=>`).
    3. Filtra por `ativo=True`, opcionalmente por `contexto` e `aprovado=True`.
    4. Converte distancia em score (`1 - distancia`) e aplica limiar minimo.
    5. Retorna lista ordenada de `ParRecuperado`.

Defaults de `top_k` e `score_minimo` vem de `settings.QA_TOP_K` e `settings.QA_SCORE_MINIMO`,
mas podem ser sobrepostos por chamada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Optional, Protocol

from config import settings
from models import ParQA, Vector
from sqlalchemy import Float, bindparam, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from services.embeddings import EmbeddingProvider, get_embedding_provider

if TYPE_CHECKING:
    from services.debug_log import DebugLogger

logger = logging.getLogger(__name__)


class BuscadorQA(Protocol):
    """Forma exigida de quem busca pares Q&A — `QAService` (real) e `QAServiceNulo`
    (Null Object, usado quando QA está desabilitada ou falhou ao inicializar) satisfazem
    por duck typing, sem herança."""

    habilitado: bool

    async def buscar_melhor(
        self,
        query: str,
        *,
        apenas_aprovados: bool = True,
        dlog: Optional["DebugLogger"] = None,
    ) -> Optional["ParRecuperado"]: ...


@dataclass
class ParRecuperado:
    """Par Q&A recuperado da base de conhecimento."""

    id: int
    id_externo: str
    pergunta: str
    resposta: str
    contexto: Optional[str]
    tags: list[str]
    score: float
    distancia: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "id_externo": self.id_externo,
            "tipo": "qa_pair",
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "contexto": self.contexto,
            "tags": self.tags,
            "score": round(self.score, 4),
            "distancia": round(self.distancia, 4),
        }


class QAService:
    """Busca semantica em pares Q&A curados usando pgvector."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        engine: Engine,
        top_k_padrao: int = 3,
        score_minimo_padrao: float = 0.80,
        score_minimo_fulltext: float = 0.25,
        habilitado: bool = True,
        score_desambigua_padrao: Optional[float] = None,
        score_desambigua_fulltext: Optional[float] = None,
    ):
        self._embeddings = embedding_provider
        self._engine = engine
        self._SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self._top_k_padrao = top_k_padrao
        self._score_minimo_padrao = score_minimo_padrao
        self._score_minimo_fulltext = score_minimo_fulltext
        self.habilitado = habilitado
        # Limiares "desambigua" da zona cinza (REQ-014, Fase 7) — capturados aqui para
        # ficarem disponíveis a quem for construir a etapa de pergunta de clarificação
        # (REQ-003.7); `buscar()` ainda usa só o corte binário "responde" acima.
        self.score_desambigua_padrao = score_desambigua_padrao
        self.score_desambigua_fulltext = score_desambigua_fulltext

    async def buscar(
        self,
        query: str,
        contexto: Optional[str] = None,
        top_k: Optional[int] = None,
        score_minimo: Optional[float] = None,
        apenas_aprovados: bool = True,
    ) -> list[ParRecuperado]:
        """
        Recupera pares Q&A relevantes para a pergunta.

        Args:
            query: Pergunta do usuario.
            contexto: Filtro opcional por contexto (ex: "catraca", "relogio_ponto").
            top_k: Quantidade maxima de pares a retornar.
            score_minimo: Score minimo (0..1) para considerar o par.
            apenas_aprovados: Se True, retorna apenas pares com aprovado=True.

        Returns:
            Lista de ParRecuperado ordenada por score desc.
        """
        if not query or not query.strip():
            logger.debug("[QA] query vazia; retornando lista vazia")
            return []

        top_k_efetivo = top_k if top_k is not None else self._top_k_padrao
        score_min = score_minimo if score_minimo is not None else self._score_minimo_padrao
        if top_k_efetivo <= 0:
            return []

        # Camada 1: busca full-text nativa do PostgreSQL (sem custo de API)
        fts_resultados = self._buscar_por_fulltext(
            query=query,
            top_k=top_k_efetivo,
            contexto=contexto,
            apenas_aprovados=apenas_aprovados,
        )
        if fts_resultados:
            logger.debug(
                "[QA] hit via full-text (ts_rank): %d resultado(s)",
                len(fts_resultados),
            )
            return fts_resultados

        # Camada 2: busca semantica por embedding (custo de API)
        vetor = await self._embeddings.embed_um(query)
        logger.debug(
            "[QA] embedding gerado dim=%d provider=%s",
            len(vetor),
            self._embeddings.nome,
        )

        resultados = self._consultar_por_similaridade(
            vetor=vetor,
            top_k=top_k_efetivo,
            contexto=contexto,
            apenas_aprovados=apenas_aprovados,
        )

        filtrados = [r for r in resultados if r.score >= score_min]

        logger.debug(
            "[QA] buscar(query=%r contexto=%s): retornados=%d filtrados=%d score_min=%.3f",
            query[:80],
            contexto,
            len(resultados),
            len(filtrados),
            score_min,
        )
        if filtrados:
            logger.debug(
                "[QA] melhores: %s",
                [(r.id_externo[:60], round(r.score, 3)) for r in filtrados[:3]],
            )
        return filtrados

    async def buscar_melhor(
        self,
        query: str,
        *,
        apenas_aprovados: bool = True,
        dlog: Optional["DebugLogger"] = None,
    ) -> Optional[ParRecuperado]:
        """Busca o melhor par Q&A para a query — `None` se desabilitado, sem hit ou em
        falha. Absorve o log de auditoria (`dlog`) e a tolerância a falha que antes
        viviam em `ProcessadorMensagem._buscar_resposta_qa` (Feature Envy: só liam
        estado deste serviço)."""
        if not self.habilitado:
            if dlog:
                dlog.log("qa_busca", "QA desabilitado ou serviço não inicializado")
            return None
        if dlog:
            dlog.log("qa_busca", f'query="{query[:80]}" score_min={self._score_minimo_padrao}')
        try:
            pares = await self.buscar(query=query, apenas_aprovados=apenas_aprovados)
            if pares:
                top = pares[0]
                if dlog:
                    dlog.log(
                        "qa_resultado",
                        f"hit score={top.score:.4f} id={top.id_externo} pergunta='{top.pergunta[:50]}'",
                    )
                return top
            if dlog:
                dlog.log("qa_resultado", f"sem hits (score_min={self._score_minimo_padrao})")
            return None
        except Exception as e:
            logger.warning("[QA] Falha na busca: %s", e)
            if dlog:
                dlog.log("qa_erro", f"{type(e).__name__}: {str(e)[:80]}")
            return None

    async def buscar_candidatos(
        self,
        query: str,
        top_k: int = 10,
        contexto: Optional[str] = None,
        apenas_aprovados: bool = False,
    ) -> list[ParRecuperado]:
        """
        Diagnóstico: retorna top-K por similaridade sem filtrar por score_minimo.

        Usado pelo pacote de análise do [curador_conhecimento] para expor
        quase-hits abaixo do limiar de produção.
        """
        if not query or not query.strip() or top_k <= 0:
            return []

        vetor = await self._embeddings.embed_um(query)
        return self._consultar_por_similaridade(
            vetor=vetor,
            top_k=top_k,
            contexto=contexto,
            apenas_aprovados=apenas_aprovados,
        )

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _consultar_por_similaridade(
        self,
        vetor: list[float],
        top_k: int,
        contexto: Optional[str],
        apenas_aprovados: bool,
    ) -> list[ParRecuperado]:
        dim = self._embeddings.dimensoes
        param = bindparam("q_emb", value=vetor, type_=Vector(dim))
        distancia_expr = ParQA.embedding.op("<=>", return_type=Float())(param)

        stmt = (
            select(ParQA, distancia_expr.label("distancia"))
            .where(ParQA.ativo.is_(True))
            .where(ParQA.embedding.isnot(None))
            .order_by(distancia_expr)
            .limit(top_k)
        )
        if apenas_aprovados:
            stmt = stmt.where(ParQA.aprovado.is_(True))
        if contexto:
            stmt = stmt.where(ParQA.contexto == contexto)

        with self._SessionLocal() as session:  # type: Session
            linhas = session.execute(stmt).all()

        resultados: list[ParRecuperado] = []
        for par, distancia in linhas:
            try:
                dist_float = float(distancia)
            except (TypeError, ValueError):
                logger.warning("[QA] distancia invalida retornada: %r", distancia)
                continue
            score = 1.0 - dist_float
            resultados.append(
                ParRecuperado(
                    id=par.id,
                    id_externo=par.id_externo,
                    pergunta=par.pergunta,
                    resposta=par.resposta,
                    contexto=par.contexto,
                    tags=par.tags or [],
                    score=score,
                    distancia=dist_float,
                )
            )
        return resultados

    def _buscar_por_fulltext(
        self,
        query: str,
        top_k: int,
        contexto: Optional[str],
        apenas_aprovados: bool,
    ) -> list[ParRecuperado]:
        """
        Busca por similaridade textual usando PostgreSQL full-text search.

        Usa ts_rank sobre a coluna pergunta_tsv (TSVECTOR) sem custo de API.
        Retorna lista vazia se nenhum resultado atinge o score minimo.
        """
        if not query or not query.strip():
            return []

        tsquery = func.plainto_tsquery("portuguese_unaccent", query)
        rank_expr = func.ts_rank(ParQA.pergunta_tsv, tsquery).label("rank")

        stmt = (
            select(ParQA, rank_expr)
            .where(ParQA.ativo.is_(True))
            .where(ParQA.pergunta_tsv.isnot(None))
            .where(ParQA.pergunta_tsv.op("@@")(tsquery))
            .order_by(rank_expr.desc())
            .limit(top_k)
        )
        if apenas_aprovados:
            stmt = stmt.where(ParQA.aprovado.is_(True))
        if contexto:
            stmt = stmt.where(ParQA.contexto == contexto)

        with self._SessionLocal() as session:  # type: Session
            linhas = session.execute(stmt).all()

        resultados: list[ParRecuperado] = []
        for par, rank in linhas:
            try:
                rank_float = float(rank)
            except (TypeError, ValueError):
                logger.warning("[QA] rank invalido retornado: %r", rank)
                continue
            if rank_float < self._score_minimo_fulltext:
                continue
            resultados.append(
                ParRecuperado(
                    id=par.id,
                    id_externo=par.id_externo,
                    pergunta=par.pergunta,
                    resposta=par.resposta,
                    contexto=par.contexto,
                    tags=par.tags or [],
                    score=rank_float,
                    distancia=1.0 - rank_float,
                )
            )
        return resultados


class QAServiceNulo:
    """Null Object de `QAService` — usado quando QA está desabilitada por configuração
    ou falhou ao inicializar (ex.: `EMBEDDING_API_KEY` ausente em dev). Satisfaz
    `BuscadorQA`: sempre "sem resultado", sem tocar rede/banco, sem exigir
    `embedding_provider`/`engine` reais."""

    habilitado = False

    async def buscar_melhor(
        self,
        query: str,
        *,
        apenas_aprovados: bool = True,
        dlog: Optional["DebugLogger"] = None,
    ) -> Optional[ParRecuperado]:
        if dlog:
            dlog.log("qa_busca", "QA desabilitado ou serviço não inicializado")
        return None


# ----------------------------------------------------------------------
# Factory singleton (para uso com FastAPI Depends / app)
# ----------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_qa_service() -> QAService:
    """Retorna instancia singleton do QAService.

    Limiares "responde" da zona cinza (REQ-014, Fase 7) substituem os defaults de
    `Settings` quando persistidos em `parametros` — mesmo padrão do `RetrievalService`
    (valor carregado uma vez na primeira chamada; `PATCH /api/config/rag` muta os
    atributos da instância diretamente para ter efeito sem restart).
    """
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    from services.parametro_service import ParametroService

    engine = create_engine(settings.DATABASE_URL, future=True)
    with _sessionmaker(bind=engine)() as sessao:
        limiares = ParametroService(sessao).limiares_zona_cinza()
        qa_habilitado = ParametroService(sessao).get_bool("qa_enabled", settings.QA_ENABLED)
    return QAService(
        embedding_provider=get_embedding_provider(),
        engine=engine,
        top_k_padrao=settings.QA_TOP_K,
        score_minimo_padrao=limiares["qa_embedding_responde_min"],
        score_minimo_fulltext=limiares["qa_fulltext_responde_min"],
        habilitado=qa_habilitado,
        score_desambigua_padrao=limiares["qa_embedding_desambigua_min"],
        score_desambigua_fulltext=limiares["qa_fulltext_desambigua_min"],
    )
