"""
Router do FAQ de ajuda contextual do painel (`/api/ajuda`).

Consulta (usado pelo botao de ajuda em cada tela):
    POST   /api/ajuda/perguntar              Busca resposta para uma pergunta
    GET    /api/ajuda/sugestoes              Perguntas sugeridas para a tela

Administracao (tela "Base de Ajuda"):
    GET    /api/ajuda/contextos              Catalogo de telas
    GET    /api/ajuda/conteudos              Lista conteudos (filtros)
    POST   /api/ajuda/conteudos              Cria
    PATCH  /api/ajuda/conteudos/{id}         Atualiza
    DELETE /api/ajuda/conteudos/{id}         Soft delete (ativo=False)
    POST   /api/ajuda/conteudos/reindexar    Gera embedding dos que estao sem
    GET    /api/ajuda/consultas              Historico de consultas (lacunas)

IMPORTANTE sobre ordem de declaracao: rotas literais (`/conteudos/reindexar`)
precisam vir ANTES de `/conteudos/{conteudo_id}` — Starlette casa `{conteudo_id}`
com qualquer segmento e a falha de conversao para `int` viraria 422 em vez de cair
na proxima rota. Mesmo cuidado documentado em `routers/pares_qa.py` e no CLAUDE.md.

Este modulo nao conversa com o cliente: o conteudo daqui nunca entra numa resposta
de WhatsApp (base separada de `pares_qa` justamente para isso).
"""

from __future__ import annotations

import logging
from typing import Optional

from config import settings
from database import Database
from fastapi import APIRouter, HTTPException, Request
from models import AjudaConsulta, AjudaConteudo, AjudaContexto
from pydantic import BaseModel
from services.ajuda import AjudaService
from sqlalchemy import func, select
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ajuda", tags=["ajuda"])

_db = Database()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PerguntarRequest(BaseModel):
    pergunta: str
    contexto: Optional[str] = None


class CriarConteudoRequest(BaseModel):
    pergunta: str
    resposta: str
    contexto_chave: Optional[str] = None
    tags: Optional[list[str]] = None
    prioridade: int = 0


class AtualizarConteudoRequest(BaseModel):
    pergunta: Optional[str] = None
    resposta: Optional[str] = None
    contexto_chave: Optional[str] = None
    tags: Optional[list[str]] = None
    prioridade: Optional[int] = None
    ativo: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _usuario_de(request: Request) -> Optional[str]:
    """Nome do usuario logado, quando houver (o gate pode estar desligado em dev)."""
    return getattr(request.state, "usuario_nome", None)


def _resolver_contexto_id(sessao, chave: Optional[str]) -> Optional[int]:
    """Traduz a chave do contexto para id, validando contra o catalogo.

    Chave desconhecida e erro explicito (400) em vez de virar conteudo global
    silenciosamente: um typo aqui faria o conteudo nunca aparecer na tela certa.
    """
    if not chave:
        return None
    contexto = sessao.query(AjudaContexto).filter_by(chave=chave).first()
    if not contexto:
        raise HTTPException(
            status_code=400,
            detail=f"Contexto '{chave}' nao existe. Consulte GET /api/ajuda/contextos.",
        )
    return contexto.id


async def _gerar_embedding(texto: str) -> Optional[list[float]]:
    """Embedding da pergunta, ou None se o provider falhar.

    Best-effort de proposito: sem embedding o conteudo ainda e encontravel por
    full-text, e bloquear o cadastro porque a API de embeddings esta fora seria
    pior que salvar com busca semantica degradada. `POST /conteudos/reindexar`
    preenche os que ficaram pendentes.
    """
    try:
        from services.embeddings import get_embedding_provider

        provider = get_embedding_provider()
        return await provider.embed_um(texto)
    except Exception as exc:
        logger.warning("[ajuda] embedding nao gerado (%s); conteudo fica so com full-text", exc)
        return None


# ---------------------------------------------------------------------------
# Consulta
# ---------------------------------------------------------------------------


@router.post("/perguntar")
async def perguntar(payload: PerguntarRequest, request: Request):
    """Responde uma pergunta de ajuda no contexto da tela atual."""
    pergunta = (payload.pergunta or "").strip()
    if not pergunta:
        raise HTTPException(status_code=400, detail="pergunta e obrigatoria")
    if not settings.AJUDA_ENABLED:
        return {"encontrou": False, "resultados": [], "motivo": "ajuda desabilitada"}

    with _db.get_session() as sessao:
        servico = AjudaService(sessao)
        resultados = await servico.buscar(pergunta, payload.contexto)
        melhor = resultados[0] if resultados else None

        try:
            servico.registrar_consulta(
                pergunta=pergunta,
                contexto=payload.contexto,
                resultado=melhor,
                usuario=_usuario_de(request),
            )
        except Exception as exc:
            # Auditoria e secundaria: nao pode impedir a resposta de chegar ao usuario.
            logger.warning("[ajuda] falha ao registrar consulta: %s", exc)

        return {
            "encontrou": melhor is not None,
            "resultados": [r.to_dict() for r in resultados],
        }


