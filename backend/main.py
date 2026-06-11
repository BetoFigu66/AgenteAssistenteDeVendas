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
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from models import (
    CategoriaReport,
    Contato,
    Empresa,
    Mensagem,
    ModoOperacao,
    Negociacao,
    OrigemMensagem,
    ProcessamentoMensagem,
    ReportProblema,
    SeveridadeReport,
    StatusNegociacao,
    StatusReport,
    User,
)
from pydantic import BaseModel
from routers.pares_qa import router as pares_qa_router
from services.identificador import identificar_por_telefone, normalizar_telefone
from services.llm import get_llm_provider
from services.processador import ProcessadorMensagem
from sqlalchemy import func

logging.basicConfig(level=logging.INFO)
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

    # Se não há resposta (ex.: negociação em modo HUMANO), devolve TwiML vazio
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
async def obter_historico(telefone: str):
    """
    Retorna o histórico de mensagens para um número de telefone.
    """
    mensagens = db.obter_historico(telefone)
    return {"telefone": telefone, "mensagens": mensagens}


@app.get("/api/telefones")
async def listar_telefones():
    """
    Lista todos os telefones com histórico.
    """
    telefones = db.listar_telefones()
    return {"telefones": telefones}


STATUS_NEGOCIACAO_ATIVOS = [
    s.value
    for s in (
        StatusNegociacao.NOVO,
        StatusNegociacao.EM_CONTATO,
        StatusNegociacao.AGUARDANDO_ORCAMENTO,
        StatusNegociacao.ORCAMENTO_ENVIADO,
        StatusNegociacao.EM_NEGOCIACAO,
    )
]


@app.get("/api/conversa/{telefone}")
async def obter_dados_conversa(telefone: str):
    """
    Retorna dados consolidados de uma conversa (telefone) para exibir no header.

    Inclui: contato, empresa e negociação ativa (quando identificados).
    """
    tel_norm = normalizar_telefone(telefone)

    with db.get_session() as session:
        ident = identificar_por_telefone(session, tel_norm)

        contato = ident.contato
        empresa = ident.empresa

        negociacao = None
        if contato:
            negociacao = (
                session.query(Negociacao)
                .filter(Negociacao.contato_id == contato.id)
                .filter(Negociacao.status.in_(STATUS_NEGOCIACAO_ATIVOS))
                .order_by(Negociacao.created_at.desc())
                .first()
            )

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
            "negociacao": {
                "id": negociacao.id,
                "titulo": negociacao.titulo,
                "status": negociacao.status.value if negociacao.status else None,
                "modo_operacao": (negociacao.modo_operacao.value if negociacao.modo_operacao else None),
            }
            if negociacao
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
# Rotas de Negociação - ORDEM IMPORTA: rotas estáticas ANTES de rotas dinâmicas
# =============================================================================


@app.get("/api/negociacoes/ativas")
async def listar_negociacoes_ativas():
    """
    Lista negociações ativas ordenadas pela quantidade de mensagens pendentes
    de aprovação (maior primeiro).

    Retorna: id, status, modo_operacao, telefone, nome_contato, empresa_nome,
    mensagens_pendentes.
    """
    with db.get_session() as session:
        # Subquery: contagem de mensagens pendentes por negociação
        pendentes_expr = func.count(Mensagem.id).label("pendentes")
        subq = (
            session.query(
                Mensagem.negociacao_id.label("neg_id"),
                pendentes_expr,
            )
            .filter(Mensagem.origem == OrigemMensagem.SYSTEM)
            .filter(Mensagem.aprovador_id.is_(None))
            .filter(Mensagem.negociacao_id.isnot(None))
            .group_by(Mensagem.negociacao_id)
            .subquery()
        )

        stmt = (
            session.query(Negociacao, Contato, Empresa, subq.c.pendentes)
            .join(Contato, Contato.id == Negociacao.contato_id)
            .join(Empresa, Empresa.id == Negociacao.empresa_id)
            .outerjoin(subq, subq.c.neg_id == Negociacao.id)
            .filter(Negociacao.status.in_(STATUS_NEGOCIACAO_ATIVOS))
            .order_by(
                func.coalesce(subq.c.pendentes, 0).desc(),
                Negociacao.updated_at.desc(),
            )
        )

        resultado = []
        for negociacao, contato, empresa, pendentes in stmt.all():
            resultado.append(
                {
                    "id": negociacao.id,
                    "status": negociacao.status.value if negociacao.status else None,
                    "modo_operacao": (negociacao.modo_operacao.value if negociacao.modo_operacao else None),
                    "titulo": negociacao.titulo,
                    "telefone": contato.telefone,
                    "nome_contato": contato.nome,
                    "empresa_id": empresa.id,
                    "empresa_nome": empresa.fantasia or empresa.nome,
                    "mensagens_pendentes": int(pendentes or 0),
                    "updated_at": (negociacao.updated_at.isoformat() if negociacao.updated_at else None),
                }
            )
        return {"total": len(resultado), "negociacoes": resultado}


