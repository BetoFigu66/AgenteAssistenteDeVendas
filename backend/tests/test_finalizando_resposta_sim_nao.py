"""Respostas "sim"/"não" à pergunta pendente, com a intenção que o classificador REALMENTE
produz.

Os testes de `test_processador_finalizando_coleta_ativa.py` cobrem a captura solta injetando
`Intencao.DESCONHECIDO` em todas as chamadas, inclusive quando o conteúdo é literalmente
"sim". Isso constrói justamente o cenário que o defeito não atinge: na vida real o
classificador reconhece "sim" isolado como `CONFIRMAR` e "não" isolado como `NEGAR`
(`services/classificador.py`, regras ancoradas em `^...$`), e a captura era abandonada antes
de olhar o campo pendente.

Efeito para o cliente: o bot repetia a pergunta que ele acabara de responder. Mesmo sintoma
do P0-2 da auditoria de agosto (commit `6455022`), por outra causa.

Estes testes usam a intenção real, então falham sem a correção em
`FinalizandoState._capturar_resposta_direta_pendente`.
"""

import asyncio

import pytest
from database import Database
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao
from services.processador import ProcessadorMensagem

from tests.test_processador_finalizando_coleta_ativa import (
    _iniciar_finalizando_catraca,
    _iniciar_finalizando_com_software,
    _resolver_modelo_catraca_manual,
    _resolver_modelo_manual,
)


def _resultado(intencao: Intencao, **entidades_kwargs) -> ResultadoClassificacao:
    return ResultadoClassificacao(
        intencoes=[intencao],
        confianca=0.9,
        confianca_nivel=NivelConfianca.ALTA,
        entidades=EntidadesExtraidas(**entidades_kwargs),
        origem="regra",
    )


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _valores(db_session, atendimento) -> dict:
    db_session.refresh(atendimento)
    return {info.chave: info.valor for info in atendimento.informacoes}


def _responder(processador, db_session, telefone, contato, conteudo, intencao):
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
    return asyncio.run(
        processador._decidir_resposta(
            db=db_session,
            telefone=telefone,
            conteudo=conteudo,
            identificacao=identificacao,
            resultado_class=_resultado(intencao),
        )
    )


def _chegar_em_pergunta_nuvem(db_session, processador, telefone):
    """Catraca sem software de acesso: o próximo pendente passa a ser o interesse em nuvem."""
    contato = _iniciar_finalizando_catraca(db_session, processador, telefone)
    atendimento = contato.atendimentos[0]
    _resolver_modelo_catraca_manual(db_session, atendimento)
    resposta = _responder(processador, db_session, telefone, contato, "nenhum", Intencao.DESCONHECIDO)
    assert resposta.template_usado == "PEDIR_INTERESSE_SISTEMA_NUVEM"
    return contato, atendimento


def test_sim_classificado_como_confirmar_captura_interesse_nuvem(db_session, processador):
    """O caso que o defeito atingia: "sim" vira CONFIRMAR e a resposta era descartada."""
    telefone = "5511999982001"
    try:
        contato, atendimento = _chegar_em_pergunta_nuvem(db_session, processador, telefone)

        resposta = _responder(processador, db_session, telefone, contato, "sim", Intencao.CONFIRMAR)

        assert _valores(db_session, atendimento).get("interesse_sistema_nuvem") == "sim"
        # E o fluxo avança, em vez de repetir a pergunta que o cliente acabou de responder.
        assert resposta.template_usado == "PEDIR_FAIXA_FUNCIONARIOS"
    finally:
        _limpar(db_session, telefone)


def test_nao_classificado_como_negar_captura_interesse_nuvem(db_session, processador):
    telefone = "5511999982002"
    try:
        contato, atendimento = _chegar_em_pergunta_nuvem(db_session, processador, telefone)

        resposta = _responder(processador, db_session, telefone, contato, "não", Intencao.NEGAR)

        assert _valores(db_session, atendimento).get("interesse_sistema_nuvem") == "não"
        # Sem interesse em nuvem, a faixa de funcionários (que serve ao licenciamento do
        # sistema) deixa de se aplicar e o fluxo salta para a quantidade. Ou seja: o "não"
        # não só foi gravado, como mudou o que o planejador pergunta em seguida.
        assert resposta.template_usado == "PEDIR_QUANTIDADE"
    finally:
        _limpar(db_session, telefone)


def test_nao_classificado_como_negar_captura_software_de_ponto(db_session, processador):
    """"Não" para "qual software vocês usam?" é a resposta "não temos", não uma negativa solta.

    O ramo do campo já sabia traduzir a sentinela de negação para "nenhum"; a mensagem é que
    nunca chegava até ele.
    """
    telefone = "5511999982003"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        _responder(processador, db_session, telefone, contato, "não", Intencao.NEGAR)

        assert _valores(db_session, atendimento).get("software_controle_ponto") == "nenhum"
    finally:
        _limpar(db_session, telefone)


def test_intencao_reconhecida_sem_relacao_nao_e_sequestrada_como_resposta(db_session, processador):
    """Regressão do que o gate original protegia, e que precisa continuar valendo.

    Uma intenção reconhecida que não tem nada a ver com a pergunta pendente (o cliente repete
    "quero orçamento") não pode ser lida como se fosse a resposta dela.
    """
    telefone = "5511999982004"
    try:
        contato, atendimento = _chegar_em_pergunta_nuvem(db_session, processador, telefone)

        _responder(processador, db_session, telefone, contato, "quero orçamento", Intencao.PEDIR_ORCAMENTO)

        assert "interesse_sistema_nuvem" not in _valores(db_session, atendimento)
    finally:
        _limpar(db_session, telefone)


def test_negativa_dentro_da_frase_nao_vira_sim(db_session, processador):
    """"não quero" não pode ser lido como "sim".

    `_RESPOSTA_SIM_REGEX` contém "quero", então testar o afirmativo primeiro fazia "não
    quero" casar com o ramo do sim. A negação tem que ser avaliada antes.
    """
    telefone = "5511999982005"
    try:
        contato, atendimento = _chegar_em_pergunta_nuvem(db_session, processador, telefone)

        _responder(processador, db_session, telefone, contato, "não quero", Intencao.DESCONHECIDO)

        assert _valores(db_session, atendimento).get("interesse_sistema_nuvem") == "não"
    finally:
        _limpar(db_session, telefone)
