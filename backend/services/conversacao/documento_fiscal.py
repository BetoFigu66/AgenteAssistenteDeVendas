"""
Pedido de CNPJ/CPF ao longo do atendimento.

O documento é pedido **no início do atendimento, junto com o nome**, sem ser obrigatório
(decisão do Beto, 05/10/2026). Em Esclarecendo ele não é repetido: a resposta sem
documento marca `recusado` (`estados/esclarecendo.py`).

No Finalizando, antes do resumo (ou antes de transferir um projeto complexo), o documento
é tratado como **o da nota fiscal**, uma vez só (decisão do Beto, 11/10/2026):

- já foi dado: pergunta se a nota sai nele (`CONFIRMAR_DOCUMENTO_NF_*`). "Sim" confirma;
  outro documento na resposta passa a ser o da nota; "não" sem documento pede o número
  (`PEDIR_DOCUMENTO_NF`), também uma vez só;
- não foi dado: pede o da nota (`PEDIR_DOCUMENTO_NF`).

Sem resposta, o resumo segue sem documento e o vendedor resolve.

Estado em `AtendimentoInfo[documento_fiscal_pendente]`: `solicitado` (pedido no início),
`recusado` (a mensagem seguinte não trouxe documento), `confirmando_nf` (perguntou se a
nota sai no documento dado), `trocar_nf` (o cliente disse que não, sem dar outro),
`pedido_finalizando` (pediu o documento da nota) e `nf_confirmada`.

O pedido do documento não entra na pilha de perguntas pendentes: CNPJ e CPF se
identificam sozinhos e as Regras globais `FORNECER_CNPJ`/`FORNECER_CPF` os capturam a
qualquer momento, e a retomada após dúvida (D1) o repetiria em Esclarecendo, contra a
regra acima. A confirmação da nota entra (`CHAVE_CONFIRMACAO_NF`), porque o "sim" e o
"não" dela precisam ser lidos.
"""

from __future__ import annotations

from typing import Optional

from models import Empresa, Pessoa, StatusPergunta, TipoDocumento

from services import atendimentos as atendimentos_svc
from services.respostas import MensagemId, renderizar_mensagem

from . import pilha
from .acoes import ContextoAcao
from .tratadores import SimNao

CHAVE_DOC_PENDENTE = "documento_fiscal_pendente"
SOLICITADO = "solicitado"
RECUSADO = "recusado"
CONFIRMANDO_NF = "confirmando_nf"
TROCAR_NF = "trocar_nf"
PEDIDO_FINALIZANDO = "pedido_finalizando"
NF_CONFIRMADA = "nf_confirmada"

# Estados em que a pergunta da nota já foi feita: um documento que chega agora é o da nota.
_PERGUNTA_NF_FEITA = frozenset({CONFIRMANDO_NF, TROCAR_NF, PEDIDO_FINALIZANDO})

CHAVE_CONFIRMACAO_NF = "confirmacao_documento_nf"


def _tem_documento(ctx: ContextoAcao) -> bool:
    atendimento = ctx.atendimento
    if ctx.empresa or ctx.pessoa or (atendimento and (atendimento.empresa_id or atendimento.pessoa_id)):
        return True
    entidades = ctx.resultado_class.entidades
    return bool(entidades.cnpjs or entidades.cpfs)


def _estado(ctx: ContextoAcao) -> Optional[str]:
    return ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_DOC_PENDENTE)


def _marcar(ctx: ContextoAcao, estado: str) -> None:
    ctx.processador._salvar_info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_DOC_PENDENTE, estado)


def pedido_inicial(ctx: ContextoAcao) -> Optional[tuple[MensagemId, None]]:
    """A parte que pede o documento no início do atendimento, ou None se ele já foi
    dado ou já foi pedido. Exige `ctx.atendimento`."""
    if _tem_documento(ctx) or _estado(ctx):
        return None
    _marcar(ctx, SOLICITADO)
    if ctx.dlog:
        ctx.dlog.log("documento", "pedido no início do atendimento")
    return (MensagemId.PEDIR_DOCUMENTO, None)


# ----------------------------------------------------------------------
# Documento da nota fiscal (Finalizando)
# ----------------------------------------------------------------------


def _aplicar_confirmacao_nf(ctx: ContextoAcao, pergunta, leitura) -> None:
    _marcar(ctx, NF_CONFIRMADA if leitura.valor == "sim" else TROCAR_NF)


pilha.registrar_definicao(
    pilha.DefinicaoPergunta(
        chave=CHAVE_CONFIRMACAO_NF,
        tratador=SimNao(),
        aplicar=_aplicar_confirmacao_nf,
        max_tentativas=1,
    )
)


def _confirmacao(ctx: ContextoAcao) -> Optional[tuple[MensagemId, Optional[dict]]]:
    """A pergunta de confirmação para o documento que o atendimento já tem, ou None. Com
    os dois, vale o último informado (`tipo_documento`)."""
    atendimento = ctx.atendimento
    if atendimento is None:
        return None
    empresa = atendimento.empresa
    if empresa and (atendimento.tipo_documento == TipoDocumento.CNPJ or not atendimento.pessoa_id):
        return (MensagemId.CONFIRMAR_DOCUMENTO_NF_CNPJ, {"empresa": empresa.nome})
    if atendimento.pessoa_id:
        return (MensagemId.CONFIRMAR_DOCUMENTO_NF_CPF, None)
    return None


def pergunta_nf(ctx: ContextoAcao) -> Optional[tuple[MensagemId, Optional[dict]]]:
    """No Finalizando, antes do resumo: a pergunta sobre o documento da nota que ainda
    cabe fazer, ou None (já confirmada, ou já perguntada sem resposta)."""
    estado = _estado(ctx)
    if estado in (NF_CONFIRMADA, PEDIDO_FINALIZANDO, CONFIRMANDO_NF):
        return None
    if estado != TROCAR_NF:
        confirmacao = _confirmacao(ctx)
        if confirmacao is not None:
            _marcar(ctx, CONFIRMANDO_NF)
            mensagem_id, contexto = confirmacao
            pilha.empilhar(ctx, CHAVE_CONFIRMACAO_NF, renderizar_mensagem(mensagem_id, contexto)[0])
            if ctx.dlog:
                ctx.dlog.log("documento", f"confirma o documento da nota ({mensagem_id.name})")
            return confirmacao
    _marcar(ctx, PEDIDO_FINALIZANDO)
    if ctx.dlog:
        ctx.dlog.log("documento", "pede o documento da nota (uma vez só)")
    return (MensagemId.PEDIR_DOCUMENTO_NF, None)


def registrar_documento_capturado(
    ctx: ContextoAcao, empresa: Optional[Empresa] = None, pessoa: Optional[Pessoa] = None
) -> None:
    """Chamado por quem captura um CNPJ/CPF válido. Se a pergunta da nota já foi feita,
    o documento que chegou é o da nota: substitui o do atendimento e encerra a pergunta
    de confirmação que estiver aberta."""
    atendimento = ctx.atendimento
    if atendimento is None or _estado(ctx) not in _PERGUNTA_NF_FEITA:
        return
    atendimentos_svc.definir_documento_nota(ctx.db, atendimento, empresa=empresa, pessoa=pessoa)
    _marcar(ctx, NF_CONFIRMADA)
    for pergunta in pilha.abertas(atendimento):
        if pergunta.chave == CHAVE_CONFIRMACAO_NF:
            pilha.encerrar(pergunta, StatusPergunta.RESPONDIDA, "outro documento")
    if ctx.dlog:
        ctx.dlog.log("documento", "documento informado depois da pergunta da nota → é o da nota")
