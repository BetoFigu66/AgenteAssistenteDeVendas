"""
Assistente de Vendas via WhatsApp com IA - Backend FastAPI
"""

import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from config import settings
from database import Database
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from models import (
    Atendimento,
    CategoriaReport,
    Contato,
    Empresa,
    EventoAtendimento,
    HistoricoConfiguracao,
    HistoricoModoExecucao,
    HistoricoStatusReport,
    Mensagem,
    ModoExecucao,
    ModoOperacao,
    MotivoEncerramento,
    MotivoEscalonamento,
    OrigemMensagem,
    Parametro,
    Pessoa,
    ProcessamentoMensagem,
    ReportProblema,
    SeveridadeReport,
    StatusAtendimento,
    StatusReport,
    TipoDocumento,
    TipoEventoAtendimento,
    User,
)
from pydantic import BaseModel
from routers.pares_qa import router as pares_qa_router
from services import atendimentos as atendimentos_svc
from services import auth as auth_svc
from services.conversacao.campos_pendentes import campos_pendentes
from services.cpf.validacao import mascarar_cpf
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import identificar_por_telefone, normalizar_telefone
from services.llm import get_llm_provider
from services.parametro_service import MODO_EXECUCAO, ParametroService
from services.processador import ProcessadorMensagem
from sqlalchemy import func
from sqlalchemy import or_ as sa_or
from starlette.middleware.sessions import SessionMiddleware
from utils.datetime_utils import serialize_utc_datetime, utc_now


def _configurar_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)s [%(name)s] %(message)s")
    for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)


_configurar_logging()
logger = logging.getLogger(__name__)

db: Database = None
processador: ProcessadorMensagem = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    global db, processador
    logger.info("Iniciando aplicação...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    db = Database()
    logger.info("Banco de dados inicializado com SQLAlchemy")

    # Executa migrations pendentes automaticamente
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations Alembic aplicadas com sucesso (upgrade head)")
    except Exception as e:
        logger.warning(f"Não foi possível aplicar migrations automaticamente: {e}")

    # Inicializa o cérebro (LLM + processador)
    try:
        llm = get_llm_provider()
        logger.info(f"LLM Provider inicializado: {llm.nome} ({settings.LLM_MODEL})")
    except Exception as e:
        logger.warning(f"LLM não disponível (seguindo apenas com regras): {e}")
        llm = None

    processador = ProcessadorMensagem(llm=llm)
    logger.info("Processador de mensagens inicializado")
    yield
    logger.info("Encerrando aplicação...")


app = FastAPI(
    title="Assistente de Vendas API", description="API para integração com WhatsApp via Twilio",
    version="0.1.0", lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pares_qa_router)


# ============================================================================
# Autenticação (REQ-010, Fase 4) — gate mínimo por sessão (cookie assinado)
# ============================================================================

# Caminhos que não exigem sessão: webhook (validação própria do Twilio, fora
# de escopo desta fase), health check, e o próprio login (senão ninguém
# consegue logar).
_CAMINHOS_PUBLICOS = {"/health", "/webhook", "/api/auth/login"}


@app.middleware("http")
async def gate_autenticacao(request: Request, call_next):
    """Bloqueia qualquer `/api/*` sem sessão válida (REQ-010.1/010.2).

    Resolve o `User` uma única vez aqui e guarda em `request.state.usuario`
    para os endpoints que precisam da identidade não repetirem a consulta.
    """
    path = request.url.path
    if request.method == "OPTIONS" or path in _CAMINHOS_PUBLICOS or not path.startswith("/api/"):
        return await call_next(request)

    user_id = request.session.get("user_id")
    if user_id is None:
        return JSONResponse(status_code=401, content={"detail": "Não autenticado"})

    with db.get_session() as session:
        usuario = session.query(User).filter_by(id=user_id).first()
        if not usuario:
            request.session.clear()
            return JSONResponse(status_code=401, content={"detail": "Não autenticado"})
        request.state.usuario = usuario.to_dict()
        request.state.usuario_id = usuario.id
        request.state.usuario_nome = usuario.nome

    return await call_next(request)


# `add_middleware()` insere no INÍCIO da lista, e a pilha final é montada em
# ordem reversa (quem é adicionado por último roda primeiro) — por isso o
# SessionMiddleware só é registrado aqui, depois do gate: precisa rodar ANTES
# do gate (pra `request.session` já existir quando o gate ler), então tem que
# ser o middleware mais "externo", ou seja, o último a ser adicionado.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    max_age=settings.SESSION_MAX_AGE_SEGUNDOS,
)


def usuario_id_atual(request: Request) -> int:
    """Dependency com o id do usuário logado — já resolvido pelo middleware,
    sem query adicional. Endpoints que precisam do objeto `User` completo devem
    buscá-lo na própria sessão do endpoint (evita `DetachedInstanceError`)."""
    return request.state.usuario_id


def usuario_nome_atual(request: Request) -> str:
    return request.state.usuario_nome


# ============================================================================
# Handlers de Exceção Globais - SEMPRE logar stack-trace para diagnóstico
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros 422 - loga stack-trace completa para diagnóstico."""
    stack_trace = traceback.format_exc()
    logger.error(f"[ERRO 422] ValidationError em {request.method} {request.url}")
    logger.error(f"[ERRO 422] Detalhes: {exc.errors()}")
    logger.error(f"[ERRO 422] Stack trace:\n{stack_trace}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "message": "Erro de validação nos dados enviados",
            "type": "validation_error"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global - loga stack-trace completa de qualquer exceção não tratada."""
    stack_trace = traceback.format_exc()
    logger.error(f"[ERRO 500] Exceção não tratada em {request.method} {request.url}")
    logger.error(f"[ERRO 500] Tipo: {type(exc).__name__}")
    logger.error(f"[ERRO 500] Mensagem: {str(exc)}")
    logger.error(f"[ERRO 500] Stack trace:\n{stack_trace}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor",
            "message": str(exc) if settings.DEBUG else "Erro interno do servidor",
            "type": "internal_error",
        },
    )


RESPOSTA_FALLBACK = "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?"


async def _processar_via_cerebro(telefone: str, conteudo: str, message_sid: Optional[str]) -> str:
    """Executa o processador dentro de uma sessão de banco."""
    with db.get_session() as session:
        resultado = await processador.processar(
            db=session,
            telefone=telefone,
            conteudo=conteudo,
            message_sid=message_sid,
        )
    return resultado.resposta


@app.post("/webhook", response_class=PlainTextResponse)
async def webhook_twilio(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: Optional[str] = Form(None),
    AccountSid: Optional[str] = Form(None),
    To: Optional[str] = Form(None),
    NumMedia: Optional[str] = Form("0"),
):
    """
    Webhook para receber mensagens do Twilio WhatsApp.

    Processa a mensagem pelo cérebro (identificação + classificação + geração)
    e retorna a resposta em formato TwiML.
    """
    telefone = From.replace("whatsapp:", "")

    try:
        resposta = await _processar_via_cerebro(telefone, Body, MessageSid)
    except Exception as e:
        logger.exception(f"Erro ao processar webhook: {e}")
        resposta = RESPOSTA_FALLBACK

    # Se não há resposta (ex.: atendimento em modo HUMANO), devolve TwiML vazio
    # — o Twilio não envia nada para o cliente e o operador responderá pela UI.
    if not resposta:
        twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response></Response>"""
    else:
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{resposta}</Message>
</Response>"""

    return PlainTextResponse(content=twiml_response, media_type="application/xml")


