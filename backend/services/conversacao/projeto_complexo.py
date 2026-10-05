"""
Projeto complexo (REQ-004.8): quando transferir para o time técnico, e quando esperar.

Os gatilhos: quantidade de equipamentos >= 4, faixa de funcionários acima do limiar
configurável, ou leitor facial (controle de acesso em porta é sempre complexo).

Decisão do Beto (05/10/2026): a transferência por projeto complexo espera a coleta. Se o
atendimento está (ou entra) no Finalizando, o gatilho só fica registrado
(`AtendimentoInfo[escalonamento_adiado]`), e a coleta segue até que cada pendência tenha
sido perguntada ao menos uma vez: os campos do catálogo ainda nunca perguntados e o
pedido de documento (`documento_fiscal.py`). O que já foi perguntado não é repetido.
Então transfere, com a evidência guardada no momento do gatilho. Fora do Finalizando
(não há coleta a esperar), transfere na hora, como antes. As demais transferências
(pedido do cliente, reclamação, modelo não reconhecido...) continuam imediatas.
"""

from __future__ import annotations

import json
from typing import Optional

from models import FaseAtendimento, GatilhoEscalonamento, ModoOperacao, MotivoEscalonamento

from services import escalonamentos as escalonamentos_svc
from services.classificador import EntidadesExtraidas, Intencao
from services.parametro_service import ParametroService
from services.respostas import MensagemId, RespostaGerada

from .acoes import Acao, ContextoAcao, GrupoAcoes, garantir_atendimento_dispatch
from .catalogo_campos import CAMPO_FAIXA_FUNCIONARIOS, CAMPO_QUANTIDADE

# O próprio requisito deixa o limiar em aberto ("a definir com o vendedor"); o default só
# serve se o Parametro (seed da migração) não existir por algum motivo.
LIMIAR_FUNCIONARIOS_PARAM = "escalonamento_limiar_funcionarios"
LIMIAR_FUNCIONARIOS_DEFAULT = 50
QUANTIDADE_MINIMA = 4

CHAVE_ADIADO = "escalonamento_adiado"

# Intenções que levam o atendimento para o Finalizando neste mesmo turno.
_INTENCOES_QUE_ABREM_COLETA = frozenset({Intencao.PEDIR_ORCAMENTO, Intencao.PERGUNTAR_DISPONIBILIDADE})


def gatilhos(
    entidades: EntidadesExtraidas, limiar_funcionarios: int, captura=None
) -> list[GatilhoEscalonamento]:
    """As condições de projeto complexo que esta mensagem satisfaz (todas, não só a
    primeira, para o registro do REQ-004.5B). Lista vazia = não é projeto complexo.

    `captura` é a resposta que a pilha identificou nesta mensagem (`pilha.Captura`).
    Um número solto que respondia à faixa de pessoas é a faixa, não uma quantidade de
    equipamentos, por mais que o classificador o tenha lido como quantidade (era o "45"
    que transferia um relógio de ponto para 45 pessoas)."""
    quantidades = list(entidades.quantidades)
    faixa = entidades.faixa_funcionarios
    valor = str(captura.leitura.valor) if captura is not None and captura.leitura.valor is not None else ""
    if valor.isdigit() and captura.pergunta.chave != CAMPO_QUANTIDADE.chave:
        quantidades = [q for q in quantidades if q != int(valor)]
        if captura.pergunta.chave == CAMPO_FAIXA_FUNCIONARIOS.chave and faixa is None:
            faixa = int(valor)

    encontrados = []
    if any(q >= QUANTIDADE_MINIMA for q in quantidades):
        encontrados.append(GatilhoEscalonamento.QUANTIDADE_MINIMA)
    if faixa is not None and faixa >= limiar_funcionarios:
        encontrados.append(GatilhoEscalonamento.FAIXA_FUNCIONARIOS)
    if entidades.tipo_leitor_mencionado == "facial":
        encontrados.append(GatilhoEscalonamento.LEITOR_FACIAL)
    return encontrados


def _evidencias(ctx: ContextoAcao, limiar: int) -> dict:
    entidades = ctx.resultado_class.entidades
    return {
        **escalonamentos_svc.evidencias_da_classificacao(ctx.resultado_class),
        # As três condições com valor e limiar, disparadas ou não: é o que permite dizer
        # depois se o gatilho leu certo a mensagem.
        "quantidades": list(entidades.quantidades),
        "quantidade_minima": QUANTIDADE_MINIMA,
        "faixa_funcionarios": entidades.faixa_funcionarios,
        "limiar_funcionarios": limiar,
        "tipo_leitor_mencionado": entidades.tipo_leitor_mencionado,
    }


