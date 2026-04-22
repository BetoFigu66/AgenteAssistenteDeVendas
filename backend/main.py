"""
Assistente de Vendas - Backend FastAPI
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uvicorn
import logging

from fastapi import HTTPException

from database import Database
from config import settings
from models import (
    CategoriaReport,
    Contato,
    Empresa,
    Mensagem,
    Negociacao,
    NegociacaoInfo,
    Orcamento,
    ProcessamentoMensagem,
    ReportProblema,
    SeveridadeReport,
    StatusNegociacao,
    StatusReport,
)
from services.identificador import identificar_por_telefone, normalizar_telefone
from services.llm import get_llm_provider
from services.processador import ProcessadorMensagem

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
    
    # Inicializa o cerebrio (LLM + processador)
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
    title="Assistente de Vendas API",
    description="API para integração com WhatsApp via Twilio",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {
        "telefone": telefone,
        "mensagens": mensagens
    }


@app.get("/api/telefones")
async def listar_telefones():
    """
    Lista todos os telefones com histórico.
    """
    telefones = db.listar_telefones()
    return {"telefones": telefones}


STATUS_NEGOCIACAO_ATIVOS = [
    s.value for s in (
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
            } if contato else None,
            "empresa": {
                "id": empresa.id,
                "cnpj": empresa.cnpj,
                "nome": empresa.nome,
                "fantasia": empresa.fantasia,
            } if empresa else None,
            "negociacao": {
                "id": negociacao.id,
                "titulo": negociacao.titulo,
                "status": negociacao.status.value if negociacao.status else None,
            } if negociacao else None,
        }


@app.get("/api/empresas/{empresa_id}")
async def obter_empresa(empresa_id: int):
    """Retorna detalhes completos de uma empresa."""
    with db.get_session() as session:
        empresa = session.query(Empresa).filter_by(id=empresa_id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa.to_dict()


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
            } if empresa else None,
            "itens": [item.to_dict() for item in negociacao.itens],
            "informacoes": [info.to_dict() for info in negociacao.informacoes],
            "orcamentos": [orc.to_dict() for orc in negociacao.orcamentos],
        }


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
        reports = (
            session.query(ReportProblema)
            .filter_by(processamento_id=processamento_id)
            .order_by(ReportProblema.created_at.desc())
            .all()
        )
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
        por_status = dict(
            session.query(ReportProblema.status, func.count(ReportProblema.id))
            .group_by(ReportProblema.status).all()
        )
        por_categoria = dict(
            session.query(ReportProblema.categoria, func.count(ReportProblema.id))
            .group_by(ReportProblema.categoria).all()
        )
        por_severidade = dict(
            session.query(ReportProblema.severidade, func.count(ReportProblema.id))
            .group_by(ReportProblema.severidade).all()
        )
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
            contexto_msgs = (
                [m.to_dict() for m in reversed(antes_q)]
                + [msg.to_dict()]
                + [m.to_dict() for m in depois_q]
            )
        
        return {
            "report": report.to_dict(),
            "processamento": proc.to_dict() if proc else None,
            "contexto_mensagens": contexto_msgs,
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