class MensagemRequest(BaseModel):
    telefone: str
    mensagem: str


class MensagemResponse(BaseModel):
    telefone: str
    conteudo: str
    origem: str
    timestamp: str


@app.post("/api/mensagem")
async def enviar_mensagem(request: MensagemRequest):
    """
    Endpoint para enviar mensagem via interface web.
    Processa pelo cérebro completo (identificação + classificação + resposta).
    """
    try:
        resposta = await _processar_via_cerebro(
            telefone=request.telefone,
            conteudo=request.mensagem,
            message_sid=None,
        )
    except Exception as e:
        logger.exception(f"Erro ao processar mensagem: {e}")
        resposta = RESPOSTA_FALLBACK

    return {
        "status": "ok",
        "resposta": resposta,
    }


@app.get("/api/historico/{telefone}")
async def obter_historico(
    telefone: str,
    limit: int = 200,
    offset: int = 0,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    status: Optional[str] = None,
):
    """
    Retorna o histórico de mensagens para um número de telefone.

    `limit`/`offset` (REQ-010, Fase 4) evitam carregar uma conversa inteira de
    uma vez só — default de 200 preserva o comportamento atual para qualquer
    conversa de teste (bem menor que isso).

    `data_inicio`/`data_fim`/`status` (REQ-005, Fase 6) filtram por período e por
    status do atendimento vinculado — destrava o filtro de período pendente na
    Fase 4 (Painel Administrativo).
    """
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset deve ser >= 0")
    if status is not None:
        try:
            StatusAtendimento(status)
        except ValueError:
            valores = [s.value for s in StatusAtendimento]
            raise HTTPException(status_code=400, detail=f"status inválido: '{status}'. Aceitos: {valores}")
    mensagens = db.obter_historico(
        telefone,
        limit=limit,
        offset=offset,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status_atendimento=status,
    )
    return {"telefone": telefone, "mensagens": mensagens}


@app.get("/api/telefones")
async def listar_telefones():
    """
    Lista todos os telefones com histórico.
    """
    telefones = db.listar_telefones()
    return {"telefones": telefones}


@app.delete("/api/dev/telefones/{telefone}")
async def apagar_dados_dev_telefone(telefone: str):
    """
    Apaga todos os dados de teste vinculados a um telefone (somente DEBUG=True).

    Remove: reports, mensagens, processamentos, orçamentos, itens de atendimento,
    atendimentos e contato. Não remove empresa nem pessoa.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Endpoint disponível apenas com DEBUG=True no backend.",
        )

    try:
        with db.get_session() as session:
            resultado = apagar_dados_telefone(session, telefone)
    except Exception as e:
        logger.exception("Erro ao apagar dados do telefone %s: %s", telefone, e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    total = sum(resultado["removidos"].values())
    if total == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum dado encontrado para o telefone {telefone}.",
        )

    logger.warning(
        "[DEV] Dados apagados telefone=%s removidos=%s",
        resultado["telefone_normalizado"],
        resultado["removidos"],
    )
    return {"status": "ok", **resultado}


STATUS_ATENDIMENTO_ATIVOS = [StatusAtendimento.ATIVO.value]


@app.get("/api/conversa/{telefone}")
async def obter_dados_conversa(telefone: str):
    """
    Retorna dados consolidados de uma conversa (telefone) para exibir no header.

    Inclui: contato, empresa OU pessoa (PJ/PF — REQ-010, Fase 4) e atendimento
    ativo (quando identificados). CPF nunca é devolvido completo, só mascarado
    (`mascarar_cpf`). Badge de restrição financeira fica de fora nesta fase —
    depende da Fase 16 (REQ-015) ter uma consulta de crédito real habilitada.
    """
    tel_norm = normalizar_telefone(telefone)

    with db.get_session() as session:
        ident = identificar_por_telefone(session, tel_norm)

        contato = ident.contato
        empresa = ident.empresa

        atendimento = None
        if contato:
            atendimento = (
                session.query(Atendimento)
                .filter(Atendimento.contato_id == contato.id)
                .filter(Atendimento.status.in_(STATUS_ATENDIMENTO_ATIVOS))
                .order_by(Atendimento.created_at.desc())
                .first()
            )

        pessoa = None
        if (
            atendimento
            and not empresa
            and atendimento.tipo_documento == TipoDocumento.CPF
            and atendimento.pessoa_id
        ):
            pessoa = session.query(Pessoa).filter_by(id=atendimento.pessoa_id).first()

        return {
            "telefone": telefone,
            "status_identificacao": ident.status.value,
            "contato": {
                "id": contato.id,
                "nome": contato.nome,
                "email": contato.email,
                "cargo": contato.cargo,
            }
            if contato
            else None,
            "empresa": {
                "id": empresa.id,
                "cnpj": empresa.cnpj,
                "nome": empresa.nome,
                "fantasia": empresa.fantasia,
            }
            if empresa
            else None,
            "pessoa": {
                "id": pessoa.id,
                "nome": pessoa.nome,
                "cpf_mascarado": mascarar_cpf(pessoa.cpf),
            }
            if pessoa
            else None,
            "atendimento": {
                "id": atendimento.id,
                "numero_atendimento_cliente": atendimento.numero_atendimento_cliente,
                "titulo": atendimento.titulo,
                "status": atendimento.status.value if atendimento.status else None,
                "modo_operacao": (atendimento.modo_operacao.value if atendimento.modo_operacao else None),
                "fase": atendimento.fase.value if atendimento.fase else None,
            }
            if atendimento
            else None,
        }


@app.get("/api/empresas/{empresa_id}")
async def obter_empresa(empresa_id: int):
    """Retorna detalhes completos de uma empresa."""
    with db.get_session() as session:
        empresa = session.query(Empresa).filter_by(id=empresa_id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa.to_dict()


# =============================================================================
# Rotas de Atendimento - ORDEM IMPORTA: rotas estáticas ANTES de rotas dinâmicas
# =============================================================================


@app.get("/api/atendimentos/ativas")
async def listar_atendimentos_ativos(
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """
    Lista atendimentos ordenados pela quantidade de mensagens pendentes de
    aprovação (maior primeiro).

    Args (REQ-010, Fase 4 — filtro/paginação; filtro por período fica pendente
    até a Fase 6/REQ-005):
        status: "ativo" (default, preserva o comportamento anterior) | "encerrado" | "todos".
        q: busca livre por telefone, nome do contato ou nome/fantasia da empresa.
        page/limit: paginação (mesmo padrão de `routers/pares_qa.py`).

    Retorna: id, status, modo_operacao, fase, telefone, nome_contato, empresa_nome,
    mensagens_pendentes.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="page deve ser >= 1")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 200")

    status_norm = (status or "ativo").strip().lower()
    if status_norm not in ("ativo", "encerrado", "todos"):
        raise HTTPException(status_code=400, detail="status deve ser 'ativo', 'encerrado' ou 'todos'")

    with db.get_session() as session:
        # Subquery: contagem de mensagens pendentes por negociação
        pendentes_expr = func.count(Mensagem.id).label("pendentes")
        subq = (
            session.query(
                Mensagem.atendimento_id.label("neg_id"),
                pendentes_expr,
            )
            .filter(Mensagem.origem == OrigemMensagem.SYSTEM)
            .filter(Mensagem.aprovador_id.is_(None))
            .filter(Mensagem.atendimento_id.isnot(None))
            .group_by(Mensagem.atendimento_id)
            .subquery()
        )

        stmt = (
            session.query(Atendimento, Contato, Empresa, subq.c.pendentes)
            .join(Contato, Contato.id == Atendimento.contato_id)
            .outerjoin(Empresa, Empresa.id == Atendimento.empresa_id)
            .outerjoin(subq, subq.c.neg_id == Atendimento.id)
        )

        if status_norm == "ativo":
            stmt = stmt.filter(Atendimento.status.in_(STATUS_ATENDIMENTO_ATIVOS))
        elif status_norm == "encerrado":
            stmt = stmt.filter(Atendimento.status == StatusAtendimento.ENCERRADO)
        # "todos" não filtra por status

        if q and q.strip():
            termo = f"%{q.strip()}%"
            stmt = stmt.filter(
                sa_or(
                    Contato.telefone.ilike(termo),
                    Contato.nome.ilike(termo),
                    Empresa.nome.ilike(termo),
                    Empresa.fantasia.ilike(termo),
                )
            )

        total = stmt.count()

        stmt = stmt.order_by(
            func.coalesce(subq.c.pendentes, 0).desc(),
            func.coalesce(Atendimento.ultima_mensagem_at, Atendimento.updated_at).desc(),
        ).offset((page - 1) * limit).limit(limit)

        resultado = []
        for atendimento, contato, empresa, pendentes in stmt.all():
            resultado.append(
                {
                    "id": atendimento.id,
                    "numero_atendimento_cliente": atendimento.numero_atendimento_cliente,
                    "status": atendimento.status.value if atendimento.status else None,
                    "modo_operacao": (atendimento.modo_operacao.value if atendimento.modo_operacao else None),
                    "motivo_escalonamento": atendimento.motivo_escalonamento,
                    "fase": atendimento.fase.value if atendimento.fase else None,
                    "titulo": atendimento.titulo,
                    "telefone": contato.telefone,
                    "nome_contato": contato.nome,
                    "empresa_id": empresa.id if empresa else None,
                    "empresa_nome": (empresa.fantasia or empresa.nome) if empresa else None,
                    "mensagens_pendentes": int(pendentes or 0),
                    "updated_at": serialize_utc_datetime(atendimento.updated_at),
                    "ultima_mensagem_at": serialize_utc_datetime(atendimento.ultima_mensagem_at),
                }
            )
        return {"total": total, "page": page, "limit": limit, "atendimentos": resultado}


