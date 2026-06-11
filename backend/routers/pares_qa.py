"""
Router CRUD para pares Q&A curados (`/api/pares-qa`).

Rotas:
    GET    /api/pares-qa                        Lista pares (filtros + paginacao)
    GET    /api/pares-qa/pendentes-aprovacao     Lista pares nao aprovados (rascunhos)
    GET    /api/pares-qa/{id}                   Retorna um par pelo id
    POST   /api/pares-qa                        Cria rascunho (sem embedding)
    PATCH  /api/pares-qa/{id}                   Atualiza par (re-gera embedding se pergunta mudou)
    DELETE /api/pares-qa/{id}                   Soft delete (ativo=False)
    POST   /api/pares-qa/{id}/aprovar           Gera embedding e marca aprovado=True
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from database import Database
from fastapi import APIRouter, HTTPException
from models import ParQA
from pydantic import BaseModel

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

        total = q.count()
        pares = q.order_by(ParQA.criado_em.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pares": [p.to_dict() for p in pares],
        }


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


@router.get("/pendentes-aprovacao")
async def listar_pendentes_aprovacao(contexto: Optional[str] = None):
    """Lista pares ativos ainda não aprovados (rascunhos para revisão)."""
    with _db.get_session() as session:
        q = session.query(ParQA).filter(ParQA.ativo, not ParQA.aprovado)
        if contexto:
            q = q.filter(ParQA.contexto == contexto)
        pares = q.order_by(ParQA.criado_em.desc()).all()
        return {"total": len(pares), "pares": [p.to_dict() for p in pares]}


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

        par.atualizado_em = datetime.utcnow()
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
        par.atualizado_em = datetime.utcnow()
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
        par.atualizado_em = datetime.utcnow()
        session.flush()
        session.refresh(par)
        logger.info("[pares_qa] Aprovado id=%d id_externo=%s", par.id, par.id_externo)
        return par.to_dict()
