"""
Regra global de encerramento do atendimento (REQ-016.10) do motor de roteamento
(`services/conversacao/motor.py`).

O disparo da pergunta de fechamento ("Posso te ajudar em mais alguma coisa?") acontece em
`regras_esclarecendo.py`, logo após uma dúvida (categoria 3) ser respondida sem
qualificação em aberto. Este módulo só interpreta a resposta do cliente quando há uma
pergunta pendente: negativa encerra o atendimento (`motivo=concluido_pelo_cliente`);
qualquer outra coisa apenas limpa o sinalizador e deixa o resto do motor responder
normalmente (REQ-016.10: resposta afirmativa/nova demanda mantém o atendimento `ativo`).
"""

from __future__ import annotations

import re

from models import MotivoEncerramento, StatusAtendimento

from services import atendimentos as atendimentos_svc
from services.respostas import MensagemId

from .acoes import Acao, ContextoAcao, GrupoAcoes
from .motor import RegraIntencao

CHAVE_FECHAMENTO_PENDENTE = "fechamento_atendimento_pendente"

_REGEX_FECHAMENTO_NEGATIVO = re.compile(
    r"\b(n[aã]o|nao|obrigad[oa]|tudo\s+certo|era\s+s[oó]\s+isso|por\s+enquanto\s+n[aã]o|valeu)\b",
    re.IGNORECASE,
)


def _builder_resposta_fechamento(ctx: ContextoAcao) -> GrupoAcoes:
    atendimento = ctx.atendimento
    if not atendimento or atendimento.status != StatusAtendimento.ATIVO:
        return GrupoAcoes()
    if ctx.processador._info_atendimento(ctx.db, atendimento.id, CHAVE_FECHAMENTO_PENDENTE) != "aguardando":
        return GrupoAcoes()

    if _REGEX_FECHAMENTO_NEGATIVO.search(ctx.conteudo):

        async def _executar_negativa(ctx: ContextoAcao):
            p = ctx.processador
            p._remover_info_atendimento(ctx.db, atendimento.id, CHAVE_FECHAMENTO_PENDENTE)
            atendimentos_svc.encerrar_atendimento(
                ctx.db, atendimento, motivo=MotivoEncerramento.CONCLUIDO_PELO_CLIENTE, ator="cliente"
            )
            if ctx.dlog:
                ctx.dlog.log("encerramento", f"atendimento {atendimento.id} encerrado (concluido_pelo_cliente)")
            return (MensagemId.DESPEDIDA_ATENDIMENTO_ENCERRADO, None)

        return GrupoAcoes(exclusivo=[Acao("fechar_atendimento_resposta_negativa", _executar_negativa)])

    async def _executar_limpa(ctx: ContextoAcao):
        ctx.processador._remover_info_atendimento(ctx.db, atendimento.id, CHAVE_FECHAMENTO_PENDENTE)
        return None

    return GrupoAcoes(pre=[Acao("limpar_fechamento_pendente", _executar_limpa)])


REGISTRO_ENCERRAMENTO: list[RegraIntencao] = [
    RegraIntencao(
        intencao=None,
        fase=None,
        builder=_builder_resposta_fechamento,
        nome="resposta_fechamento_atendimento",
    ),
]
