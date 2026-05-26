"""
Servico de busca por pares Q&A curados (QAService).

Fluxo de `buscar`:
    1. Gera o embedding da query via `EmbeddingProvider`.
    2. Consulta `pares_qa` usando o operador de distancia cosseno do pgvector (`<=>`).
    3. Filtra por `ativo=True`, opcionalmente por `contexto` e `aprovado=True`.
    4. Converte distancia em score (`1 - distancia`) e aplica limiar minimo.
    5. Retorna lista ordenada de `ParRecuperado`.

Defaults de `top_k` e `score_minimo` vem de `settings.QA_TOP_K` e `settings.QA_SCORE_MINIMO`, mas podem ser sobrepostos por chamada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

from config import settings
from models import ParQA, Vector
from sqlalchemy import Float, bindparam, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from services.embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


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
    ):
        self._embeddings = embedding_provider
        self._engine = engine
        self._SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self._top_k_padrao = top_k_padrao
        self._score_minimo_padrao = score_minimo_padrao

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


# ----------------------------------------------------------------------
# Factory singleton (para uso com FastAPI Depends / app)
# ----------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_qa_service() -> QAService:
    """Retorna instancia singleton do QAService."""
    engine = create_engine(settings.DATABASE_URL, future=True)
    return QAService(
        embedding_provider=get_embedding_provider(),
        engine=engine,
        top_k_padrao=settings.QA_TOP_K,
        score_minimo_padrao=settings.QA_SCORE_MINIMO,
    )
