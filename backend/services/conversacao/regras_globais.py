"""
Regras globais do motor de roteamento (`services/conversacao/motor.py`) — avaliadas
independente da Fase efetiva do atendimento: ESCALAR_HUMANO, RECLAMAR, FORNECER_CNPJ,
FORNECER_CPF, a data de nascimento que completa o fluxo PF (pergunta da pilha), FORNECER_NOME
(efeito colateral silencioso), a resposta que só trata da confirmação do nome de perfil
(`confirmacao_nome_perfil.py`) e a resposta à pergunta de fechamento do atendimento
(REQ-016.10, `regras_encerramento.py`), além do projeto complexo (`projeto_complexo.py`).
São wrappers finos em cima dos helpers já existentes e testados em `ProcessadorMensagem`.

Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o funcionamento geral do motor.
"""

from __future__ import annotations

from models import Contato, MotivoEscalonamento

from services import escalonamentos as escalonamentos_svc
from services.classificador import Intencao
from services.cpf.validacao import mascarar_cpf
from services.identificador import normalizar_telefone
from services.respostas import MensagemId

from . import pilha, projeto_complexo
from .acoes import Acao, ContextoAcao, GrupoAcoes, garantir_atendimento_dispatch
from .confirmacao_nome_perfil import REGRA_RESPOSTA_SO_AO_NOME
from .motor import RegraIntencao
from .regras_encerramento import REGISTRO_ENCERRAMENTO
from .tratadores import DataNascimento

# Fluxo PF: o CPF chegou sem a data de nascimento. A pergunta da data vai para a pilha
# com o CPF nos dados; a pilha só identifica a resposta (`grava=False`) e quem completa o
# cadastro é a Regra `_builder_data_nascimento_capturada`, que precisa responder.
CHAVE_DATA_NASCIMENTO = "data_nascimento"
pilha.registrar_definicao(
    pilha.DefinicaoPergunta(chave=CHAVE_DATA_NASCIMENTO, tratador=DataNascimento(), grava=False)
)

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


async def _executar_fornecer_cnpj(ctx: ContextoAcao):
    entidades = ctx.resultado_class.entidades
    if ctx.dlog:
        ctx.dlog.log("rota", f"cnpj_fornecido={entidades.cnpjs[0]}")
    return await ctx.processador._processar_cnpj_fornecido(
        ctx.db,
        ctx.telefone,
        entidades.cnpjs[0],
        nome_informado=ctx.nome_digitado(),
    )


async def _executar_fornecer_cpf(ctx: ContextoAcao):
    p = ctx.processador
    entidades = ctx.resultado_class.entidades
    if ctx.dlog:
        ctx.dlog.log("rota", f"cpf_fornecido={mascarar_cpf(entidades.cpfs[0])}")
    data_nasc = p._parse_data_entidade(entidades, ctx.conteudo)
    resposta = await p._processar_cpf_fornecido(
        ctx.db,
        ctx.telefone,
        entidades.cpfs[0],
        nome_informado=ctx.nome_digitado(),
        data_nascimento=data_nasc,
    )
    if resposta.template_usado == MensagemId.PERGUNTAR_DATA_NASCIMENTO.name:
        _registrar_pergunta_data(ctx, entidades.cpfs[0])
    return resposta


# A pergunta em si, sem o "Anotei seu CPF." que a abre: é o que se reapresenta.
_PERGUNTA_DATA = "qual é a sua data de nascimento? (formato DD/MM/AAAA)"


def _registrar_pergunta_data(ctx: ContextoAcao, cpf: str) -> None:
    """Põe a pergunta da data na pilha do atendimento PF que `_processar_cpf_fornecido`
    acabou de criar ou reaproveitar."""
    p = ctx.processador
    telefone_norm = normalizar_telefone(ctx.telefone)
    contato = ctx.db.query(Contato).filter(Contato.telefone.in_([telefone_norm, ctx.telefone])).first()
    atendimento = p._atendimento_ativo(ctx.db, contato) if contato else None
    if atendimento is None:
        return
    ctx.atendimento = atendimento
    ctx.contato = contato
    pilha.empilhar(ctx, CHAVE_DATA_NASCIMENTO, _PERGUNTA_DATA, {"cpf": cpf})


def _builder_data_nascimento_capturada(ctx: ContextoAcao) -> GrupoAcoes:
    """Continuação do fluxo PF: a pilha reconheceu a data de nascimento que estava
    sendo esperada. A decisão de *se* a mensagem responde a essa pergunta é da pilha
    (que sabe que ela foi feita, e com qual CPF); aqui só se completa o cadastro.

    Se a mesma mensagem repete o CPF, `FORNECER_CPF` já completa com a data e esta Regra
    não contribui, para o cadastro não rodar duas vezes."""
    captura = ctx.captura_pilha
    if captura is None or captura.pergunta.chave != CHAVE_DATA_NASCIMENTO:
        return GrupoAcoes()
    if ctx.resultado_class.entidades.cpfs:
        return GrupoAcoes()

    p = ctx.processador
    cpf_pendente = (captura.pergunta.dados or {}).get("cpf")
    data_nascimento = captura.leitura.valor
    contato_pendente = ctx.identificacao.contato
    # `contato.nome` vira `Pessoa.nome` aqui, então um nome que veio do perfil do WhatsApp
    # (igual ao `ProfileName` desta mensagem), mesmo confirmado como forma de tratamento,
    # não é repassado como nome informado.
    nome_do_cliente = (
        contato_pendente.nome if contato_pendente and contato_pendente.nome != ctx.nome_perfil else None
    )

    async def _executar(ctx: ContextoAcao):
        if ctx.dlog:
            ctx.dlog.log("rota", f"data_nasc_complemento cpf={mascarar_cpf(cpf_pendente)}")
        return await p._processar_cpf_fornecido(
            ctx.db,
            ctx.telefone,
            cpf_pendente,
            nome_informado=nome_do_cliente,
            data_nascimento=data_nascimento,
        )

    return GrupoAcoes(exclusivo=[Acao("fornecer_data_nascimento", _executar)])


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
        intencao=None,
        fase=None,
        builder=_builder_data_nascimento_capturada,
        nome="fornecer_data_nascimento",
    ),
    RegraIntencao(
        intencao=Intencao.FORNECER_NOME,
        fase=None,
        builder=lambda ctx: GrupoAcoes(pre=[Acao("fornecer_nome", _executar_fornecer_nome)]),
        nome="fornecer_nome",
    ),
    REGRA_RESPOSTA_SO_AO_NOME,
] + REGISTRO_ENCERRAMENTO
