"""
Servico de recuperacao semantica (RAG) sobre `documentos_conhecimento`.

Fluxo de `buscar`:
    1. Gera o embedding da pergunta via `EmbeddingProvider`.
    2. Consulta a tabela usando o operador de distancia cosseno do pgvector (`<=>`).
    3. Aplica filtros por `ativo=True` e, opcionalmente, por `tipo`.
    4. Converte a distancia em score (`1 - distancia`) e aplica limiar minimo.
    5. Retorna lista ordenada de `DocumentoRecuperado`.

Defaults de `top_k` e `score_minimo` vem de `settings.RAG_TOP_K` e
`settings.RAG_SCORE_MINIMO`, mas podem ser sobrepostos por chamada.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional, Sequence

from sqlalchemy import Float, bindparam, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from models import DocumentoConhecimento, Vector
from services.embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


@dataclass
class DocumentoRecuperado:
    """Trecho recuperado da base de conhecimento."""

    id: int
    id_externo: str
    id_documento_origem: str
    tipo: str
    titulo: str
    conteudo: str
    score: float
    distancia: float
    metadados: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "id_externo": self.id_externo,
            "id_documento_origem": self.id_documento_origem,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "conteudo": self.conteudo,
            "score": self.score,
            "distancia": self.distancia,
            "metadata": self.metadados,
        }


class RetrievalService:
    """Busca semantica em `documentos_conhecimento` usando pgvector."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        engine: Engine,
        top_k_padrao: int = 4,
        score_minimo_padrao: float = 0.70,
    ):
        self._embeddings = embedding_provider
        self._engine = engine
        self._SessionLocal = sessionmaker(
            bind=engine, autocommit=False, autoflush=False
        )
        self._top_k_padrao = top_k_padrao
        self._score_minimo_padrao = score_minimo_padrao

    async def buscar(
        self,
        query: str,
        top_k: Optional[int] = None,
        tipo: Optional[str] = "produto",
        tipos: Optional[Sequence[str]] = None,
        score_minimo: Optional[float] = None,
        apenas_ativos: bool = True,
    ) -> list[DocumentoRecuperado]:
        """
        Recupera trechos relevantes para a pergunta.

        Args:
            query: Pergunta/texto do usuario.
            top_k: Quantidade maxima de trechos a retornar.
            tipo: Filtro por um unico `tipo` (ignorado se `tipos` for passado).
                  Passe `None` para nao filtrar por tipo.
            tipos: Filtro por varios tipos (tem precedencia sobre `tipo`).
            score_minimo: Score minimo (0..1) para considerar o trecho.
            apenas_ativos: Se True, filtra por `ativo=True`.

        Returns:
            Lista de `DocumentoRecuperado` ordenada por score desc.
        """
        if not query or not query.strip():
            logger.debug("[RAG] query vazia; retornando lista vazia")
            return []

        top_k_efetivo = top_k if top_k is not None else self._top_k_padrao
        score_min = (
            score_minimo if score_minimo is not None else self._score_minimo_padrao
        )
        if top_k_efetivo <= 0:
            return []

        vetor = await self._embeddings.embed_um(query)
        logger.debug(
            "[RAG] embedding gerado dim=%d provider=%s",
            len(vetor),
            self._embeddings.nome,
        )

        resultados = self._consultar_por_similaridade(
            vetor=vetor,
            top_k=top_k_efetivo,
            tipo=tipo,
            tipos=tipos,
            apenas_ativos=apenas_ativos,
        )

        filtrados = [r for r in resultados if r.score >= score_min]

        logger.debug(
            "[RAG] buscar(query=%r tipo=%s tipos=%s): "
            "retornados=%d filtrados=%d score_min=%.3f top_k=%d",
            query[:80],
            tipo,
            list(tipos) if tipos else None,
            len(resultados),
            len(filtrados),
            score_min,
            top_k_efetivo,
        )
        if filtrados:
            logger.debug(
                "[RAG] melhores: %s",
                [
                    (r.titulo[:60], round(r.score, 3))
                    for r in filtrados[:3]
                ],
            )
        return filtrados

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _consultar_por_similaridade(
        self,
        vetor: list[float],
        top_k: int,
        tipo: Optional[str],
        tipos: Optional[Sequence[str]],
        apenas_ativos: bool,
    ) -> list[DocumentoRecuperado]:
        # Usa o operador de distancia cosseno do pgvector ("<=>").
        # O bindparam usa o mesmo tipo Vector definido no modelo para
        # aproveitar o bind_processor e serializar o vetor corretamente.
        dim = self._embeddings.dimensoes
        param = bindparam("q_emb", value=vetor, type_=Vector(dim))
        distancia_expr = DocumentoConhecimento.embedding.op("<=>", return_type=Float())(param)

        stmt = (
            select(DocumentoConhecimento, distancia_expr.label("distancia"))
            .order_by(distancia_expr)
            .limit(top_k)
        )
        if apenas_ativos:
            stmt = stmt.where(DocumentoConhecimento.ativo.is_(True))
        if tipos:
            stmt = stmt.where(DocumentoConhecimento.tipo.in_(list(tipos)))
        elif tipo:
            stmt = stmt.where(DocumentoConhecimento.tipo == tipo)

        with self._SessionLocal() as session:  # type: Session
            linhas = session.execute(stmt).all()

        resultados: list[DocumentoRecuperado] = []
        for doc, distancia in linhas:
            try:
                dist_float = float(distancia)
            except (TypeError, ValueError):
                logger.warning("[RAG] distancia invalida retornada: %r", distancia)
                continue
            score = 1.0 - dist_float
            resultados.append(
                DocumentoRecuperado(
                    id=doc.id,
                    id_externo=doc.id_externo,
                    id_documento_origem=doc.id_documento_origem,
                    tipo=doc.tipo,
                    titulo=doc.titulo,
                    conteudo=doc.conteudo,
                    score=score,
                    distancia=dist_float,
                    metadados=doc.metadados or {},
                )
            )
        return resultados


# ----------------------------------------------------------------------
# Factory singleton (para uso com FastAPI Depends / app)
# ----------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Retorna instancia singleton do `RetrievalService`."""
    engine = create_engine(settings.DATABASE_URL, future=True)
    return RetrievalService(
        embedding_provider=get_embedding_provider(),
        engine=engine,
        top_k_padrao=settings.RAG_TOP_K,
        score_minimo_padrao=settings.RAG_SCORE_MINIMO,
    )