@router.get("/sugestoes")
async def sugestoes(contexto: Optional[str] = None, limite: int = 8):
    """Perguntas sugeridas para exibir sem o usuario digitar nada."""
    if limite < 1 or limite > 50:
        raise HTTPException(status_code=400, detail="limite deve estar entre 1 e 50")
    with _db.get_session() as sessao:
        itens = AjudaService(sessao).sugestoes(contexto, limite=limite)
        return {"sugestoes": [i.to_dict() for i in itens]}


# ---------------------------------------------------------------------------
# Administracao
# ---------------------------------------------------------------------------


@router.get("/contextos")
async def listar_contextos(apenas_ativos: bool = True):
    """Catalogo de telas que podem ter ajuda."""
    with _db.get_session() as sessao:
        q = sessao.query(AjudaContexto)
        if apenas_ativos:
            q = q.filter(AjudaContexto.ativo.is_(True))
        contextos = q.order_by(AjudaContexto.chave).all()

        # Contagem de conteudos ativos por contexto — a tela usa para mostrar
        # quais telas ainda nao tem nenhuma ajuda cadastrada.
        contagens = dict(
            sessao.execute(
                select(AjudaConteudo.contexto_id, func.count(AjudaConteudo.id))
                .where(AjudaConteudo.ativo.is_(True))
                .group_by(AjudaConteudo.contexto_id)
            ).all()
        )
        itens = []
        for c in contextos:
            d = c.to_dict()
            d["total_conteudos"] = contagens.get(c.id, 0)
            itens.append(d)
        return {"contextos": itens, "globais": contagens.get(None, 0)}


