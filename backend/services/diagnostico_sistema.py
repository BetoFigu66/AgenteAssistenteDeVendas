"""
Diagnóstico do sistema para a aba "Sistema" do painel: as configurações do `.env`
(`config.py::Settings`) sem os dados sensíveis, e a situação do LLM.

Mascaramento (o valor sensível nunca sai daqui, nem parcialmente):
- nome com KEY, SECRET, TOKEN, PASSWORD, SENHA, SID, USER ou USUARIO: só "definido" ou
  "não definido";
- URL com usuário e senha embutidos (`DATABASE_URL`): o trecho `usuario:senha@` vira `***@`;
  id de conta no caminho (`/accounts/{id}`, Cloudflare) vira `***`;
- número de telefone: só os 4 últimos dígitos.

A situação do LLM junta três fontes: se o processador subiu com um provedor, um teste ao
vivo (uma chamada curta, guardada por `_VALIDADE_TESTE_SEGUNDOS` para a tela não gastar
cota a cada atualização) e o uso real recente, da tabela `comparacoes_llm`.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import timedelta
from typing import Any, Optional

from config import Settings, settings
from models import ComparacaoLLM
from sqlalchemy import func
from sqlalchemy.orm import Session
from utils.datetime_utils import serialize_utc_datetime, utc_now

_PADRAO_SENSIVEL = re.compile(r"KEY|SECRET|TOKEN|PASSWORD|SENHA|SID|USER|USUARIO|CREDENCIA")
_PADRAO_TELEFONE = re.compile(r"NUMBER|TELEFONE|NUMERO")
_PADRAO_CREDENCIAL_URL = re.compile(r"(?P<esquema>[a-zA-Z][\w+.-]*://)[^@/\s]+@")
# Id de conta no caminho da URL (Cloudflare: `.../accounts/{id}/ai/v1`).
_PADRAO_CONTA_URL = re.compile(r"(?P<prefixo>/accounts/)[^/\s]+")

_GRUPOS = (
    ("TWILIO_", "Canal WhatsApp"),
    ("CANAL_", "Canal WhatsApp"),
    ("APP_URL", "Canal WhatsApp"),
    ("LLM_", "LLM"),
    ("EMBEDDING_", "Embeddings"),
    ("RAG_", "Base de conhecimento"),
    ("QA_", "Base de conhecimento"),
    ("AJUDA_", "Base de ajuda"),
    ("DATABASE_", "Banco de dados"),
    ("SQL_", "Banco de dados"),
    ("SESSION_", "Autenticação"),
    ("AUTH_", "Autenticação"),
    ("RECEITAWS_", "Consultas externas"),
    ("CPF_", "Consultas externas"),
)

_SECRET_DE_DEV = "dev-secret-key-troque-em-producao"

_VALIDADE_TESTE_SEGUNDOS = 60
_TIMEOUT_TESTE_SEGUNDOS = 20
_ultimo_teste: Optional[dict] = None
_ultimo_teste_em: float = 0.0


def _grupo(nome: str) -> str:
    for prefixo, grupo in _GRUPOS:
        if nome.startswith(prefixo):
            return grupo
    return "Servidor"


def eh_sensivel(nome: str) -> bool:
    return bool(_PADRAO_SENSIVEL.search(nome))


def mascarar_valor(nome: str, valor: Any) -> tuple[Any, bool]:
    """(valor exibível, se foi mascarado)."""
    if valor is None or valor == "":
        return valor, False
    if eh_sensivel(nome):
        return "definido", True
    if isinstance(valor, str):
        if _PADRAO_TELEFONE.search(nome):
            digitos = re.sub(r"\D", "", valor)
            return (f"***{digitos[-4:]}" if len(digitos) > 4 else "***"), True
        sem_credencial = _PADRAO_CREDENCIAL_URL.sub(r"\g<esquema>***@", valor)
        sem_credencial = _PADRAO_CONTA_URL.sub(r"\g<prefixo>***", sem_credencial)
        if sem_credencial != valor:
            return sem_credencial, True
    return valor, False


def configuracoes(cfg: Settings = settings) -> list[dict]:
    """As configurações do `Settings`, na ordem do `config.py`, sem os dados sensíveis."""
    definidos = cfg.model_fields_set
    itens = []
    for nome in type(cfg).model_fields:
        valor = getattr(cfg, nome)
        exibicao, mascarado = mascarar_valor(nome, valor)
        if eh_sensivel(nome) and not valor:
            exibicao = "não definido"
        aviso = None
        if nome == "SESSION_SECRET_KEY" and valor == _SECRET_DE_DEV:
            aviso = "Valor padrão de desenvolvimento: trocar antes de expor o sistema."
        itens.append(
            {
                "nome": nome,
                "grupo": _grupo(nome),
                "valor": exibicao,
                "sensivel": eh_sensivel(nome),
                "mascarado": mascarado,
                "origem": "configurado" if nome in definidos else "padrão",
                "aviso": aviso,
            }
        )
    return itens


async def _testar(llm) -> dict:
    inicio = time.monotonic()
    try:
        resposta = await asyncio.wait_for(
            llm.completar(
                prompt_sistema="Você é um teste de disponibilidade. Responda apenas: ok",
                prompt_usuario="ok?",
                temperatura=0.0,
                max_tokens=5,
            ),
            timeout=_TIMEOUT_TESTE_SEGUNDOS,
        )
        return {
            "ok": True,
            "erro": None,
            "latencia_ms": int((time.monotonic() - inicio) * 1000),
            "modelo_respondeu": getattr(resposta, "modelo", None),
        }
    except asyncio.TimeoutError:
        erro = f"Sem resposta em {_TIMEOUT_TESTE_SEGUNDOS}s"
    except Exception as e:  # o erro do provedor é exatamente o que a tela mostra
        erro = f"{type(e).__name__}: {e}"
    # A mensagem do provedor repete o endereço chamado, com o id da conta.
    erro = _PADRAO_CONTA_URL.sub(r"\g<prefixo>***", erro)
    return {"ok": False, "erro": erro[:1000], "latencia_ms": int((time.monotonic() - inicio) * 1000)}


async def teste_ao_vivo(llm_processador, forcar: bool = False) -> dict:
    """Testa o provedor com uma chamada curta. Reaproveita o último resultado por
    `_VALIDADE_TESTE_SEGUNDOS`, salvo com `forcar`."""
    global _ultimo_teste, _ultimo_teste_em
    if not forcar and _ultimo_teste is not None and time.monotonic() - _ultimo_teste_em < _VALIDADE_TESTE_SEGUNDOS:
        return {**_ultimo_teste, "em_cache": True}

    llm = llm_processador
    if llm is None:
        try:
            from services.llm import get_llm_provider

            llm = get_llm_provider()
        except Exception as e:
            resultado = {"ok": False, "erro": f"Provedor não pôde ser criado: {e}", "latencia_ms": None}
            llm = None
    if llm is not None:
        resultado = await _testar(llm)
    resultado["testado_em"] = serialize_utc_datetime(utc_now())
    _ultimo_teste, _ultimo_teste_em = resultado, time.monotonic()
    return {**resultado, "em_cache": False}


def uso_recente(db: Session, horas: int = 24) -> dict:
    """Contagem por situação nas últimas `horas` e o último uso com e sem sucesso."""
    desde = utc_now() - timedelta(hours=horas)
    contagem = dict(
        db.query(ComparacaoLLM.situacao, func.count(ComparacaoLLM.id))
        .filter(ComparacaoLLM.created_at >= desde)
        .group_by(ComparacaoLLM.situacao)
        .all()
    )
    ultimo = db.query(ComparacaoLLM).order_by(ComparacaoLLM.id.desc()).first()
    ultimo_ok = (
        db.query(ComparacaoLLM).filter(ComparacaoLLM.situacao == "ok").order_by(ComparacaoLLM.id.desc()).first()
    )
    return {
        "horas": horas,
        "por_situacao": contagem,
        "ultimo": (
            {
                "situacao": ultimo.situacao,
                "etapa": ultimo.etapa,
                "erro": ultimo.erro,
                "em": serialize_utc_datetime(ultimo.created_at),
                "mensagem_id": ultimo.mensagem_id,
            }
            if ultimo
            else None
        ),
        "ultimo_ok_em": serialize_utc_datetime(ultimo_ok.created_at) if ultimo_ok else None,
    }


async def status_llm(db: Session, llm_processador, forcar: bool = False) -> dict:
    teste = await teste_ao_vivo(llm_processador, forcar=forcar)
    if llm_processador is None:
        situacao, resumo = "desligado", "O processador subiu sem LLM: só regras e templates."
    elif teste["ok"]:
        situacao, resumo = "funcional", "O provedor respondeu ao teste."
    else:
        situacao, resumo = "erro", "O provedor está configurado, mas o teste falhou: o sistema segue só com regras."
    return {
        "situacao": situacao,
        "resumo": resumo,
        "provedor": settings.LLM_PROVIDER,
        "modelo": settings.LLM_MODEL,
        "endereco": mascarar_valor("LLM_BASE_URL", settings.LLM_BASE_URL)[0],
        "chave_definida": bool(settings.LLM_API_KEY),
        "carregado_no_processador": llm_processador is not None,
        "teste": teste,
        "uso_recente": uso_recente(db),
    }