@app.get("/api/atendimentos/{atendimento_id}")
async def obter_atendimento(atendimento_id: int):
    """Retorna detalhes completos de um atendimento, incluindo itens, infos e orçamentos."""
    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")

        contato = atendimento.contato
        empresa = atendimento.empresa

        return {
            **atendimento.to_dict(),
            "contato": contato.to_dict() if contato else None,
            "empresa": {
                "id": empresa.id,
                "cnpj": empresa.cnpj,
                "nome": empresa.nome,
            }
            if empresa
            else None,
            "itens": [item.to_dict() for item in atendimento.itens],
            "informacoes": [info.to_dict() for info in atendimento.informacoes],
            "orcamentos": [orc.to_dict() for orc in atendimento.orcamentos],
        }


@app.get("/api/atendimentos/{atendimento_id}/campos-pendentes")
async def obter_campos_pendentes(atendimento_id: int):
    """REQ-010, Fase 4: expõe `campos_pendentes()` (services/conversacao) — hoje
    só existia indiretamente via `AtendimentoInfo.pendente` dentro do modal de
    detalhes."""
    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")

        pendentes = campos_pendentes(atendimento)
        return {
            "campos_pendentes": [
                {
                    "id_catalogo": c.id_catalogo,
                    "chave": c.chave,
                    "pergunta": c.pergunta,
                    "ordem": c.ordem,
                }
                for c in pendentes
            ]
        }