async def _escalar(
    ctx: ContextoAcao, gatilhos_: list[GatilhoEscalonamento], evidencias: dict
) -> tuple[MensagemId, None]:
    atendimento = await garantir_atendimento_dispatch(ctx)
    await ctx.processador._escalar_atendimento(
        ctx.db,
        atendimento,
        MotivoEscalonamento.PROJETO_COMPLEXO,
        ator="sistema:projeto_complexo",
        dlog=ctx.dlog,
        gatilhos=gatilhos_,
        evidencias=evidencias,
    )
    if ctx.dlog:
        ctx.dlog.log(
            "rota",
            "projeto complexo (" + ", ".join(g.value for g in gatilhos_) + ")"
            " → PROJETO_COMPLEXO_ESCALADO + modo=HUMANO",
        )
    return (MensagemId.PROJETO_COMPLEXO_ESCALADO, None)


def _adiado(ctx: ContextoAcao) -> Optional[dict]:
    if ctx.atendimento is None:
        return None
    bruto = ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_ADIADO)
    return json.loads(bruto) if bruto else None


def adiado(ctx: ContextoAcao) -> bool:
    """Há uma transferência por projeto complexo esperando a coleta terminar?"""
    return _adiado(ctx) is not None


async def escalar_adiado(ctx: ContextoAcao) -> RespostaGerada:
    """Transfere agora, com os gatilhos e a evidência guardados quando o gatilho bateu."""
    registro = _adiado(ctx)
    ctx.processador._remover_info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_ADIADO)
    resposta = await _escalar(
        ctx,
        [GatilhoEscalonamento(g) for g in registro["gatilhos"]],
        {**registro["evidencias"], "adiado_ate_fim_da_coleta": True},
    )
    return await ctx.processador._gerador.gerar(*resposta)


def _vai_coletar(ctx: ContextoAcao) -> bool:
    """O atendimento está no Finalizando, ou entra nele neste turno."""
    if ctx.atendimento is not None and ctx.atendimento.fase == FaseAtendimento.FINALIZANDO:
        return True
    intencoes = set(ctx.resultado_class.intencoes)
    if Intencao.PEDIR_ORCAMENTO in intencoes:
        return True
    return Intencao.PERGUNTAR_DISPONIBILIDADE in intencoes and bool(ctx.resultado_class.entidades.tipos_produto)


def builder(ctx: ContextoAcao) -> GrupoAcoes:
    """Regra global (wildcard): não repete se o atendimento já está em modo humano."""
    if ctx.atendimento and ctx.atendimento.modo_operacao == ModoOperacao.HUMANO:
        return GrupoAcoes()
    limiar = ParametroService(ctx.db).get_int(LIMIAR_FUNCIONARIOS_PARAM, LIMIAR_FUNCIONARIOS_DEFAULT)
    encontrados = gatilhos(ctx.resultado_class.entidades, limiar, ctx.captura_pilha)
    if not encontrados:
        return GrupoAcoes()
    evidencias = _evidencias(ctx, limiar)

    if not _vai_coletar(ctx):

        async def _executar_agora(ctx: ContextoAcao):
            return await _escalar(ctx, encontrados, evidencias)

        return GrupoAcoes(exclusivo=[Acao("projeto_complexo", _executar_agora)])

    async def _adiar(ctx: ContextoAcao):
        atendimento = await garantir_atendimento_dispatch(ctx)
        anterior = _adiado(ctx)
        # Um gatilho novo enquanto a transferência espera soma ao registro.
        todos = list(dict.fromkeys([*(anterior or {}).get("gatilhos", []), *(g.value for g in encontrados)]))
        registro = {"gatilhos": todos, "evidencias": (anterior or {}).get("evidencias", evidencias)}
        ctx.processador._salvar_info_atendimento(
            ctx.db, atendimento.id, CHAVE_ADIADO, json.dumps(registro), pendente=False
        )
        if ctx.dlog:
            ctx.dlog.log("rota", f"projeto complexo ({', '.join(todos)}) → transferência adiada até o fim da coleta")
        return None

    return GrupoAcoes(pre=[Acao("adiar_projeto_complexo", _adiar)])