@app.get("/api/negociacoes/{negociacao_id}")
async def obter_negociacao(negociacao_id: int):
    """Retorna detalhes completos de uma negociação, incluindo itens, infos e orçamentos."""
    with db.get_session() as session:
        negociacao = session.query(Negociacao).filter_by(id=negociacao_id).first()
        if not negociacao:
            raise HTTPException(status_code=404, detail="Negociação não encontrada")

        contato = negociacao.contato
        empresa = negociacao.empresa

        return {
            **negociacao.to_dict(),
            "contato": contato.to_dict() if contato else None,
            "empresa": {
                "id": empresa.id,
                "cnpj": empresa.cnpj,
                "nome": empresa.nome,
            }
            if empresa
            else None,
            "itens": [item.to_dict() for item in negociacao.itens],
            "informacoes": [info.to_dict() for info in negociacao.informacoes],
            "orcamentos": [orc.to_dict() for orc in negociacao.orcamentos],
        }


class AlterarModoRequest(BaseModel):
    modo_operacao: str  # "agente" | "humano"


@app.patch("/api/negociacoes/{negociacao_id}/modo-operacao")
async def alterar_modo_operacao(negociacao_id: int, payload: AlterarModoRequest):
    """
    Alterna o modo de operação de uma negociação entre AGENTE e HUMANO.

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
        negociacao = session.query(Negociacao).filter_by(id=negociacao_id).first()
        if not negociacao:
            raise HTTPException(status_code=404, detail="Negociação não encontrada")
        negociacao.modo_operacao = novo_modo
        session.flush()
        session.refresh(negociacao)
        logger.info(f"[ModoOperacao] Negociação {negociacao.id} alterada para modo={novo_modo.value}")
        return negociacao.to_dict()


class EnviarMensagemManualRequest(BaseModel):
    conteudo: str
    aprovador_id: Optional[int] = None  # quem enviou (opcional nesta etapa)


@app.post("/api/negociacoes/{negociacao_id}/mensagens-manuais", status_code=201)
async def enviar_mensagem_manual(negociacao_id: int, payload: EnviarMensagemManualRequest):
    """
    Registra uma mensagem enviada manualmente pelo operador (modo HUMANO).

    A mensagem é salva com origem=SYSTEM e já considerada aprovada (o operador
    é o próprio autor). No futuro, integrar com Twilio para envio efetivo ao cliente.
    """
    conteudo = (payload.conteudo or "").strip()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Conteúdo da mensagem é obrigatório")

    with db.get_session() as session:
        negociacao = session.query(Negociacao).filter_by(id=negociacao_id).first()
        if not negociacao:
            raise HTTPException(status_code=404, detail="Negociação não encontrada")

        contato = negociacao.contato
        telefone = contato.telefone if contato and contato.telefone else None
        if not telefone:
            raise HTTPException(
                status_code=400,
                detail="Negociação não tem contato com telefone associado",
            )

        aprovador = None
        if payload.aprovador_id is not None:
            aprovador = session.query(User).filter_by(id=payload.aprovador_id).first()
            if not aprovador:
                raise HTTPException(
                    status_code=404,
                    detail=f"Usuário aprovador_id={payload.aprovador_id} não encontrado",
                )

        mensagem = Mensagem(
            telefone=telefone,
            conteudo=conteudo,
            origem=OrigemMensagem.SYSTEM,
            contato_id=contato.id if contato else None,
            negociacao_id=negociacao.id,
            aprovador_id=aprovador.id if aprovador else None,
            timestamp_aprovacao=datetime.utcnow() if aprovador else None,
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
# Users e Aprovação de Mensagens
# ---------------------------------------------------------------------------


class UserRequest(BaseModel):
    nome: str


class AprovarMensagemRequest(BaseModel):
    aprovador_id: int


@app.get("/api/users")
async def listar_users():
    """Lista usuários cadastrados (sem autenticação)."""
    with db.get_session() as session:
        users = session.query(User).order_by(User.nome.asc()).all()
        return {"users": [u.to_dict() for u in users]}


@app.post("/api/users", status_code=201)
async def criar_user(payload: UserRequest):
    """Cria um usuário (id + nome). Sem autenticação por enquanto."""
    nome = (payload.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    with db.get_session() as session:
        user = User(nome=nome)
        session.add(user)
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
        }


@app.post("/api/mensagens/{mensagem_id}/aprovar")
async def aprovar_mensagem(mensagem_id: int, payload: AprovarMensagemRequest):
    """
    Aprova uma mensagem gerada pelo agente, registrando aprovador e timestamp.

    Regras:
    - Só mensagens com origem=SYSTEM podem ser aprovadas.
    - Não reaprova mensagens já aprovadas (retorna 409).
    - aprovador_id deve existir na tabela users.
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
                    f"em {mensagem.timestamp_aprovacao.isoformat() if mensagem.timestamp_aprovacao else 'N/A'}"
                )
            )
            raise HTTPException(status_code=409, detail=detalhe)

        aprovador = session.query(User).filter_by(id=payload.aprovador_id).first()
        if not aprovador:
            raise HTTPException(
                status_code=404,
                detail=f"Usuário aprovador_id={payload.aprovador_id} não encontrado",
            )

        mensagem.aprovador_id = aprovador.id
        mensagem.timestamp_aprovacao = datetime.utcnow()
        session.flush()
        session.refresh(mensagem)
        return mensagem.to_dict()


