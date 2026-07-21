"""
Router CRUD para pares Q&A curados (`/api/pares-qa`).

Rotas:
    GET    /api/pares-qa                        Lista pares (filtros + paginacao)
    GET    /api/pares-qa/pendentes-aprovacao     Lista pares nao aprovados (rascunhos)
    GET    /api/pares-qa/similares               Busca por similaridade (deteccao de duplicatas)
    GET    /api/pares-qa/estatisticas-uso        Pares mais usados nas respostas reais
    GET    /api/pares-qa/{id}                   Retorna um par pelo id
    POST   /api/pares-qa                        Cria rascunho (sem embedding)
    PATCH  /api/pares-qa/{id}                   Atualiza par (re-gera embedding se pergunta mudou)
    DELETE /api/pares-qa/{id}                   Soft delete (ativo=False)
    POST   /api/pares-qa/{id}/aprovar           Gera embedding e marca aprovado=True

IMPORTANTE sobre ordem de declaracao: rotas literais (`/pendentes-aprovacao`,
`/similares`, `/estatisticas-uso`) precisam vir ANTES de `/{par_id}` — Starlette
casa `{par_id}` com qualquer segmento de path antes de o FastAPI tentar converter
para `int`, e uma falha de conversao vira 422 em vez de cair pra proxima rota.
Ja aconteceu com `/pendentes-aprovacao` (ver historico do REQ-013, Fase 9).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from database import Database
from fastapi import APIRouter, HTTPException
from models import ParQA, Vector
from pydantic import BaseModel
from sqlalchemy import Float, bindparam, select, text
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pares-qa", tags=["pares-qa"])

_db = Database()


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------


class CriarParQARequest(BaseModel):
    id_externo: Optional[str] = None
    pergunta: str
    resposta: str
    contexto: Optional[str] = None
    tags: Optional[list[str]] = None
    aprovado: bool = False
    criado_por: Optional[str] = None


class AtualizarParQARequest(BaseModel):
    pergunta: Optional[str] = None
    resposta: Optional[str] = None
    contexto: Optional[str] = None
    tags: Optional[list[str]] = None
    aprovado: Optional[bool] = None
    ativo: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_pergunta(pergunta: str) -> str:
    return hashlib.sha256(pergunta.strip().lower().encode()).hexdigest()[:16]


def _resolver_id_externo(id_externo: Optional[str], contexto: Optional[str], pergunta: str) -> str:
    if id_externo:
        return id_externo
    ctx = contexto or "geral"
    return f"qa:{ctx}:{_hash_pergunta(pergunta)}"


async def _gerar_embedding(texto: str) -> list[float]:
    """Gera embedding via provider configurado."""
    from services.embeddings import get_embedding_provider

    provider = get_embedding_provider()
    return await provider.embed_um(texto)


# ---------------------------------------------------------------------------
# GET /api/pares-qa
# ---------------------------------------------------------------------------


@router.get("")
async def listar_pares_qa(
    contexto: Optional[str] = None,
    tag: Optional[str] = None,
    ativo: Optional[bool] = True,
    aprovado: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
):
    """Lista pares Q&A com filtros e paginacao."""
    if page < 1:
        raise HTTPException(status_code=400, detail="page deve ser >= 1")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 200")

    offset = (page - 1) * limit

    with _db.get_session() as session:
        q = session.query(ParQA)
        if ativo is not None:
            q = q.filter(ParQA.ativo == ativo)
        if aprovado is not None:
            q = q.filter(ParQA.aprovado == aprovado)
        if contexto:
            q = q.filter(ParQA.contexto == contexto)
        if tag:
            q = q.filter(ParQA.tags.any(tag))

        total = q.count()
        pares = q.order_by(ParQA.criado_em.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pares": [p.to_dict() for p in pares],
        }


# ---------------------------------------------------------------------------
# Rotas literais (precisam vir antes de /{par_id} — ver nota no topo do arquivo)
# ---------------------------------------------------------------------------


@router.get("/pendentes-aprovacao")
async def listar_pendentes_aprovacao(contexto: Optional[str] = None):
    """Lista pares ativos ainda não aprovados (rascunhos para revisão)."""
    with _db.get_session() as session:
        q = session.query(ParQA).filter(ParQA.ativo, not ParQA.aprovado)
        if contexto:
            q = q.filter(ParQA.contexto == contexto)
        pares = q.order_by(ParQA.criado_em.desc()).all()
        return {"total": len(pares), "pares": [p.to_dict() for p in pares]}


@router.get("/similares")
async def buscar_pares_similares(pergunta: str, top_k: int = 5):
    """
    Busca pares Q&A por similaridade semântica (REQ-013.5) — usado para alertar
    sobre possíveis duplicatas antes de criar um novo par manualmente.

    Só compara contra pares que já têm embedding (aprovados) — rascunhos não
    aprovados não têm embedding ainda (lazy embedding), então não entram nesta
    busca; a checagem de duplicata entre rascunhos fica para uma fase futura.
    """
    pergunta = (pergunta or "").strip()
    if not pergunta:
        raise HTTPException(status_code=400, detail="pergunta é obrigatória")
    if top_k < 1 or top_k > 20:
        raise HTTPException(status_code=400, detail="top_k deve estar entre 1 e 20")

    try:
        vetor = await _gerar_embedding(pergunta)
    except Exception as e:
        logger.warning("[pares_qa] Falha ao gerar embedding para busca de similares: %s", e)
        raise HTTPException(status_code=502, detail=f"Falha ao gerar embedding: {e}")

    dim = len(vetor)
    param = bindparam("q_emb", value=vetor, type_=Vector(dim))
    distancia_expr = ParQA.embedding.op("<=>", return_type=Float())(param)

    with _db.get_session() as session:
        stmt = (
            select(ParQA, distancia_expr.label("distancia"))
            .where(ParQA.ativo.is_(True))
            .where(ParQA.embedding.isnot(None))
            .order_by(distancia_expr)
            .limit(top_k)
        )
        linhas = session.execute(stmt).all()

        candidatos = []
        for par, distancia in linhas:
            d = par.to_dict()
            d["score"] = round(1.0 - float(distancia), 4)
            candidatos.append(d)
    return {"candidatos": candidatos}


@router.get("/estatisticas-uso")
async def estatisticas_uso_pares_qa(top: int = 10, dias: int = 90):
    """
    Pares Q&A mais usados como resposta real (REQ-013.7), derivado de
    `processamentos_mensagem.rag_trechos` — coluna que registra o `id_externo`
    do par quando ele decidiu a resposta (`template_usado='qa_pair'`).
    """
    if top < 1 or top > 100:
        raise HTTPException(status_code=400, detail="top deve estar entre 1 e 100")
    if dias < 1 or dias > 3650:
        raise HTTPException(status_code=400, detail="dias deve estar entre 1 e 3650")

    sql = text(
        """
        SELECT trecho->>'id_externo' AS id_externo, COUNT(*) AS usos
        FROM processamentos_mensagem,
             jsonb_array_elements(rag_trechos) AS trecho
        WHERE template_usado = 'qa_pair'
          AND trecho->>'tipo' = 'qa_pair'
          AND created_at >= now() - make_interval(days => :dias)
        GROUP BY trecho->>'id_externo'
        ORDER BY usos DESC
        LIMIT :top
        """
    )
    with _db.get_session() as session:
        linhas = session.execute(sql, {"dias": dias, "top": top}).all()
        id_externos = [r.id_externo for r in linhas if r.id_externo]
        pares_por_id_externo = {}
        if id_externos:
            pares = session.query(ParQA).filter(ParQA.id_externo.in_(id_externos)).all()
            pares_por_id_externo = {p.id_externo: p.to_dict() for p in pares}

    estatisticas = [
        {
            "id_externo": r.id_externo,
            "usos": r.usos,
            "par": pares_por_id_externo.get(r.id_externo),
        }
        for r in linhas
        if r.id_externo
    ]
    return {"estatisticas": estatisticas}


# ---------------------------------------------------------------------------
# GET /api/pares-qa/{par_id}
# ---------------------------------------------------------------------------


@router.get("/{par_id}")
async def obter_par_qa(par_id: int):
    """Retorna um par Q&A pelo id interno."""
    with _db.get_session() as session:
        par = session.query(ParQA).filter_by(id=par_id).first()
        if not par:
            raise HTTPException(status_code=404, detail="Par Q&A não encontrado")
        return par.to_dict()


# ---------------------------------------------------------------------------
# POST /api/pares-qa
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def criar_par_qa(payload: CriarParQARequest):
    """Cria rascunho de par Q&A sem gerar embedding. Embedding e gerado na aprovacao."""
    pergunta = (payload.pergunta or "").strip()
    resposta = (payload.resposta or "").strip()
    if not pergunta:
        raise HTTPException(status_code=400, detail="pergunta é obrigatória")
    if not resposta:
        raise HTTPException(status_code=400, detail="resposta é obrigatória")

    id_externo = _resolver_id_externo(payload.id_externo, payload.contexto, pergunta)

    with _db.get_session() as session:
        existente = session.query(ParQA).filter_by(id_externo=id_externo).first()
        if existente:
            raise HTTPException(
                status_code=409,
                detail=f"Já existe um par com id_externo='{id_externo}' (id={existente.id})",
            )
        novo = ParQA(
            id_externo=id_externo,
            pergunta=pergunta,
            resposta=resposta,
            contexto=payload.contexto,
            tags=payload.tags or [],
            embedding=None,
            ativo=True,
            aprovado=False,
            criado_por=payload.criado_por,
        )
        session.add(novo)
        session.flush()
        session.refresh(novo)
        logger.info("[pares_qa] Rascunho criado id=%d id_externo=%s", novo.id, novo.id_externo)
        return novo.to_dict()


# ---------------------------------------------------------------------------
# PATCH /api/pares-qa/{par_id}
# ---------------------------------------------------------------------------


@router.patch("/{par_id}")
async def atualizar_par_qa(par_id: int, payload: AtualizarParQARequest):
    """
    Atualiza campos de um par Q&A.
    Re-gera o embedding automaticamente se `pergunta` for alterada.
    """
    with _db.get_session() as session:
        par = session.query(ParQA).filter_by(id=par_id).first()
        if not par:
            raise HTTPException(status_code=404, detail="Par Q&A não encontrado")

        pergunta_nova = (payload.pergunta or "").strip() if payload.pergunta is not None else None
        regenerar_embedding = pergunta_nova is not None and pergunta_nova != par.pergunta

        if regenerar_embedding:
            try:
                novo_embedding = await _gerar_embedding(pergunta_nova)
            except Exception as e:
                logger.warning("[pares_qa] Falha ao re-gerar embedding: %s", e)
                raise HTTPException(status_code=502, detail=f"Falha ao gerar embedding: {e}")
            par.embedding = novo_embedding
            par.pergunta = pergunta_nova

        if payload.resposta is not None:
            par.resposta = payload.resposta.strip()
        if payload.contexto is not None:
            par.contexto = payload.contexto or None
        if payload.tags is not None:
            par.tags = payload.tags
        if payload.aprovado is not None:
            par.aprovado = payload.aprovado
        if payload.ativo is not None:
            par.ativo = payload.ativo

        par.atualizado_em = utc_now()
        session.flush()
        session.refresh(par)
        logger.info(
            "[pares_qa] Atualizado id=%d embedding_regenerado=%s",
            par.id,
            regenerar_embedding,
        )
        return par.to_dict()


# ---------------------------------------------------------------------------
# DELETE /api/pares-qa/{par_id}  (soft delete)
# ---------------------------------------------------------------------------


@router.delete("/{par_id}", status_code=200)
async def desativar_par_qa(par_id: int):
    """Soft delete: marca o par como ativo=False."""
    with _db.get_session() as session:
        par = session.query(ParQA).filter_by(id=par_id).first()
        if not par:
            raise HTTPException(status_code=404, detail="Par Q&A não encontrado")
        if not par.ativo:
            raise HTTPException(status_code=409, detail="Par Q&A já está inativo")
        par.ativo = False
        par.atualizado_em = utc_now()
        session.flush()
        logger.info("[pares_qa] Desativado (soft delete) id=%d", par_id)
        return {"ok": True, "id": par_id, "ativo": False}


# ---------------------------------------------------------------------------
# POST /api/pares-qa/{par_id}/aprovar
# ---------------------------------------------------------------------------


@router.post("/{par_id}/aprovar")
async def aprovar_par_qa(par_id: int):
    """Gera embedding da pergunta e marca o par como aprovado=True."""
    with _db.get_session() as session:
        par = session.query(ParQA).filter_by(id=par_id).first()
        if not par:
            raise HTTPException(status_code=404, detail="Par Q&A não encontrado")
        if par.aprovado:
            raise HTTPException(status_code=409, detail="Par Q&A já está aprovado")
        if not par.ativo:
            raise HTTPException(
                status_code=400,
                detail="Não é possível aprovar um par inativo. Reative-o primeiro.",
            )
        pergunta = par.pergunta

    try:
        embedding = await _gerar_embedding(pergunta)
    except Exception as e:
        logger.warning("[pares_qa] Falha ao gerar embedding na aprovacao: %s", e)
        raise HTTPException(status_code=502, detail=f"Falha ao gerar embedding: {e}")

    with _db.get_session() as session:
        par = session.query(ParQA).filter_by(id=par_id).first()
        par.embedding = embedding
        par.aprovado = True
        par.atualizado_em = utc_now()
        session.flush()
        session.refresh(par)
        logger.info("[pares_qa] Aprovado id=%d id_externo=%s", par.id, par.id_externo)
        return par.to_dict()
