"""
Busca do FAQ de ajuda contextual do painel.

Duas camadas, na ordem (mesmo principio do `QAService`, mas sobre `ajuda_conteudos`):

  1. **Full-text** nativo do Postgres sobre `pergunta_tsv`, com o dicionario
     `portuguese_unaccent` (ignora acento e aplica stemming). Custo zero.
  2. **Embeddings** (pgvector) apenas se o full-text nao achou nada. Resolve
     sinonimo — "como mudo o parametro" nao casa por radical com "como altero o
     valor de um parametro", mas casa semanticamente.

A camada 2 depende de `EMBEDDING_API_KEY`. Se ela falhar ou nao estiver
configurada, a busca devolve o que a camada 1 achou (possivelmente nada) em vez
de estourar: ajuda indisponivel nao pode derrubar a tela.

Hierarquia de contexto: uma pergunta feita em `reports.detalhe` procura conteudo
de `reports.detalhe`, depois de `reports`, e por fim os globais (`contexto_id`
nulo, validos em qualquer tela). O mais especifico ganha — e o proposito de uma
ajuda "contextual"; um conteudo global otimo nao deve passar na frente de um
conteudo especifico daquela tela.

Nada aqui e usado pelo `ProcessadorMensagem`: este modulo nao responde cliente.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

from config import settings
from models import AjudaConsulta, AjudaConteudo, AjudaContexto, Vector
from sqlalchemy import Float, bindparam, case, func, literal, or_, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ORIGEM_FULLTEXT = "fulltext"
ORIGEM_EMBEDDING = "embedding"

_CONFIG_FTS = "portuguese_unaccent"


@dataclass
class ResultadoAjuda:
    """Conteudo de ajuda recuperado para uma pergunta."""

    conteudo_id: int
    pergunta: str
    resposta: str
    contexto_chave: Optional[str]
    score: float
    origem: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conteudo_id": self.conteudo_id,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "contexto_chave": self.contexto_chave,
            "score": round(self.score, 4),
            "origem": self.origem,
        }


def contextos_candidatos(contexto: Optional[str]) -> List[str]:
    """
    Expande um contexto na lista do mais especifico ao mais generico.

    >>> contextos_candidatos("reports.detalhe")
    ['reports.detalhe', 'reports']

    Os globais (`contexto_id` nulo) entram sempre e nao aparecem nesta lista.
    """
    partes = [p for p in str(contexto or "").split(".") if p]
    candidatos: List[str] = []
    while partes:
        candidatos.append(".".join(partes))
        partes.pop()
    return candidatos


class AjudaService:
    """Busca e sugestoes do FAQ de ajuda. Recebe a `Session` de quem chama."""

    def __init__(
        self,
        sessao: Session,
        top_k: Optional[int] = None,
        fulltext_min: Optional[float] = None,
        embedding_min: Optional[float] = None,
    ):
        self._s = sessao
        self._top_k = top_k if top_k is not None else settings.AJUDA_TOP_K
        self._fulltext_min = fulltext_min if fulltext_min is not None else settings.AJUDA_FULLTEXT_MIN
        self._embedding_min = embedding_min if embedding_min is not None else settings.AJUDA_EMBEDDING_MIN

    # ------------------------------------------------------------------
    # Busca
    # ------------------------------------------------------------------

    async def buscar(self, pergunta: str, contexto: Optional[str] = None) -> List[ResultadoAjuda]:
        """Camada 1 (full-text) e, se nao achar, camada 2 (embeddings)."""
        pergunta = (pergunta or "").strip()
        if not pergunta:
            return []

        resultados = self._buscar_fulltext(pergunta, contexto)
        if resultados:
            logger.debug("[Ajuda] hit full-text: %d resultado(s)", len(resultados))
            return resultados

        vetor = await self._embutir(pergunta)
        if vetor is None:
            return []
        return self._buscar_embedding(vetor, contexto)

    def _base_query(self, contexto: Optional[str]):
        """
        SELECT com join no contexto e a expressao de especificidade.

        `especificidade` ordena os candidatos: quanto mais especifico o contexto do
        conteudo, maior o numero. Global (sem contexto) fica em 0.
        """
        candidatos = contextos_candidatos(contexto)
        # O primeiro da lista e o mais especifico, entao recebe o maior peso.
        pesos = {chave: len(candidatos) - i for i, chave in enumerate(candidatos)}
        especificidade = (
            case(pesos, value=AjudaContexto.chave, else_=0) if pesos else literal(0)
        )

        stmt = (
            select(AjudaConteudo, AjudaContexto.chave, especificidade.label("especificidade"))
            .join(AjudaContexto, AjudaConteudo.contexto_id == AjudaContexto.id, isouter=True)
            .where(AjudaConteudo.ativo.is_(True))
        )
        if candidatos:
            # Conteudo do contexto pedido (ou de um ancestral dele) OU global.
            stmt = stmt.where(
                or_(
                    AjudaConteudo.contexto_id.is_(None),
                    AjudaContexto.chave.in_(candidatos),
                )
            )
        return stmt

    def _buscar_fulltext(self, pergunta: str, contexto: Optional[str]) -> List[ResultadoAjuda]:
        tsquery = func.plainto_tsquery(_CONFIG_FTS, pergunta)
        rank = func.ts_rank(AjudaConteudo.pergunta_tsv, tsquery)

        # Sem `order_by` no SQL de proposito: a ordenacao combina especificidade do
        # contexto e score, e acontece em `_montar` (mesma regra para as duas camadas).
        stmt = (
            self._base_query(contexto)
            .where(AjudaConteudo.pergunta_tsv.isnot(None))
            .where(AjudaConteudo.pergunta_tsv.op("@@")(tsquery))
            .add_columns(rank.label("rank"))
        )
        linhas = self._s.execute(stmt).all()

        resultados = []
        for conteudo, chave, especificidade, valor_rank in linhas:
            try:
                score = float(valor_rank)
            except (TypeError, ValueError):
                continue
            if score < self._fulltext_min:
                continue
            resultados.append((especificidade, score, conteudo, chave))
        return self._montar(resultados, ORIGEM_FULLTEXT)

    def _buscar_embedding(self, vetor: List[float], contexto: Optional[str]) -> List[ResultadoAjuda]:
        param = bindparam("q_emb", value=vetor, type_=Vector(len(vetor)))
        distancia = AjudaConteudo.embedding.op("<=>", return_type=Float())(param)

        stmt = (
            self._base_query(contexto)
            .where(AjudaConteudo.embedding.isnot(None))
            .add_columns(distancia.label("distancia"))
        )
        linhas = self._s.execute(stmt).all()

        resultados = []
        for conteudo, chave, especificidade, valor_dist in linhas:
            try:
                score = 1.0 - float(valor_dist)
            except (TypeError, ValueError):
                continue
            if score < self._embedding_min:
                continue
            resultados.append((especificidade, score, conteudo, chave))
        return self._montar(resultados, ORIGEM_EMBEDDING)

    def _montar(self, linhas: list, origem: str) -> List[ResultadoAjuda]:
        """Ordena por especificidade do contexto e depois por score, e corta em top_k."""
        linhas.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [
            ResultadoAjuda(
                conteudo_id=conteudo.id,
                pergunta=conteudo.pergunta,
                resposta=conteudo.resposta,
                contexto_chave=chave,
                score=score,
                origem=origem,
            )
            for _especificidade, score, conteudo, chave in linhas[: self._top_k]
        ]

    async def _embutir(self, texto: str) -> Optional[List[float]]:
        """Embedding da pergunta, ou None se o provider nao estiver disponivel."""
        try:
            from services.embeddings import get_embedding_provider

            provider = get_embedding_provider()
            return await provider.embed_um(texto)
        except Exception as exc:
            logger.warning("[Ajuda] busca semantica indisponivel: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Sugestoes (sem pergunta) e auditoria
    # ------------------------------------------------------------------

    def sugestoes(self, contexto: Optional[str] = None, limite: int = 8) -> List[ResultadoAjuda]:
        """
        Perguntas para exibir quando o usuario abre a ajuda sem digitar nada.

        Ordena por especificidade do contexto, depois por `prioridade` (definida na
        tela de administracao) e por fim pelo id, para dar ordem estavel.
        """
        stmt = self._base_query(contexto)
        linhas = self._s.execute(stmt).all()

        ordenadas = sorted(
            linhas,
            key=lambda t: (t[2], t[0].prioridade, -t[0].id),
            reverse=True,
        )
        return [
            ResultadoAjuda(
                conteudo_id=conteudo.id,
                pergunta=conteudo.pergunta,
                resposta=conteudo.resposta,
                contexto_chave=chave,
                score=1.0,
                origem="sugestao",
            )
            for conteudo, chave, _especificidade in ordenadas[:limite]
        ]

    def registrar_consulta(
        self,
        pergunta: str,
        contexto: Optional[str],
        resultado: Optional[ResultadoAjuda],
        usuario: Optional[str] = None,
    ) -> AjudaConsulta:
        """
        Grava a consulta — inclusive quando encontrou.

        As que nao encontraram dizem o que falta escrever; as que encontraram dizem
        o que mais perguntam. Falha aqui nao deve quebrar a resposta ao usuario, por
        isso quem chama trata a excecao.
        """
        registro = AjudaConsulta(
            pergunta=pergunta.strip(),
            contexto=contexto or None,
            encontrou=resultado is not None,
            conteudo_id=resultado.conteudo_id if resultado else None,
            score=resultado.score if resultado else None,
            origem_busca=resultado.origem if resultado else None,
            usuario=usuario,
        )
        self._s.add(registro)
        self._s.flush()
        return registro
