"""
Registro do que o sistema faria sem o LLM e do que fez com ele (tabela `comparacoes_llm`).

Cada ponto do processamento que usa (ou usaria) o LLM chama `registrar` com o resultado
sem LLM (regras, template) e, quando o LLM respondeu, o resultado dele. Os pontos são:

- `classificacao`: a confiança das regras ficou abaixo do limite e o LLM foi consultado
  (`services/classificador.py::classificar`);
- `resposta_rag`: havia trechos da base e o LLM redigiria a resposta a partir deles;
- `personalizacao`: um template marcado para ser reescrito no tom do cliente.

O ponto é registrado mesmo sem LLM configurado (`situacao=indisponivel`) ou com o LLM
falhando (`erro`): é o que mostra, depois, onde a falta dele pesou.

A coleta vale para uma mensagem do cliente: `ProcessadorMensagem.processar` abre a
coleta (`iniciar`), e no fim grava os registros ligados à mensagem do cliente e à
mensagem de resposta que levou o texto (`gravar`). Fora de uma coleta aberta (testes,
o curador), `registrar` não faz nada.

Só o ponto em si é comparado: quando a classificação do LLM leva a um caminho diferente,
o resto da resposta que as regras dariam não é calculado (exigiria rodar o turno duas
vezes, e o turno grava estado no banco).
"""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Optional, Sequence

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Etapas
CLASSIFICACAO = "classificacao"
RESPOSTA_RAG = "resposta_rag"
PERSONALIZACAO = "personalizacao"

# Situações
OK = "ok"
ERRO = "erro"
VAZIO = "vazio"
INDISPONIVEL = "indisponivel"


@dataclass
class UsoLLM:
    etapa: str
    situacao: str
    sem_llm: str
    com_llm: Optional[str] = None
    dados: dict = field(default_factory=dict)
    erro: Optional[str] = None
    provedor: Optional[str] = None
    modelo: Optional[str] = None
    latencia_ms: Optional[int] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None

    @property
    def texto_usado(self) -> str:
        """O texto que de fato seguiu adiante: o do LLM quando ele respondeu."""
        return self.com_llm if self.situacao == OK and self.com_llm else self.sem_llm


_coleta: ContextVar[Optional[list[UsoLLM]]] = ContextVar("coleta_uso_llm", default=None)


def iniciar() -> Token:
    return _coleta.set([])


def encerrar(token: Token) -> list[UsoLLM]:
    usos = _coleta.get() or []
    _coleta.reset(token)
    return usos


def coletados() -> list[UsoLLM]:
    """Os usos coletados até agora na coleta aberta (vazio se não houver)."""
    return list(_coleta.get() or [])


def registrar(uso: UsoLLM) -> None:
    coleta = _coleta.get()
    if coleta is not None:
        coleta.append(uso)


def identificar_llm(llm) -> tuple[Optional[str], Optional[str]]:
    """(provedor, modelo) de um `LLMProvider`, ou (None, None)."""
    if llm is None:
        return None, None
    from config import settings

    return getattr(llm, "nome", None), settings.LLM_MODEL


def _mensagem_que_levou(texto: str, mensagens_saida: Sequence) -> Optional[int]:
    """A mensagem de resposta que contém o texto, ou a primeira (a classificação, por
    exemplo, não tem texto próprio na resposta)."""
    if not mensagens_saida:
        return None
    trecho = (texto or "").strip()
    if trecho:
        for msg in mensagens_saida:
            if trecho in (msg.conteudo or ""):
                return msg.id
    return mensagens_saida[0].id


def gravar(
    db: Session,
    usos: Sequence[UsoLLM],
    *,
    mensagem_id: int,
    processamento_id: Optional[int],
    mensagens_saida: Sequence,
) -> None:
    """Grava os usos coletados. Não commita: vai na transação do processamento."""
    if not usos:
        return
    from models import ComparacaoLLM

    for uso in usos:
        db.add(
            ComparacaoLLM(
                mensagem_id=mensagem_id,
                resposta_mensagem_id=_mensagem_que_levou(uso.texto_usado, mensagens_saida),
                processamento_id=processamento_id,
                etapa=uso.etapa,
                situacao=uso.situacao,
                sem_llm=uso.sem_llm,
                com_llm=uso.com_llm,
                dados=uso.dados or None,
                # A mensagem do provedor pode repetir o endereço, com o id da conta.
                erro=re.sub(r"/accounts/[^/\s]+", "/accounts/***", uso.erro or "")[:2000] or None,
                provedor=uso.provedor,
                modelo=uso.modelo,
                latencia_ms=uso.latencia_ms,
                tokens_input=uso.tokens_input,
                tokens_output=uso.tokens_output,
            )
        )
