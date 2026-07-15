"""
Tipos centrais do motor de roteamento Intenção×Fase→Ações.

Substitui o antigo "a primeira intenção que bater vence" por: toda intenção que bater é
coletada; cada par (Intenção, Fase-do-atendimento) pode contribuir Ações, categorizadas em
4 grupos de execução (`TipoExecucao`). Ver `motor.py` para o gerenciador que mescla e
executa essas Ações.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, Union

from models import Atendimento, Contato, Empresa, Pessoa
from sqlalchemy.orm import Session

from services.classificador import ResultadoClassificacao
from services.debug_log import DebugLogger
from services.identificador import ResultadoIdentificacao
from services.respostas import MensagemId, RespostaGerada

if TYPE_CHECKING:
    from services.processador import ProcessadorMensagem


class TipoExecucao(str, Enum):
    """Grupo de execução de uma Ação — ver `motor.resolver_e_executar`.

    Se o grupo `EXCLUSIVO` tiver qualquer Ação, só as dele rodam (ignora PRE/
    PROCESSAMENTO/POS por completo). Generaliza escalonamento humano/reclamação como só
    mais uma Ação, sem tratamento especial no dispatcher.
    """

    PRE = "pre"
    PROCESSAMENTO = "processamento"
    POS = "pos"
    EXCLUSIVO = "exclusivo"


@dataclass
class ContextoAcao:
    """Tudo que uma Ação pode precisar para executar."""

    db: Session
    telefone: str
    conteudo: str
    identificacao: ResultadoIdentificacao
    resultado_class: ResultadoClassificacao
    processador: "ProcessadorMensagem"
    contato: Optional[Contato] = None
    empresa: Optional[Empresa] = None
    pessoa: Optional[Pessoa] = None
    atendimento: Optional[Atendimento] = None
    dlog: Optional[DebugLogger] = None
    # Fragmentos já produzidos por Ações anteriores NESTA mensagem, na ordem de execução
    # — permite que uma Ação de último recurso (ex.: pedir documento fiscal) só aja
    # quando nada mais respondeu nada ainda.
    fragmentos_ate_agora: list[RespostaGerada] = field(default_factory=list)


# Uma Ação produz: um par (MensagemId, contexto) pronto pro catálogo de templates, OU uma
# RespostaGerada já pronta (RAG/QA/LLM), OU None (efeito colateral puro, ex.: salvar nome).
RespostaFragmento = Union[tuple[MensagemId, Optional[dict]], RespostaGerada, None]


@dataclass
class Acao:
    """Uma unidade executável — nome só para auditoria/debug (dlog)."""

    nome: str
    executar: Callable[[ContextoAcao], Awaitable[RespostaFragmento]]


@dataclass
class GrupoAcoes:
    """Sempre as 4 listas — todo builder de Regra devolve isto, mesmo que vazio."""

    pre: list[Acao] = field(default_factory=list)
    processamento: list[Acao] = field(default_factory=list)
    pos: list[Acao] = field(default_factory=list)
    exclusivo: list[Acao] = field(default_factory=list)

    def __iadd__(self, outro: "GrupoAcoes") -> "GrupoAcoes":
        self.pre += outro.pre
        self.processamento += outro.processamento
        self.pos += outro.pos
        self.exclusivo += outro.exclusivo
        return self
