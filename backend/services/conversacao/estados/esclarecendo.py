"""`EsclarecendoState` — comportamento da fase Esclarecendo.

Hoje só tem um método real: a "ação padrão" (wildcard) da fase, movida de
`regras_esclarecendo.py::_executar_acao_padrao_esclarecendo` — o restante do
comportamento de Esclarecendo já era corretamente escopado como Ações/builders no próprio
`regras_esclarecendo.py` (não delegava para `ProcessadorMensagem`), então não há mais nada
fase-específico a extrair daqui por enquanto.
"""

from __future__ import annotations

from models import FaseAtendimento

from services.classificador import Intencao
from services.conversacao.acoes import ContextoAcao, RespostaFragmento, garantir_atendimento_dispatch
from services.identificador import StatusIdentificacao
from services.respostas import MensagemId

from .base import EstadoAtendimento

_CHAVE_DOC_PENDENTE = "documento_fiscal_pendente"


class EsclarecendoState(EstadoAtendimento):
    fase = FaseAtendimento.ESCLARECENDO

    async def tratamento_principal(self, ctx: ContextoAcao) -> RespostaFragmento:
        """Último recurso do turno — só age se nada mais respondeu nada. Trata: (a) SAUDACAO
        pra quem já está identificado (empresa/pessoa), respondendo com o nome; (b) fallback
        QA/NAO_ENTENDI pra quem já está identificado e não disse "oi"; (c) o fluxo de
        documento fiscal pendente pra quem ainda não tem empresa/pessoa vinculada.

        (c) só pergunta documento **uma vez**: se `documento_fiscal_pendente` já está
        "solicitado" e chegamos aqui de novo, é porque esta mensagem não trouxe CNPJ/CPF (se
        tivesse, a regra global `FORNECER_CNPJ`/`FORNECER_CPF`, que é `exclusivo`, já teria
        resolvido antes — nunca chegaríamos até aqui) — não insiste de novo, marca "recusado"
        e segue a conversa normalmente (fallback QA/NAO_ENTENDI). Não depende de reconhecer a
        recusa por palavra (ex.: "não quero fornecer ainda" não bate na regra `NEGAR`, que
        exige a mensagem inteira ser só "não")."""
        if ctx.fragmentos_ate_agora:
            return None
        if ctx.atendimento and ctx.atendimento.fase != FaseAtendimento.ESCLARECENDO:
            return None

        p = ctx.processador

        if ctx.empresa or ctx.pessoa:
            nome = (ctx.contato.nome if ctx.contato else None) or (ctx.pessoa.nome if ctx.pessoa else None)
            if Intencao.SAUDACAO in ctx.resultado_class.intencoes:
                if nome:
                    return (MensagemId.SAUDACAO_COM_NOME, {"nome": nome})
                return (MensagemId.PERGUNTAR_NOME, None)
            return await p._fallback_qa_ou_nao_entendi(
                ctx.conteudo, resultado_class=ctx.resultado_class, db=ctx.db, atendimento=ctx.atendimento,
                dlog=ctx.dlog,
            )

        atendimento = await garantir_atendimento_dispatch(ctx)
        estado_doc = p._info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE)

        if estado_doc in ("solicitado", "recusado"):
            if estado_doc == "solicitado":
                p._salvar_info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE, "recusado")
                if ctx.dlog:
                    ctx.dlog.log(
                        "esclarecendo",
                        "documento pedido sem resposta → marcado 'recusado', não insiste mais",
                    )
            elif ctx.dlog:
                ctx.dlog.log("esclarecendo", "documento_fiscal_pendente=recusado → não repete, cai no fallback")
            return await p._fallback_qa_ou_nao_entendi(
                ctx.conteudo, resultado_class=ctx.resultado_class, db=ctx.db, atendimento=atendimento, dlog=ctx.dlog
            )

        p._salvar_info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE, "solicitado")

        if ctx.identificacao.status == StatusIdentificacao.NOVO:
            entidades = ctx.resultado_class.entidades
            ctx_novo = {
                "nome": entidades.nomes[0] if entidades.nomes else None,
                "tem_documento": bool(entidades.cnpjs or entidades.cpfs),
                "modo": "identificacao",
            }
            return (MensagemId.SAUDACAO_NOVO_CONTATO, ctx_novo)

        nome_contato = atendimento.contato.nome if atendimento.contato else None
        return (MensagemId.PERGUNTAR_CNPJ, {"nome": nome_contato})


ESCLARECENDO = EsclarecendoState()