@app.get("/api/atendimentos/{atendimento_id}/eventos")
async def obter_eventos_atendimento(atendimento_id: int, limit: int = 100):
    """REQ-005, Fase 6: timeline de eventos auditáveis do atendimento (criação,
    encerramento, reabertura, escalonamento, mudanças de fase/modo de operação),
    mais recentes primeiro."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 500")
    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")

        eventos = (
            session.query(EventoAtendimento)
            .filter_by(atendimento_id=atendimento_id)
            .order_by(EventoAtendimento.timestamp.desc())
            .limit(limit)
            .all()
        )
        return {"atendimento_id": atendimento_id, "eventos": [evento.to_dict() for evento in eventos]}


class AlterarModoRequest(BaseModel):
    modo_operacao: str  # "agente" | "humano"


@app.patch("/api/atendimentos/{atendimento_id}/modo-operacao")
async def alterar_modo_operacao(
    atendimento_id: int,
    payload: AlterarModoRequest,
    ator_nome: str = Depends(usuario_nome_atual),
):
    """
    Alterna o modo de operação de um atendimento entre AGENTE e HUMANO.

    - AGENTE: sistema gera respostas automáticas.
    - HUMANO: sistema só registra mensagens recebidas; operador responde pela UI.
    """
    try:
        novo_modo = ModoOperacao(payload.modo_operacao)
    except ValueError:
        valores = [m.value for m in ModoOperacao]
        raise HTTPException(
            status_code=400,
            detail=f"modo_operacao inválido: '{payload.modo_operacao}'. Aceitos: {valores}",
        )

    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")
        if novo_modo == ModoOperacao.HUMANO:
            # REQ-004.3: takeover manual pelo vendedor recebe o mesmo tratamento de um
            # escalonamento (motivo/timestamp/resumo via helper central da Fase 5).
            await processador._escalar_atendimento(
                session, atendimento, MotivoEscalonamento.MANUAL_VENDEDOR, ator=ator_nome
            )
        else:
            modo_anterior = atendimento.modo_operacao.value
            atendimento.modo_operacao = novo_modo
            session.flush()
            atendimentos_svc.registrar_evento_atendimento(
                session,
                atendimento,
                tipo=TipoEventoAtendimento.MODO_OPERACAO_ALTERADO,
                ator=ator_nome,
                estado_anterior=modo_anterior,
                estado_novo=novo_modo.value,
                motivo="Retomada manual do modo agente pelo vendedor",
            )
        session.refresh(atendimento)
        logger.info(
            f"[ModoOperacao] Atendimento {atendimento.id} alterado para modo={novo_modo.value} por {ator_nome}"
        )
        return atendimento.to_dict()


class EncerrarAtendimentoRequest(BaseModel):
    justificativa: Optional[str] = None


@app.post("/api/atendimentos/{atendimento_id}/encerrar")
async def encerrar_atendimento_manual(
    atendimento_id: int,
    payload: EncerrarAtendimentoRequest,
    ator: str = Depends(usuario_nome_atual),
):
    """Encerramento manual pelo vendedor (REQ-016.4/016.8, motivo=manual_vendedor)."""
    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")
        if atendimento.status == StatusAtendimento.ENCERRADO:
            raise HTTPException(status_code=400, detail="Atendimento já está encerrado")

        atendimentos_svc.encerrar_atendimento(
            session, atendimento, motivo=MotivoEncerramento.MANUAL_VENDEDOR, ator=ator
        )
        session.refresh(atendimento)
        logger.info(f"[Atendimentos] Atendimento {atendimento.id} encerrado manualmente por {ator}")
        return atendimento.to_dict()


class ReabrirAtendimentoRequest(BaseModel):
    justificativa: Optional[str] = None


@app.post("/api/atendimentos/{atendimento_id}/reabrir")
async def reabrir_atendimento_manual(
    atendimento_id: int,
    payload: ReabrirAtendimentoRequest,
    ator: str = Depends(usuario_nome_atual),
):
    """Reabertura manual pelo vendedor (REQ-016.8) — bloqueada quando o atendimento foi
    encerrado por conversão de orçamento (`concluido_conversao`), pois a compra já foi
    concluída (REQ-016.7)."""
    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")
        if atendimento.status == StatusAtendimento.ATIVO:
            raise HTTPException(status_code=400, detail="Atendimento já está ativo")
        if atendimento.motivo_encerramento == MotivoEncerramento.CONCLUIDO_CONVERSAO.value:
            raise HTTPException(
                status_code=409,
                detail="Atendimento concluído por conversão de orçamento não pode ser reaberto",
            )

        atendimentos_svc.reabrir_atendimento(session, atendimento, ator=ator, justificativa=payload.justificativa)
        session.refresh(atendimento)
        logger.info(f"[Atendimentos] Atendimento {atendimento.id} reaberto manualmente por {ator}")
        return atendimento.to_dict()


class EnviarMensagemManualRequest(BaseModel):
    conteudo: str


@app.post("/api/atendimentos/{atendimento_id}/mensagens-manuais", status_code=201)
async def enviar_mensagem_manual(
    atendimento_id: int,
    payload: EnviarMensagemManualRequest,
    aprovador_id: int = Depends(usuario_id_atual),
):
    """
    Registra uma mensagem enviada manualmente pelo operador (modo HUMANO).

    A mensagem é salva com origem=SYSTEM e já considerada aprovada (o operador
    logado é o próprio autor). No futuro, integrar com Twilio para envio efetivo ao cliente.
    """
    conteudo = (payload.conteudo or "").strip()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Conteúdo da mensagem é obrigatório")

    with db.get_session() as session:
        atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")

        contato = atendimento.contato
        telefone = contato.telefone if contato and contato.telefone else None
        if not telefone:
            raise HTTPException(
                status_code=400,
                detail="Atendimento não tem contato com telefone associado",
            )

        mensagem = Mensagem(
            telefone=telefone,
            conteudo=conteudo,
            origem=OrigemMensagem.SYSTEM,
            contato_id=contato.id if contato else None,
            atendimento_id=atendimento.id,
            aprovador_id=aprovador_id,
            timestamp_aprovacao=utc_now(),
        )
        session.add(mensagem)
        session.flush()
        session.refresh(mensagem)
        return mensagem.to_dict()


@app.get("/api/processamentos/{processamento_id}")
async def obter_processamento(processamento_id: int):
    """Retorna as decisões do cérebro para uma mensagem (debug/auditoria)."""
    with db.get_session() as session:
        proc = session.query(ProcessamentoMensagem).filter_by(id=processamento_id).first()
        if not proc:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        return {
            **proc.to_dict(),
            "reports": [r.to_dict() for r in proc.reports],
        }


# ---------------------------------------------------------------------------
# Autenticação (REQ-010, Fase 4)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    login: str
    senha: str


class SenhaRequest(BaseModel):
    senha: str
    login: Optional[str] = None  # obrigatório se o usuário ainda não tiver um (ex.: seeds antigos)


@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request):
    """Autentica por login+senha e abre a sessão (cookie assinado)."""
    with db.get_session() as session:
        usuario = auth_svc.autenticar(session, payload.login, payload.senha)
        if not usuario:
            raise HTTPException(status_code=401, detail="Login ou senha inválidos")
        request.session["user_id"] = usuario.id
        return usuario.to_dict()


@app.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


@app.get("/api/auth/me")
async def obter_usuario_logado(request: Request):
    """Middleware já garante sessão válida para chegar aqui — devolve o usuário."""
    return request.state.usuario


# ---------------------------------------------------------------------------
# Users e Aprovação de Mensagens
# ---------------------------------------------------------------------------


class UserRequest(BaseModel):
    nome: str
    login: Optional[str] = None
    senha: Optional[str] = None


class AprovarMensagemRequest(BaseModel):
    feedback: Optional[str] = None  # REQ-011.6: nota opcional ("correta, mas...")


@app.get("/api/users")
async def listar_users():
    """Lista usuários cadastrados."""
    with db.get_session() as session:
        users = session.query(User).order_by(User.nome.asc()).all()
        return {"users": [u.to_dict() for u in users]}


@app.post("/api/users", status_code=201)
async def criar_user(payload: UserRequest):
    """Cria um usuário. `login`/`senha` são opcionais nesta etapa — sem eles, o
    usuário só ganha capacidade de login depois, via `PATCH /api/users/{id}/senha`."""
    nome = (payload.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")

    login_normalizado = (payload.login or "").strip().lower() or None
    if login_normalizado and payload.senha is None:
        raise HTTPException(status_code=400, detail="Informe uma senha para o login")

    with db.get_session() as session:
        if login_normalizado:
            existente = session.query(User).filter(User.login == login_normalizado).first()
            if existente:
                raise HTTPException(status_code=409, detail=f"Login '{login_normalizado}' já está em uso")

        user = User(
            nome=nome,
            login=login_normalizado,
            senha_hash=auth_svc.hash_senha(payload.senha) if login_normalizado else None,
        )
        session.add(user)
        session.flush()
        return user.to_dict()


@app.patch("/api/users/{user_id}/senha")
async def definir_senha_user(user_id: int, payload: SenhaRequest):
    """Define/redefine a senha de um usuário — requer sessão válida (qualquer
    usuário logado pode fazer isso; escopo mínimo, sem fluxo de "esqueci senha").

    Também é como os usuários criados antes desta fase (sem `login`) ganham
    capacidade de logar: informe `login` junto na primeira vez.
    """
    senha = payload.senha or ""
    if len(senha) < 4:
        raise HTTPException(status_code=422, detail="Senha deve ter ao menos 4 caracteres")

    login_novo = (payload.login or "").strip().lower() or None

    with db.get_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        if not user.login and not login_novo:
            raise HTTPException(
                status_code=400,
                detail="Usuário não tem login definido — informe 'login' junto com a senha",
            )

        if login_novo and login_novo != user.login:
            existente = session.query(User).filter(User.login == login_novo, User.id != user_id).first()
            if existente:
                raise HTTPException(status_code=409, detail=f"Login '{login_novo}' já está em uso")
            user.login = login_novo

        user.senha_hash = auth_svc.hash_senha(senha)
        session.flush()
        return user.to_dict()


@app.get("/api/mensagens/pendentes")
async def listar_mensagens_pendentes():
    """
    Lista mensagens geradas pelo agente (origem=SYSTEM) que ainda não foram
    aprovadas por um usuário.
    """
    with db.get_session() as session:
        mensagens = (
            session.query(Mensagem)
            .filter(Mensagem.origem == OrigemMensagem.SYSTEM)
            .filter(Mensagem.aprovador_id.is_(None))
            .order_by(Mensagem.timestamp.asc())
            .all()
        )
        return {
            "total": len(mensagens),
            "mensagens": [m.to_dict() for m in mensagens],
            # REQ-011.13: limiar de SLA para o painel destacar pendências antigas.
            "sla_aprovacao_minutos": ParametroService(session).sla_aprovacao_minutos(),
        }


@app.post("/api/mensagens/{mensagem_id}/aprovar")
async def aprovar_mensagem(
    mensagem_id: int,
    payload: AprovarMensagemRequest,
    aprovador_id: int = Depends(usuario_id_atual),
):
    """
    Aprova uma mensagem gerada pelo agente, registrando aprovador (usuário da
    sessão) e timestamp.

    Regras:
    - Só mensagens com origem=SYSTEM podem ser aprovadas.
    - Não reaprova mensagens já aprovadas (retorna 409).
    """
    with db.get_session() as session:
        mensagem = session.query(Mensagem).filter_by(id=mensagem_id).first()
        if not mensagem:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada")

        origem_val = mensagem.origem.value if isinstance(mensagem.origem, OrigemMensagem) else mensagem.origem
        if origem_val != OrigemMensagem.SYSTEM.value:
            raise HTTPException(
                status_code=400,
                detail="Apenas mensagens geradas pelo agente (origem=system) podem ser aprovadas",
            )

        if mensagem.aprovador_id is not None:
            # Verifica se foi reprovada (tem report vinculado) ou aprovada normalmente
            from models import ReportProblema as _RP

            foi_reprovada = session.query(_RP).filter_by(mensagem_id=mensagem.id).first() is not None
            detalhe = (
                "Mensagem já foi reprovada e não pode ser aprovada"
                if foi_reprovada
                else (
                    f"Mensagem já aprovada por aprovador_id={mensagem.aprovador_id} "
                    f"em {serialize_utc_datetime(mensagem.timestamp_aprovacao) or 'N/A'}"
                )
            )
            raise HTTPException(status_code=409, detail=detalhe)

        mensagem.aprovador_id = aprovador_id
        mensagem.timestamp_aprovacao = utc_now()
        if payload.feedback is not None:
            feedback = payload.feedback.strip()
            mensagem.feedback_aprovacao = feedback or None
        session.flush()
        session.refresh(mensagem)
        return mensagem.to_dict()


class ReprovarMensagemRequest(BaseModel):
    justificativa: str


@app.post("/api/mensagens/{mensagem_id}/reprovar", status_code=201)
async def reprovar_mensagem(
    mensagem_id: int,
    payload: ReprovarMensagemRequest,
    reprovador_id: int = Depends(usuario_id_atual),
    reprovador_nome: str = Depends(usuario_nome_atual),
):
    """
    Reprova uma mensagem gerada pelo agente, criando um report de problema.

    Regras:
    - Só mensagens com origem=SYSTEM podem ser reprovadas.
    - Não reprova mensagens já aprovadas.
    - Cria um report vinculado à mensagem (e ao processamento, se houver).
    """
    try:
        with db.get_session() as session:
            mensagem = session.query(Mensagem).filter_by(id=mensagem_id).first()
            if not mensagem:
                raise HTTPException(status_code=404, detail="Mensagem não encontrada")

            origem_val = mensagem.origem.value if isinstance(mensagem.origem, OrigemMensagem) else mensagem.origem
            if origem_val != OrigemMensagem.SYSTEM.value:
                raise HTTPException(
                    status_code=400,
                    detail="Apenas mensagens geradas pelo agente (origem=system) podem ser reprovadas",
                )

            if mensagem.aprovador_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Mensagem já foi aprovada e não pode ser reprovada",
                )

            justificativa = payload.justificativa.strip()
            if not justificativa:
                raise HTTPException(status_code=400, detail="Justificativa é obrigatória")

            logger.info(f"Criando report para mensagem_id={mensagem_id}, processamento_id={mensagem.processamento_id}")

            # Marca a mensagem como "revisada" para sair do estado pendente_aprovacao
            mensagem.aprovador_id = reprovador_id
            mensagem.timestamp_aprovacao = utc_now()

            # Cria o report vinculado à mensagem (e ao processamento se existir)
            report = ReportProblema(
                processamento_id=mensagem.processamento_id,  # pode ser None
                mensagem_id=mensagem.id,
                descricao=f"Mensagem reprovada: {justificativa}",
                autor=reprovador_nome,
                categoria=CategoriaReport.RESPOSTA_INADEQUADA,
                severidade=SeveridadeReport.MEDIA,
            )
            session.add(report)
            session.commit()
            session.refresh(report)
            logger.info(f"Report criado com sucesso: id={report.id}")

            return {
                "mensagem": "Mensagem reprovada e report criado com sucesso",
                "report_id": report.id,
                "mensagem_id": mensagem.id,
            }
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        stack_trace = traceback.format_exc()
        print(f"[ERRO REPROVAR] mensagem_id={mensagem_id}: {e}\n{stack_trace}", flush=True)
        logger.error(f"[ERRO REPROVAR] mensagem_id={mensagem_id}: {e}\n{stack_trace}")
        raise HTTPException(status_code=500, detail="Erro interno ao reprovar mensagem")


# ---------------------------------------------------------------------------


def _validar_enum(valor: Optional[str], enum_cls, nome: str):
    """Valida e converte string em enum, ou retorna None."""
    if valor is None:
        return None
    try:
        return enum_cls(valor)
    except ValueError:
        valores = [e.value for e in enum_cls]
        raise HTTPException(
            status_code=400,
            detail=f"Valor inválido para {nome}: '{valor}'. Aceitos: {valores}",
        )


DESCRICAO_REPORT_MIN_CHARS = 10

# REQ-012 (Fase 8): transições válidas do workflow de triagem de reports — evita
# pular etapas por engano (ex.: aberto → resolvido sem passar por análise) e
# permite reabertura a partir de qualquer estado terminal.
_TRANSICOES_STATUS_REPORT: dict[StatusReport, set[StatusReport]] = {
    StatusReport.ABERTO: {StatusReport.EM_ANALISE, StatusReport.AGUARDANDO_FIX, StatusReport.DESCARTADO},
    StatusReport.EM_ANALISE: {
        StatusReport.AGUARDANDO_FIX,
        StatusReport.RESOLVIDO,
        StatusReport.DESCARTADO,
        StatusReport.ABERTO,
    },
    StatusReport.AGUARDANDO_FIX: {StatusReport.RESOLVIDO, StatusReport.DESCARTADO, StatusReport.EM_ANALISE},
    StatusReport.RESOLVIDO: {StatusReport.ABERTO},
    StatusReport.DESCARTADO: {StatusReport.ABERTO},
}


class ReportProblemaRequest(BaseModel):
    descricao: str
    categoria: Optional[str] = None
    severidade: Optional[str] = None
    mensagem_id: Optional[int] = None


class AtualizarReportRequest(BaseModel):
    status: Optional[str] = None
    categoria: Optional[str] = None
    severidade: Optional[str] = None
    resolucao: Optional[str] = None


@app.post("/api/processamentos/{processamento_id}/reports", status_code=201)
async def criar_report_problema(
    processamento_id: int,
    payload: ReportProblemaRequest,
    autor: str = Depends(usuario_nome_atual),
):
    """Registra um report de problema sobre um processamento."""
    descricao = (payload.descricao or "").strip()
    if not descricao:
        raise HTTPException(status_code=400, detail="Descrição do problema é obrigatória")
    if len(descricao) < DESCRICAO_REPORT_MIN_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Descrição do problema deve ter pelo menos {DESCRICAO_REPORT_MIN_CHARS} caracteres",
        )

    categoria = _validar_enum(payload.categoria, CategoriaReport, "categoria")
    severidade = _validar_enum(payload.severidade, SeveridadeReport, "severidade")

    with db.get_session() as session:
        proc = session.query(ProcessamentoMensagem).filter_by(id=processamento_id).first()
        if not proc:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")

        report = ReportProblema(
            processamento_id=processamento_id,
            mensagem_id=payload.mensagem_id,
            descricao=descricao,
            autor=autor,
        )
        if categoria:
            report.categoria = categoria
        if severidade:
            report.severidade = severidade

        session.add(report)
        session.commit()
        session.refresh(report)
        return report.to_dict()


@app.patch("/api/reports/{report_id}")
async def atualizar_report(
    report_id: int,
    payload: AtualizarReportRequest,
    resolvido_por: str = Depends(usuario_nome_atual),
):
    """Atualiza um report (triagem/resolução)."""
    status_novo = _validar_enum(payload.status, StatusReport, "status")
    categoria = _validar_enum(payload.categoria, CategoriaReport, "categoria")
    severidade = _validar_enum(payload.severidade, SeveridadeReport, "severidade")

    with db.get_session() as session:
        report = session.query(ReportProblema).filter_by(id=report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report não encontrado")

        if status_novo is not None and status_novo != report.status:
            permitidos = _TRANSICOES_STATUS_REPORT.get(report.status, set())
            if status_novo not in permitidos:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Transição de status inválida: '{report.status.value}' → "
                        f"'{status_novo.value}'. Permitidas a partir de "
                        f"'{report.status.value}': {sorted(s.value for s in permitidos)}"
                    ),
                )

            session.add(
                HistoricoStatusReport(
                    report_id=report.id,
                    status_anterior=report.status.value,
                    status_novo=status_novo.value,
                    ator=resolvido_por,
                )
            )

            report.status = status_novo
            if status_novo in (StatusReport.RESOLVIDO, StatusReport.DESCARTADO):
                report.resolvido_em = utc_now()
                report.resolvido_por = resolvido_por
            else:
                # Se voltou a abrir, limpa resolvido_em/resolvido_por
                report.resolvido_em = None
                report.resolvido_por = None

        if categoria is not None:
            report.categoria = categoria
        if severidade is not None:
            report.severidade = severidade
        if payload.resolucao is not None:
            report.resolucao = payload.resolucao or None

        session.commit()
        session.refresh(report)
        return report.to_dict()


@app.get("/api/processamentos/{processamento_id}/reports")
async def listar_reports_problema(processamento_id: int):
    """Lista reports de problema associados a um processamento."""
    with db.get_session() as session:
        reports = session.query(ReportProblema).filter_by(
            processamento_id=processamento_id).order_by(
                ReportProblema.created_at.desc()
            ).all()
        return {"reports": [r.to_dict() for r in reports]}


_STATUS_REPORTS_ABERTOS = (
    StatusReport.ABERTO,
    StatusReport.EM_ANALISE,
    StatusReport.AGUARDANDO_FIX,
)


def _aplicar_filtros_reports(
    q,
    *,
    status_enum=None,
    categoria_enum=None,
    severidade_enum=None,
    apenas_abertos=False,
    autor=None,
    data_inicio=None,
    data_fim=None,
    busca=None,
):
    if status_enum:
        q = q.filter(ReportProblema.status == status_enum)
    elif apenas_abertos:
        q = q.filter(ReportProblema.status.in_(_STATUS_REPORTS_ABERTOS))
    if categoria_enum:
        q = q.filter(ReportProblema.categoria == categoria_enum)
    if severidade_enum:
        q = q.filter(ReportProblema.severidade == severidade_enum)
    if autor:
        q = q.filter(ReportProblema.autor.ilike(f"%{autor}%"))
    if data_inicio is not None:
        q = q.filter(ReportProblema.created_at >= data_inicio)
    if data_fim is not None:
        q = q.filter(ReportProblema.created_at <= data_fim)
    if busca:
        termo = f"%{busca}%"
        q = q.filter(
            sa_or(
                ReportProblema.descricao.ilike(termo),
                ReportProblema.resolucao.ilike(termo),
                ReportProblema.autor.ilike(termo),
            )
        )
    return q


def _calcular_stats_reports(q):
    from sqlalchemy import func

    total = q.count()
    por_status = dict(
        q.with_entities(ReportProblema.status, func.count(ReportProblema.id))
        .group_by(ReportProblema.status)
        .all()
    )
    por_categoria = dict(
        q.with_entities(ReportProblema.categoria, func.count(ReportProblema.id))
        .group_by(ReportProblema.categoria)
        .all()
    )
    por_severidade = dict(
        q.with_entities(ReportProblema.severidade, func.count(ReportProblema.id))
        .group_by(ReportProblema.severidade)
        .all()
    )
    return {
        "total": total,
        "por_status": {k.value if k else "null": v for k, v in por_status.items()},
        "por_categoria": {k.value if k else "null": v for k, v in por_categoria.items()},
        "por_severidade": {k.value if k else "null": v for k, v in por_severidade.items()},
    }


@app.get("/api/reports")
async def listar_todos_reports(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    severidade: Optional[str] = None,
    apenas_abertos: bool = False,
    autor: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    q_busca: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """Lista todos os reports de problema com filtros (fila de triagem).

    `page`/`limit` (REQ-010, Fase 4) seguem o mesmo padrão de `routers/pares_qa.py`.
    `autor`/`data_inicio`/`data_fim`/`q_busca` (REQ-012, Fase 8) filtram por autor
    (parcial), período de `created_at`, e busca textual em descrição/resolução/autor.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="page deve ser >= 1")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 200")

    status_enum = _validar_enum(status, StatusReport, "status")
    categoria_enum = _validar_enum(categoria, CategoriaReport, "categoria")
    severidade_enum = _validar_enum(severidade, SeveridadeReport, "severidade")

    with db.get_session() as session:
        q = session.query(ReportProblema)
        q = _aplicar_filtros_reports(
            q,
            status_enum=status_enum,
            categoria_enum=categoria_enum,
            severidade_enum=severidade_enum,
            apenas_abertos=apenas_abertos,
            autor=autor,
            data_inicio=data_inicio,
            data_fim=data_fim,
            busca=q_busca,
        )

        total = q.count()
        q = q.order_by(ReportProblema.created_at.desc()).offset((page - 1) * limit).limit(limit)
        reports = q.all()

        # Enriquecer com dados do processamento + mensagem
        result = []
        for r in reports:
            d = r.to_dict()
            proc = r.processamento
            if proc:
                d["processamento"] = {
                    "intencao": proc.intencao,
                    "template_usado": proc.template_usado,
                    "status_identificacao": proc.status_identificacao,
                }
                msg = proc.mensagem
                if msg:
                    d["mensagem"] = {
                        "id": msg.id,
                        "telefone": msg.telefone,
                        "conteudo": msg.conteudo,
                        "timestamp": serialize_utc_datetime(msg.timestamp),
                    }
            result.append(d)
        return {"total": total, "page": page, "limit": limit, "reports": result}


