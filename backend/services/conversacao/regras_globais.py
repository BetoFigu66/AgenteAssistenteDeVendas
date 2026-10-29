"""
Regras globais do motor de roteamento (`services/conversacao/motor.py`) — avaliadas
independente da Fase efetiva do atendimento: ESCALAR_HUMANO, RECLAMAR, FORNECER_CNPJ e
FORNECER_CPF (captura não exclusiva: registra e deixa o resto da mensagem seguir),
FORNECER_NOME (efeito colateral silencioso), a resposta que só trata da confirmação do nome de perfil
(`confirmacao_nome_perfil.py`) e a resposta à pergunta de fechamento do atendimento
(REQ-016.10, `regras_encerramento.py`), além do projeto complexo (`projeto_complexo.py`).
São wrappers finos em cima dos helpers já existentes e testados em `ProcessadorMensagem`.

Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o funcionamento geral do motor.
"""

from __future__ import annotations

from typing import Optional

from models import Contato, Empresa, MotivoEscalonamento, Pessoa

from services import escalonamentos as escalonamentos_svc
from services.classificador import Intencao
from services.cnpj.receitaws import formatar_cnpj, normalizar_cnpj
from services.cpf.validacao import formatar_cpf, mascarar_cpf, normalizar_cpf
from services.identificador import normalizar_telefone
from services.respostas import MensagemId

from . import documento_fiscal, projeto_complexo
from .acoes import Acao, ContextoAcao, GrupoAcoes, garantir_atendimento_dispatch
from .confirmacao_nome_perfil import CHAVE_NOME_PERFIL_CONFIRMACAO, CONFIRMADO, REGRA_RESPOSTA_SO_AO_NOME
from .motor import RegraIntencao
from .regras_encerramento import REGISTRO_ENCERRAMENTO


async def _executar_escalar_humano(ctx: ContextoAcao):
    """REQ-004.6: pedido explícito do cliente — escala de verdade (bug crítico
    corrigido na Fase 5: antes só respondia o template, sem setar modo humano)."""
    atendimento = await garantir_atendimento_dispatch(ctx)
    await ctx.processador._escalar_atendimento(
        ctx.db,
        atendimento,
        MotivoEscalonamento.SOLICITADO_CLIENTE,
        ator="cliente",
        dlog=ctx.dlog,
        evidencias=escalonamentos_svc.evidencias_da_classificacao(ctx.resultado_class),
    )
    if ctx.dlog:
        ctx.dlog.log("rota", "ESCALAR_HUMANO → ESCALADO_HUMANO + modo=HUMANO")
    return (MensagemId.ESCALADO_HUMANO, None)


async def _executar_reclamar(ctx: ContextoAcao):
    """REQ-004.7: reclamação/insatisfação — escala de verdade (mesmo bug corrigido
    acima). Prioridade de pós-venda (REQ-009) só se aplica na Fase 15."""
    atendimento = await garantir_atendimento_dispatch(ctx)
    await ctx.processador._escalar_atendimento(
        ctx.db,
        atendimento,
        MotivoEscalonamento.RECLAMACAO,
        ator="cliente",
        dlog=ctx.dlog,
        evidencias=escalonamentos_svc.evidencias_da_classificacao(ctx.resultado_class),
    )
    if ctx.dlog:
        ctx.dlog.log("rota", "RECLAMAR → RECLAMACAO_ESCALADA + modo=HUMANO")
    return (MensagemId.RECLAMACAO_ESCALADA, None)


def _atualizar_contexto_apos_documento(ctx: ContextoAcao) -> None:
    """Depois de capturar o documento, `ctx` passa a enxergar o contato, o atendimento e a
    empresa/pessoa recém-vinculados, para as Ações seguintes do mesmo turno (a Fase, o
    pedido de documento do início, a pergunta da nota) não agirem como se ele faltasse."""
    p = ctx.processador
    telefone_norm = normalizar_telefone(ctx.telefone)
    contato = ctx.db.query(Contato).filter(Contato.telefone.in_([telefone_norm, ctx.telefone])).first()
    if contato is None:
        return
    ctx.contato = contato
    atendimento = p._atendimento_ativo(ctx.db, contato)
    if atendimento is not None:
        ctx.atendimento = atendimento
        ctx.empresa = atendimento.empresa or ctx.empresa
        ctx.pessoa = atendimento.pessoa or ctx.pessoa