class ReprovarMensagemRequest(BaseModel):
    justificativa: str
    reprovador_id: int


@app.post("/api/mensagens/{mensagem_id}/reprovar", status_code=201)
async def reprovar_mensagem(mensagem_id: int, payload: ReprovarMensagemRequest):
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

            reprovador = session.query(User).filter_by(id=payload.reprovador_id).first()
            if not reprovador:
                raise HTTPException(
                    status_code=404,
                    detail=f"Usuário reprovador_id={payload.reprovador_id} não encontrado",
                )

            justificativa = payload.justificativa.strip()
            if not justificativa:
                raise HTTPException(status_code=400, detail="Justificativa é obrigatória")

            logger.info(f"Criando report para mensagem_id={mensagem_id}, processamento_id={mensagem.processamento_id}")

            # Marca a mensagem como "revisada" para sair do estado pendente_aprovacao
            mensagem.aprovador_id = reprovador.id
            mensagem.timestamp_aprovacao = datetime.utcnow()

            # Cria o report vinculado à mensagem (e ao processamento se existir)
            report = ReportProblema(
                processamento_id=mensagem.processamento_id,  # pode ser None
                mensagem_id=mensagem.id,
                descricao=f"Mensagem reprovada: {justificativa}",
                autor=reprovador.nome,
                categoria=CategoriaReport.RESPOSTA_INADEQUADA,
                severidade=SeveridadeReport.ALTA,
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


class ReportProblemaRequest(BaseModel):
    descricao: str
    autor: Optional[str] = None
    categoria: Optional[str] = None
    severidade: Optional[str] = None
    mensagem_id: Optional[int] = None


class AtualizarReportRequest(BaseModel):
    status: Optional[str] = None
    categoria: Optional[str] = None
    severidade: Optional[str] = None
    resolucao: Optional[str] = None
    resolvido_por: Optional[str] = None


@app.post("/api/processamentos/{processamento_id}/reports", status_code=201)
async def criar_report_problema(processamento_id: int, payload: ReportProblemaRequest):
    """Registra um report de problema sobre um processamento."""
    descricao = (payload.descricao or "").strip()
    if not descricao:
        raise HTTPException(status_code=400, detail="Descrição do problema é obrigatória")

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
            autor=(payload.autor or None),
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
async def atualizar_report(report_id: int, payload: AtualizarReportRequest):
    """Atualiza um report (triagem/resolução)."""
    status_novo = _validar_enum(payload.status, StatusReport, "status")
    categoria = _validar_enum(payload.categoria, CategoriaReport, "categoria")
    severidade = _validar_enum(payload.severidade, SeveridadeReport, "severidade")

    with db.get_session() as session:
        report = session.query(ReportProblema).filter_by(id=report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report não encontrado")

        if status_novo is not None:
            report.status = status_novo
            if status_novo in (StatusReport.RESOLVIDO, StatusReport.DESCARTADO):
                report.resolvido_em = datetime.utcnow()
                if payload.resolvido_por:
                    report.resolvido_por = payload.resolvido_por
            else:
                # Se voltou a abrir, limpa resolvido_em
                report.resolvido_em = None

        if categoria is not None:
            report.categoria = categoria
        if severidade is not None:
            report.severidade = severidade
        if payload.resolucao is not None:
            report.resolucao = payload.resolucao or None
        if payload.resolvido_por is not None and status_novo is None:
            report.resolvido_por = payload.resolvido_por or None

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


@app.get("/api/reports")
async def listar_todos_reports(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    severidade: Optional[str] = None,
    apenas_abertos: bool = False,
):
    """Lista todos os reports de problema com filtros (fila de triagem)."""
    status_enum = _validar_enum(status, StatusReport, "status")
    categoria_enum = _validar_enum(categoria, CategoriaReport, "categoria")
    severidade_enum = _validar_enum(severidade, SeveridadeReport, "severidade")

    with db.get_session() as session:
        q = session.query(ReportProblema)

        if status_enum:
            q = q.filter(ReportProblema.status == status_enum)
        elif apenas_abertos:
            q = q.filter(
                ReportProblema.status.in_([StatusReport.ABERTO, StatusReport.EM_ANALISE, StatusReport.AGUARDANDO_FIX])
            )
        if categoria_enum:
            q = q.filter(ReportProblema.categoria == categoria_enum)
        if severidade_enum:
            q = q.filter(ReportProblema.severidade == severidade_enum)

        q = q.order_by(ReportProblema.created_at.desc())
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
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    }
            result.append(d)
        return {"reports": result}


@app.get("/api/reports/stats")
async def stats_reports():
    """Estatísticas agregadas dos reports (para header da tela de triagem)."""
    from sqlalchemy import func

    with db.get_session() as session:
        total = session.query(func.count(ReportProblema.id)).scalar()
        por_status = dict(session.query(
            ReportProblema.status, func.count(ReportProblema.id)).group_by(
                ReportProblema.status).all())
        por_categoria = dict(session.query(
            ReportProblema.categoria, func.count(ReportProblema.id)).group_by(ReportProblema.categoria).all()
        )
        por_severidade = dict(session.query(
                ReportProblema.severidade, func.count(ReportProblema.id)
            ).group_by(ReportProblema.severidade).all())
        return {
            "total": total,
            "por_status": {k.value if k else "null": v for k, v in por_status.items()},
            "por_categoria": {k.value if k else "null": v for k, v in por_categoria.items()},
            "por_severidade": {k.value if k else "null": v for k, v in por_severidade.items()},
        }


@app.get("/api/reports/{report_id}/contexto")
async def obter_contexto_report(report_id: int, antes: int = 3, depois: int = 3):
    """Retorna o contexto completo de um report: o report + processamento + janela de mensagens ao redor."""
    with db.get_session() as session:
        report = session.query(ReportProblema).filter_by(id=report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report não encontrado")

        proc = report.processamento
        msg = proc.mensagem if proc else None

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

        return {
            "report": report.to_dict(),
            "processamento": proc.to_dict() if proc else None,
            "contexto_mensagens": contexto_msgs,
        }


# ============================================================================
# Configuração RAG (runtime) — para ajuste dinâmico durante testes
# ============================================================================


class RagConfigUpdate(BaseModel):
    rag_score_minimo: Optional[float] = None
    rag_top_k: Optional[int] = None


@app.get("/api/config/rag")
async def get_config_rag():
    """Retorna a configuração atual da RAG em memória."""
    from services.rag import get_retrieval_service

    try:
        servico = get_retrieval_service()
        return {
            "rag_enabled": settings.RAG_ENABLED,
            "rag_score_minimo": servico._score_minimo_padrao,
            "rag_top_k": servico._top_k_padrao,
        }
    except Exception:
        return {
            "rag_enabled": settings.RAG_ENABLED,
            "rag_score_minimo": settings.RAG_SCORE_MINIMO,
            "rag_top_k": settings.RAG_TOP_K,
        }


@app.patch("/api/config/rag")
async def patch_config_rag(body: RagConfigUpdate):
    """Atualiza em memória os parâmetros da RAG sem reiniciar o servidor."""
    from services.rag import get_retrieval_service

    try:
        servico = get_retrieval_service()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RAG não disponível: {exc}")
    if body.rag_score_minimo is not None:
        if not 0.0 <= body.rag_score_minimo <= 1.0:
            raise HTTPException(status_code=422, detail="rag_score_minimo deve estar entre 0.0 e 1.0")
        servico._score_minimo_padrao = body.rag_score_minimo
    if body.rag_top_k is not None:
        if body.rag_top_k < 1:
            raise HTTPException(status_code=422, detail="rag_top_k deve ser >= 1")
        servico._top_k_padrao = body.rag_top_k
    logger.info(
        "[RAG config] score_minimo=%.2f top_k=%d",
        servico._score_minimo_padrao,
        servico._top_k_padrao,
    )
    return {
        "rag_score_minimo": servico._score_minimo_padrao,
        "rag_top_k": servico._top_k_padrao,
    }


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