@app.get("/api/reports/stats")
async def stats_reports(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    severidade: Optional[str] = None,
    apenas_abertos: bool = False,
    autor: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    q_busca: Optional[str] = None,
):
    """Estatísticas agregadas dos reports (para header da tela de triagem)."""
    status_enum = _validar_enum(status, StatusReport, "status")
    categoria_enum = _validar_enum(categoria, CategoriaReport, "categoria")
    severidade_enum = _validar_enum(severidade, SeveridadeReport, "severidade")

    with db.get_session() as session:
        q = session.query(ReportProblema)
        q = _aplicar_filtros_reports(
            q,
            status_enum=status_enum,
            categoria_enum=categoria_enum,
            severidade_enum=severidade_enum,
            apenas_abertos=apenas_abertos,
            autor=autor,
            data_inicio=data_inicio,
            data_fim=data_fim,
            busca=q_busca,
        )
        return _calcular_stats_reports(q)


@app.get("/api/reports/{report_id}/contexto")
async def obter_contexto_report(report_id: int, antes: int = 3, depois: int = 3):
    """Retorna o contexto completo de um report: o report + processamento + janela de mensagens ao redor."""
    with db.get_session() as session:
        report = session.query(ReportProblema).filter_by(id=report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report não encontrado")

        proc = report.processamento
        msg = proc.mensagem if proc else None
        if not msg and report.mensagem_id:
            msg = session.query(Mensagem).filter_by(id=report.mensagem_id).first()

        contexto_msgs = []
        if msg:
            # Janela de N mensagens antes e depois (mesmo telefone)
            antes_q = (
                session.query(Mensagem)
                .filter(
                    Mensagem.telefone == msg.telefone,
                    Mensagem.timestamp < msg.timestamp,
                )
                .order_by(Mensagem.timestamp.desc())
                .limit(antes)
                .all()
            )
            depois_q = (
                session.query(Mensagem)
                .filter(
                    Mensagem.telefone == msg.telefone,
                    Mensagem.timestamp > msg.timestamp,
                )
                .order_by(Mensagem.timestamp.asc())
                .limit(depois)
                .all()
            )
            contexto_msgs = [
                m.to_dict() for m in reversed(antes_q)] + [msg.to_dict()] + [m.to_dict() for m in depois_q
            ]

        atendimento_id = (proc.atendimento_id_ativa if proc else None) or (msg.atendimento_id if msg else None)

        historico_status = (
            session.query(HistoricoStatusReport)
            .filter_by(report_id=report.id)
            .order_by(HistoricoStatusReport.timestamp.desc())
            .all()
        )

        return {
            "report": report.to_dict(),
            "processamento": proc.to_dict() if proc else None,
            "contexto_mensagens": contexto_msgs,
            "telefone": msg.telefone if msg else None,
            "atendimento_id": atendimento_id,
            "historico_status": [h.to_dict() for h in historico_status],
        }


@app.get("/api/reports/{report_id}/pacote-analise")
async def obter_pacote_analise_report(
    report_id: int,
    antes: int = 5,
    depois: int = 3,
    formato: str = "yaml",
):
    """
    Gera pacote de análise para o agente [curador_conhecimento].

    Extrai contexto do report, reprocessa classificação e buscas Q&A/RAG sobre a
    pergunta original (estado atual da base), e sugere documentos fonte em
    docs/FoldersProdutos/.

    Query `formato`: `yaml` (default) ou `json`.
    """
    from services.curador import montar_pacote_analise

    formato_norm = (formato or "yaml").lower().strip()
    if formato_norm not in ("yaml", "json"):
        raise HTTPException(
            status_code=400,
            detail="formato inválido; use 'yaml' ou 'json'",
        )

    try:
        with db.get_session() as session:
            pacote = await montar_pacote_analise(
                session=session,
                report_id=report_id,
                antes=antes,
                depois=depois,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[PacoteAnalise] Falha ao gerar pacote report_id=%s", report_id)
        raise HTTPException(status_code=500, detail="Erro ao gerar pacote de análise") from exc

    if formato_norm == "json":
        return pacote

    import yaml

    yaml_text = yaml.dump(
        pacote,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    return PlainTextResponse(
        content=yaml_text,
        media_type="text/yaml; charset=utf-8",
    )


# ============================================================================
# Configuração RAG (runtime) — para ajuste dinâmico durante testes
# ============================================================================


class RagConfigUpdate(BaseModel):
    rag_score_minimo: Optional[float] = None
    rag_top_k: Optional[int] = None
    rag_enabled: Optional[bool] = None
    qa_enabled: Optional[bool] = None
    qa_score_minimo: Optional[float] = None


class AtendimentoConfigUpdate(BaseModel):
    janela_continuacao_atendimento_horas: Optional[int] = None


class ParametroValorUpdate(BaseModel):
    valor: str


@app.get("/api/config/rag")
async def get_config_rag():
    """Retorna a configuração vigente de RAG e Q&A (REQ-014, Fase 7) — superfície única
    para os dois, já que ambos compõem a mesma etapa de geração de resposta."""
    from services.rag import get_qa_service, get_retrieval_service

    resultado = {
        "rag_enabled": settings.RAG_ENABLED,
        "rag_score_minimo": settings.RAG_SCORE_MINIMO,
        "rag_top_k": settings.RAG_TOP_K,
        "qa_enabled": settings.QA_ENABLED,
        "qa_score_minimo": settings.QA_SCORE_MINIMO,
    }
    try:
        servico = get_retrieval_service()
        resultado["rag_enabled"] = servico.habilitado
        resultado["rag_score_minimo"] = servico._score_minimo_padrao
        resultado["rag_top_k"] = servico._top_k_padrao
    except Exception:
        pass
    try:
        qa = get_qa_service()
        resultado["qa_enabled"] = qa.habilitado
        # `_score_minimo_padrao` é o limiar "responde" da zona cinza (persistido como
        # parametro `qa_embedding_responde_min`) — exposto aqui como `qa_score_minimo`
        # para espelhar o nome irmão `rag_score_minimo` na mesma superfície de config.
        resultado["qa_score_minimo"] = qa._score_minimo_padrao
    except Exception:
        pass
    return resultado


@app.patch("/api/config/rag")
async def patch_config_rag(body: RagConfigUpdate, ator: str = Depends(usuario_nome_atual)):
    """Atualiza RAG/Q&A sem reiniciar o servidor, persistindo em `parametros`
    (REQ-014, Fase 7).

    Valida TODOS os campos antes de aplicar qualquer um — uma falha de validação em
    um campo não deixa outro já aplicado pela metade (bug de atomicidade original).
    """
    from services.rag import get_qa_service, get_retrieval_service

    if body.rag_score_minimo is not None and not 0.0 <= body.rag_score_minimo <= 1.0:
        raise HTTPException(status_code=422, detail="rag_score_minimo deve estar entre 0.0 e 1.0")
    if body.rag_top_k is not None and body.rag_top_k < 1:
        raise HTTPException(status_code=422, detail="rag_top_k deve ser >= 1")
    if body.qa_score_minimo is not None and not 0.0 <= body.qa_score_minimo <= 1.0:
        raise HTTPException(status_code=422, detail="qa_score_minimo deve estar entre 0.0 e 1.0")

    retrieval = None
    if body.rag_score_minimo is not None or body.rag_top_k is not None or body.rag_enabled is not None:
        try:
            retrieval = get_retrieval_service()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"RAG não disponível: {exc}")

    qa = None
    if body.qa_enabled is not None or body.qa_score_minimo is not None:
        try:
            qa = get_qa_service()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"QA não disponível: {exc}")

    with db.get_session() as session:
        svc = ParametroService(session)
        if body.rag_score_minimo is not None:
            svc.set("rag_score_minimo", str(body.rag_score_minimo), ator=ator)
            retrieval._score_minimo_padrao = body.rag_score_minimo
        if body.rag_top_k is not None:
            svc.set("rag_top_k", str(body.rag_top_k), ator=ator)
            retrieval._top_k_padrao = body.rag_top_k
        if body.rag_enabled is not None:
            svc.set("rag_enabled", "true" if body.rag_enabled else "false", ator=ator)
            retrieval.habilitado = body.rag_enabled
        if body.qa_enabled is not None:
            svc.set("qa_enabled", "true" if body.qa_enabled else "false", ator=ator)
            qa.habilitado = body.qa_enabled
        if body.qa_score_minimo is not None:
            svc.set("qa_embedding_responde_min", str(body.qa_score_minimo), ator=ator)
            qa._score_minimo_padrao = body.qa_score_minimo

    logger.info("[Config RAG/QA] alterado por %s: %s", ator, body.model_dump(exclude_none=True))
    return await get_config_rag()


@app.post("/api/config/rag/reset")
async def reset_config_rag(ator: str = Depends(usuario_nome_atual)):
    """Restaura RAG/Q&A aos defaults de `Settings` (REQ-014, Fase 7)."""
    from services.rag import get_qa_service, get_retrieval_service

    with db.get_session() as session:
        svc = ParametroService(session)
        svc.set("rag_score_minimo", str(settings.RAG_SCORE_MINIMO), ator=ator)
        svc.set("rag_top_k", str(settings.RAG_TOP_K), ator=ator)
        svc.set("rag_enabled", "true" if settings.RAG_ENABLED else "false", ator=ator)
        svc.set("qa_enabled", "true" if settings.QA_ENABLED else "false", ator=ator)
        svc.set("qa_embedding_responde_min", str(settings.QA_SCORE_MINIMO), ator=ator)

    try:
        retrieval = get_retrieval_service()
        retrieval._score_minimo_padrao = settings.RAG_SCORE_MINIMO
        retrieval._top_k_padrao = settings.RAG_TOP_K
        retrieval.habilitado = settings.RAG_ENABLED
    except Exception:
        pass
    try:
        qa = get_qa_service()
        qa.habilitado = settings.QA_ENABLED
        qa._score_minimo_padrao = settings.QA_SCORE_MINIMO
    except Exception:
        pass

    logger.info("[Config RAG/QA] reset a defaults por %s", ator)
    return await get_config_rag()


@app.get("/api/config/historico")
async def obter_historico_configuracao(nome: Optional[str] = None, limit: int = 50):
    """Histórico de alterações de parâmetros de configuração (REQ-014, Fase 7)."""
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 200")
    with db.get_session() as session:
        query = session.query(HistoricoConfiguracao)
        if nome:
            query = query.filter(HistoricoConfiguracao.nome == nome)
        registros = query.order_by(HistoricoConfiguracao.timestamp.desc()).limit(limit).all()
        return {"historico": [r.to_dict() for r in registros]}


# ============================================================================
# Configuração de atendimento (runtime) — REQ-014.2C / REQ-016.18
# ============================================================================


@app.get("/api/config/atendimento")
async def get_config_atendimento():
    """Retorna parâmetros de atendimento persistidos em `parametros`."""
    from services.parametro_service import ParametroService

    with db.get_session() as session:
        svc = ParametroService(session)
        return {
            "janela_continuacao_atendimento_horas": svc.janela_continuacao_atendimento_horas(),
        }


# ============================================================================
# Modo de execução (runtime) — REQ-011
# ============================================================================


class ModoExecucaoUpdate(BaseModel):
    modo_execucao: str


@app.get("/api/config/execucao")
async def get_config_execucao():
    """Modo de execução vigente (REQ-011.1) + histórico recente de trocas (REQ-011.3)."""
    with db.get_session() as session:
        svc = ParametroService(session)
        historico = (
            session.query(HistoricoModoExecucao)
            .order_by(HistoricoModoExecucao.timestamp.desc())
            .limit(20)
            .all()
        )
        return {
            "modo_execucao": svc.modo_execucao().value,
            "sla_aprovacao_minutos": svc.sla_aprovacao_minutos(),
            "historico": [h.to_dict() for h in historico],
        }


@app.patch("/api/config/execucao")
async def patch_config_execucao(body: ModoExecucaoUpdate, ator: str = Depends(usuario_nome_atual)):
    """Troca o modo de execução vigente, registrando auditoria (REQ-011.3)."""
    try:
        novo_modo = ModoExecucao(body.modo_execucao)
    except ValueError:
        valores = [m.value for m in ModoExecucao]
        raise HTTPException(
            status_code=422,
            detail=f"modo_execucao inválido: '{body.modo_execucao}'. Aceitos: {valores}",
        )

    with db.get_session() as session:
        svc = ParametroService(session)
        modo_anterior = svc.modo_execucao()
        if modo_anterior == novo_modo:
            return {"modo_execucao": novo_modo.value, "alterado": False}

        svc.set(MODO_EXECUCAO, novo_modo.value, descricao="Modo de execução vigente (REQ-011)")
        session.add(
            HistoricoModoExecucao(modo_anterior=modo_anterior.value, modo_novo=novo_modo.value, ator=ator)
        )
        session.commit()
        logger.info(f"[ModoExecucao] {modo_anterior.value} → {novo_modo.value} (ator={ator})")
        return {"modo_execucao": novo_modo.value, "alterado": True}


@app.patch("/api/config/atendimento")
async def patch_config_atendimento(body: AtendimentoConfigUpdate, ator: str = Depends(usuario_nome_atual)):
    """Atualiza parâmetros de atendimento sem reiniciar o servidor."""
    from services.parametro_service import (
        JANELA_CONTINUACAO_ATENDIMENTO_HORAS,
        ParametroService,
    )

    with db.get_session() as session:
        svc = ParametroService(session)
        if body.janela_continuacao_atendimento_horas is not None:
            try:
                svc.set_int(
                    JANELA_CONTINUACAO_ATENDIMENTO_HORAS,
                    body.janela_continuacao_atendimento_horas,
                    minimo=1,
                    ator=ator,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "janela_continuacao_atendimento_horas": svc.janela_continuacao_atendimento_horas(),
        }


# ============================================================================
# Parâmetros de configuração (tabela parametros) — REQ-014
# ============================================================================


@app.get("/api/parametros")
async def listar_parametros():
    """Lista todos os parâmetros (nome, descrição, valor)."""
    with db.get_session() as session:
        rows = session.query(Parametro).order_by(Parametro.nome.asc()).all()
        return {
            "total": len(rows),
            "parametros": [p.to_dict() for p in rows],
        }


@app.patch("/api/parametros/{nome}")
async def atualizar_parametro(nome: str, body: ParametroValorUpdate, ator: str = Depends(usuario_nome_atual)):
    """Atualiza apenas o valor de um parâmetro existente."""
    from services.parametro_service import ParametroService, validar_valor_parametro

    with db.get_session() as session:
        row = session.query(Parametro).filter(Parametro.nome == nome).first()
        if not row:
            raise HTTPException(status_code=404, detail="Parâmetro não encontrado")
        try:
            valor = validar_valor_parametro(nome, body.valor)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        svc = ParametroService(session)
        atualizado = svc.set(nome, valor, ator=ator)
        return atualizado.to_dict()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
