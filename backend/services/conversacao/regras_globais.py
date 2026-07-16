"""
Regras globais do motor de roteamento (`services/conversacao/motor.py`) — avaliadas
independente da Fase efetiva do atendimento: ESCALAR_HUMANO, RECLAMAR, FORNECER_CNPJ,
FORNECER_CPF, FORNECER_DATA_NASCIMENTO (continuação do fluxo PF pendente), FORNECER_NOME
(efeito colateral silencioso) e a resposta à pergunta de fechamento do atendimento
(REQ-016.10, `regras_encerramento.py`). São wrappers finos em cima dos helpers já
existentes e testados em `ProcessadorMensagem` — nenhuma lógica de negócio nova aqui.
"""

from __future__ import annotations

from models import TipoDocumento

from services.classificador import Intencao
from services.cpf.validacao import mascarar_cpf
from services.respostas import MensagemId

from .acoes import Acao, ContextoAcao, GrupoAcoes
from .motor import RegraIntencao
from .regras_encerramento import REGISTRO_ENCERRAMENTO


async def _executar_escalar_humano(ctx: ContextoAcao):
    if ctx.dlog:
        ctx.dlog.log("rota", "ESCALAR_HUMANO → ESCALADO_HUMANO")
    return (MensagemId.ESCALADO_HUMANO, None)


async def _executar_reclamar(ctx: ContextoAcao):
    if ctx.dlog:
        ctx.dlog.log("rota", "RECLAMAR → RECLAMACAO_ESCALADA")
    return (MensagemId.RECLAMACAO_ESCALADA, None)


async def _executar_fornecer_cnpj(ctx: ContextoAcao):
    entidades = ctx.resultado_class.entidades
    if ctx.dlog:
        ctx.dlog.log("rota", f"cnpj_fornecido={entidades.cnpjs[0]}")
    return await ctx.processador._processar_cnpj_fornecido(
        ctx.db,
        ctx.telefone,
        entidades.cnpjs[0],
        nome_informado=entidades.nomes[0] if entidades.nomes else None,
    )


async def _executar_fornecer_cpf(ctx: ContextoAcao):
    p = ctx.processador
    entidades = ctx.resultado_class.entidades
    if ctx.dlog:
        ctx.dlog.log("rota", f"cpf_fornecido={mascarar_cpf(entidades.cpfs[0])}")
    data_nasc = p._parse_data_entidade(entidades, ctx.conteudo)
    return await p._processar_cpf_fornecido(
        ctx.db,
        ctx.telefone,
        entidades.cpfs[0],
        nome_informado=entidades.nomes[0] if entidades.nomes else None,
        data_nascimento=data_nasc,
    )


def _builder_fornecer_data_nascimento(ctx: ContextoAcao) -> GrupoAcoes:
    """Continuação do fluxo PF: data de nascimento isolada (sem CPF na mesma mensagem)
    só significa algo se há um atendimento PF aguardando exatamente essa data
    (`cpf_pendente` em `AtendimentoInfo`) — senão a Regra não contribui nada, deixando a
    mensagem livre para as demais Regras tratarem normalmente. A checagem roda no
    *builder* (síncrono), não no `executar` — precisa decidir se é `exclusivo` ou vazio
    antes do motor montar a lista final de Ações."""
    p = ctx.processador
    data_nasc_avulsa = p._parse_data_entidade(ctx.resultado_class.entidades, ctx.conteudo)
    if not data_nasc_avulsa:
        return GrupoAcoes()

    contato_pendente = ctx.identificacao.contato
    if not contato_pendente:
        return GrupoAcoes()

    neg_pendente = p._atendimento_ativo(ctx.db, contato_pendente)
    if not (neg_pendente and neg_pendente.tipo_documento == TipoDocumento.CPF and not neg_pendente.pessoa_id):
        return GrupoAcoes()

    cpf_pendente = p._info_atendimento(ctx.db, neg_pendente.id, "cpf_pendente")
    if not cpf_pendente:
        return GrupoAcoes()

    async def _executar(ctx: ContextoAcao):
        if ctx.dlog:
            ctx.dlog.log("rota", f"data_nasc_complemento cpf={mascarar_cpf(cpf_pendente)}")
        return await p._processar_cpf_fornecido(
            ctx.db,
            ctx.telefone,
            cpf_pendente,
            nome_informado=contato_pendente.nome,
            data_nascimento=data_nasc_avulsa,
        )

    return GrupoAcoes(exclusivo=[Acao("fornecer_data_nascimento", _executar)])


async def _executar_fornecer_nome(ctx: ContextoAcao):
    """Grava `contato.nome` silenciosamente quando o contato já existe e ainda não tem
    nome — unifica 3 duplicações que existiam espalhadas pelo roteador antigo. Quando
    ainda não há `Contato` (telefone totalmente novo), o nome é passado direto para quem
    cria o contato (`_garantir_contato_e_atendimento_qualificacao`/
    `_garantir_atendimento_anonimo`), então não há nada a fazer aqui nesse caso."""
    entidades = ctx.resultado_class.entidades
    if entidades.nomes and ctx.contato and not ctx.contato.nome:
        ctx.contato.nome = entidades.nomes[0]
        ctx.db.commit()
    return None


REGRAS_GLOBAIS: list[RegraIntencao] = [
    RegraIntencao(
        intencao=Intencao.ESCALAR_HUMANO,
        fase=None,
        builder=lambda ctx: GrupoAcoes(exclusivo=[Acao("escalar_humano", _executar_escalar_humano)]),
        nome="escalar_humano",
    ),
    RegraIntencao(
        intencao=Intencao.RECLAMAR,
        fase=None,
        builder=lambda ctx: GrupoAcoes(exclusivo=[Acao("reclamar", _executar_reclamar)]),
        nome="reclamar",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_CNPJ,
        fase=None,
        builder=lambda ctx: GrupoAcoes(exclusivo=[Acao("fornecer_cnpj", _executar_fornecer_cnpj)]),
        nome="fornecer_cnpj",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_CPF,
        fase=None,
        builder=lambda ctx: GrupoAcoes(exclusivo=[Acao("fornecer_cpf", _executar_fornecer_cpf)]),
        nome="fornecer_cpf",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_DATA_NASCIMENTO,
        fase=None,
        builder=_builder_fornecer_data_nascimento,
        nome="fornecer_data_nascimento",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_NOME,
        fase=None,
        builder=lambda ctx: GrupoAcoes(pre=[Acao("fornecer_nome", _executar_fornecer_nome)]),
        nome="fornecer_nome",
    ),
] + REGISTRO_ENCERRAMENTO
