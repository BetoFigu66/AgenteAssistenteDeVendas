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

from database import Database
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db: Database = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    global db
    logger.info("Iniciando aplicação...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    db = Database()
    logger.info("Banco de dados inicializado com SQLAlchemy")
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

RESPOSTA_PADRAO = "Ainda não fui treinado, não consigo te responder, me desculpe."


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
    
    Twilio envia dados como application/x-www-form-urlencoded com campos:
    - From: Número do remetente (ex: whatsapp:+5511999999999)
    - Body: Conteúdo da mensagem
    - MessageSid: ID único da mensagem
    - AccountSid: ID da conta Twilio
    - To: Número do destinatário (seu número Twilio)
    - NumMedia: Quantidade de arquivos de mídia
    """
    telefone = From.replace("whatsapp:", "")
    
    db.salvar_mensagem(
        telefone=telefone,
        conteudo=Body,
        origem="user",
        message_sid=MessageSid
    )
    
    db.salvar_mensagem(
        telefone=telefone,
        conteudo=RESPOSTA_PADRAO,
        origem="system"
    )
    
    # Twilio espera resposta TwiML ou texto simples
    # Resposta vazia com 200 OK = não enviar resposta automática
    # Para enviar resposta, usar TwiML:
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{RESPOSTA_PADRAO}</Message>
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
    Endpoint para enviar mensagem via interface web (simulação).
    Salva a mensagem do usuário e retorna a resposta padrão.
    """
    telefone = request.telefone
    
    db.salvar_mensagem(
        telefone=telefone,
        conteudo=request.mensagem,
        origem="user"
    )
    
    db.salvar_mensagem(
        telefone=telefone,
        conteudo=RESPOSTA_PADRAO,
        origem="system"
    )
    
    return {
        "status": "ok",
        "resposta": RESPOSTA_PADRAO
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