async def _executar_fornecer_cnpj(ctx: ContextoAcao):
    entidades = ctx.resultado_class.entidades
    if ctx.dlog:
        ctx.dlog.log("rota", f"cnpj_fornecido={entidades.cnpjs[0]}")
    resposta = await ctx.processador._processar_cnpj_fornecido(
        ctx.db,
        ctx.telefone,
        entidades.cnpjs[0],
        nome_informado=ctx.nome_digitado(),
    )
    ctx.registros.append(resposta)
    if resposta.template_usado == MensagemId.CNPJ_CONSULTADO_OK.name:
        _atualizar_contexto_apos_documento(ctx)
        cnpj = formatar_cnpj(normalizar_cnpj(entidades.cnpjs[0]))
        empresa = ctx.db.query(Empresa).filter_by(cnpj=cnpj).first()
        documento_fiscal.registrar_documento_capturado(ctx, empresa=empresa)
    return None


def _nome_para_pessoa(ctx: ContextoAcao) -> Optional[str]:
    """O nome que vai para `Pessoa.nome`: o digitado nesta mensagem ou, se o contato já
    tem nome, esse, exceto quando ele veio do perfil do WhatsApp, que mesmo confirmado
    como forma de tratamento não é repassado como nome informado. A origem vem do
    desfecho da confirmação, não da comparação com o `ProfileName`: depois da limpeza do
    nome de perfil, quem digita o próprio nome ("meu nome é Joaquim Barbosa") pode
    coincidir com ele."""
    digitado = ctx.nome_digitado()
    if digitado:
        return digitado
    contato = ctx.contato or ctx.identificacao.contato
    if not contato or not contato.nome:
        return None
    if ctx.atendimento and (
        ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_NOME_PERFIL_CONFIRMACAO) == CONFIRMADO
    ):
        return None
    return contato.nome


async def _executar_fornecer_cpf(ctx: ContextoAcao):
    """Sem data de nascimento desde 11/10/2026: o CPF completa o cadastro PF na hora."""
    entidades = ctx.resultado_class.entidades
    if ctx.dlog:
        ctx.dlog.log("rota", f"cpf_fornecido={mascarar_cpf(entidades.cpfs[0])}")
    resposta = await ctx.processador._processar_cpf_fornecido(
        ctx.db,
        ctx.telefone,
        entidades.cpfs[0],
        nome_informado=_nome_para_pessoa(ctx),
    )
    ctx.registros.append(resposta)
    if resposta.template_usado == MensagemId.CPF_CONSULTADO_OK.name:
        _atualizar_contexto_apos_documento(ctx)
        pessoa = ctx.db.query(Pessoa).filter_by(cpf=formatar_cpf(normalizar_cpf(entidades.cpfs[0]))).first()
        documento_fiscal.registrar_documento_capturado(ctx, pessoa=pessoa)
    return None


async def _executar_fornecer_nome(ctx: ContextoAcao):
    """Grava `contato.nome` silenciosamente quando o contato já existe e ainda não tem
    nome — unifica 3 duplicações que existiam espalhadas pelo roteador antigo. Quando
    ainda não há `Contato` (telefone totalmente novo), o nome é passado direto para quem
    cria o contato (`_garantir_contato_e_atendimento_qualificacao`/
    `_garantir_atendimento_anonimo`), então não há nada a fazer aqui nesse caso.

    O nome de perfil do WhatsApp não chega mais ao contato sem confirmação
    (`confirmacao_nome_perfil.py`), então não existe mais "nome provisório" a substituir:
    vale a regra de sempre, só preenche quem ainda não tem nome."""
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
        intencao=None,
        fase=None,
        builder=projeto_complexo.builder,
        nome="projeto_complexo",
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
        builder=lambda ctx: GrupoAcoes(pre=[Acao("fornecer_cnpj", _executar_fornecer_cnpj)]),
        nome="fornecer_cnpj",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_CPF,
        fase=None,
        builder=lambda ctx: GrupoAcoes(pre=[Acao("fornecer_cpf", _executar_fornecer_cpf)]),
        nome="fornecer_cpf",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_NOME,
        fase=None,
        builder=lambda ctx: GrupoAcoes(pre=[Acao("fornecer_nome", _executar_fornecer_nome)]),
        nome="fornecer_nome",
    ),
    REGRA_RESPOSTA_SO_AO_NOME,
] + REGISTRO_ENCERRAMENTO