@router.get("/conteudos")
async def listar_conteudos(
    contexto: Optional[str] = None,
    ativo: Optional[bool] = True,
    q: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """Lista conteudos de ajuda com filtros e paginacao."""
    if page < 1:
        raise HTTPException(status_code=400, detail="page deve ser >= 1")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 200")

    with _db.get_session() as sessao:
        consulta = sessao.query(AjudaConteudo).outerjoin(
            AjudaContexto, AjudaConteudo.contexto_id == AjudaContexto.id
        )
        if ativo is not None:
            consulta = consulta.filter(AjudaConteudo.ativo.is_(ativo))
        if contexto == "__global__":
            consulta = consulta.filter(AjudaConteudo.contexto_id.is_(None))
        elif contexto:
            consulta = consulta.filter(AjudaContexto.chave == contexto)
        if q and q.strip():
            padrao = f"%{q.strip()}%"
            consulta = consulta.filter(
                AjudaConteudo.pergunta.ilike(padrao) | AjudaConteudo.resposta.ilike(padrao)
            )

        total = consulta.count()
        itens = (
            consulta.order_by(AjudaConteudo.prioridade.desc(), AjudaConteudo.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "conteudos": [i.to_dict() for i in itens],
        }


@router.post("/conteudos", status_code=201)
async def criar_conteudo(payload: CriarConteudoRequest, request: Request):
    """Cria um conteudo de ajuda (ja ativo; embedding best-effort)."""
    pergunta = (payload.pergunta or "").strip()
    resposta = (payload.resposta or "").strip()
    if not pergunta:
        raise HTTPException(status_code=400, detail="pergunta e obrigatoria")
    if not resposta:
        raise HTTPException(status_code=400, detail="resposta e obrigatoria")

    embedding = await _gerar_embedding(pergunta)

    with _db.get_session() as sessao:
        contexto_id = _resolver_contexto_id(sessao, payload.contexto_chave)
        novo = AjudaConteudo(
            contexto_id=contexto_id,
            pergunta=pergunta,
            resposta=resposta,
            tags=payload.tags or [],
            prioridade=payload.prioridade or 0,
            ativo=True,
            embedding=embedding,
            criado_por=_usuario_de(request),
        )
        sessao.add(novo)
        sessao.flush()
        sessao.refresh(novo)
        logger.info("[ajuda] conteudo criado id=%d contexto=%s", novo.id, payload.contexto_chave)
        return novo.to_dict()


# Rota literal antes da dinamica — ver nota no topo do arquivo.
@router.post("/conteudos/reindexar")
async def reindexar_conteudos():
    """Gera embedding para os conteudos ativos que estao sem.

    Serve para recuperar de um periodo em que a API de embeddings esteve fora.
    """
    with _db.get_session() as sessao:
        pendentes = [
            (c.id, c.pergunta)
            for c in sessao.query(AjudaConteudo)
            .filter(AjudaConteudo.ativo.is_(True), AjudaConteudo.embedding.is_(None))
            .all()
        ]

    if not pendentes:
        return {"pendentes": 0, "indexados": 0, "falhas": 0}

    indexados, falhas = 0, 0
    for conteudo_id, pergunta in pendentes:
        vetor = await _gerar_embedding(pergunta)
        if vetor is None:
            falhas += 1
            continue
        with _db.get_session() as sessao:
            item = sessao.query(AjudaConteudo).filter_by(id=conteudo_id).first()
            if item:
                item.embedding = vetor
                item.updated_at = utc_now()
                indexados += 1

    logger.info("[ajuda] reindexacao: %d indexado(s), %d falha(s)", indexados, falhas)
    return {"pendentes": len(pendentes), "indexados": indexados, "falhas": falhas}


@router.patch("/conteudos/{conteudo_id}")
async def atualizar_conteudo(conteudo_id: int, payload: AtualizarConteudoRequest):
    """Atualiza um conteudo. Alterar a pergunta re-gera o embedding."""
    with _db.get_session() as sessao:
        item = sessao.query(AjudaConteudo).filter_by(id=conteudo_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Conteudo de ajuda nao encontrado")
        pergunta_atual = item.pergunta

    pergunta_nova = (payload.pergunta or "").strip() if payload.pergunta is not None else None
    regerar = bool(pergunta_nova) and pergunta_nova != pergunta_atual
    embedding = await _gerar_embedding(pergunta_nova) if regerar else None

    with _db.get_session() as sessao:
        item = sessao.query(AjudaConteudo).filter_by(id=conteudo_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Conteudo de ajuda nao encontrado")

        if regerar:
            item.pergunta = pergunta_nova
            item.embedding = embedding
        if payload.resposta is not None:
            item.resposta = payload.resposta.strip()
        if payload.contexto_chave is not None:
            item.contexto_id = _resolver_contexto_id(sessao, payload.contexto_chave or None)
        if payload.tags is not None:
            item.tags = payload.tags
        if payload.prioridade is not None:
            item.prioridade = payload.prioridade
        if payload.ativo is not None:
            item.ativo = payload.ativo

        item.updated_at = utc_now()
        sessao.flush()
        sessao.refresh(item)
        logger.info("[ajuda] conteudo %d atualizado (embedding_regerado=%s)", conteudo_id, regerar)
        return item.to_dict()


@router.delete("/conteudos/{conteudo_id}")
async def desativar_conteudo(conteudo_id: int):
    """Soft delete: mantem o registro para nao perder o historico de consultas."""
    with _db.get_session() as sessao:
        item = sessao.query(AjudaConteudo).filter_by(id=conteudo_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Conteudo de ajuda nao encontrado")
        if not item.ativo:
            raise HTTPException(status_code=409, detail="Conteudo ja esta inativo")
        item.ativo = False
        item.updated_at = utc_now()
        sessao.flush()
        return {"ok": True, "id": conteudo_id, "ativo": False}


@router.get("/consultas")
async def listar_consultas(
    encontrou: Optional[bool] = None,
    contexto: Optional[str] = None,
    limit: int = 100,
):
    """
    Historico de consultas. `encontrou=false` lista as lacunas — as perguntas que
    os usuarios fizeram e a base nao soube responder, que e a pauta de conteudo.

    Tambem devolve `agrupadas`: as perguntas repetidas, para priorizar o que
    escrever primeiro em vez de olhar linha por linha.
    """
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 500")

    with _db.get_session() as sessao:
        consulta = sessao.query(AjudaConsulta)
        if encontrou is not None:
            consulta = consulta.filter(AjudaConsulta.encontrou.is_(encontrou))
        if contexto:
            consulta = consulta.filter(AjudaConsulta.contexto == contexto)
        total = consulta.count()
        itens = consulta.order_by(AjudaConsulta.created_at.desc()).limit(limit).all()

        agrupamento = select(
            func.lower(AjudaConsulta.pergunta).label("pergunta"),
            AjudaConsulta.contexto,
            func.count(AjudaConsulta.id).label("vezes"),
        )
        if encontrou is not None:
            agrupamento = agrupamento.where(AjudaConsulta.encontrou.is_(encontrou))
        if contexto:
            agrupamento = agrupamento.where(AjudaConsulta.contexto == contexto)
        agrupamento = (
            agrupamento.group_by(func.lower(AjudaConsulta.pergunta), AjudaConsulta.contexto)
            .order_by(func.count(AjudaConsulta.id).desc())
            .limit(20)
        )

        return {
            "total": total,
            "consultas": [i.to_dict() for i in itens],
            "agrupadas": [
                {"pergunta": r.pergunta, "contexto": r.contexto, "vezes": r.vezes}
                for r in sessao.execute(agrupamento).all()
            ],
        }
