"""Testes do gate de modo de execução (REQ-011, Fase 2).

Diferente das demais suítes de `_decidir_resposta`, aqui o gate mora em
`ProcessadorMensagem.processar()` (nível acima) — testamos via `processar()` mesmo,
com a classificação real (regra) em vez de injetar `ResultadoClassificacao`, já que o
objetivo é o comportamento ponta a ponta do que sai (ou não) para o canal.
"""

import asyncio

import pytest
from database import Database
from models import Mensagem, ModoExecucao, OrigemMensagem
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import MODO_EXECUCAO, ParametroService
from services.processador import ProcessadorMensagem


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
    ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)


def _msg_out_mais_recente(db_session, telefone):
    return (
        db_session.query(Mensagem)
        .filter_by(telefone=telefone, origem=OrigemMensagem.SYSTEM)
        .order_by(Mensagem.id.desc())
        .first()
    )


def test_execucao_normal_envia_direto_e_auto_aprova(db_session, processador):
    telefone = "5511999988001"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        resultado = asyncio.run(
            processador.processar(db_session, telefone, "Quero orçamento de catraca")
        )
        assert resultado.resposta != ""

        msg_out = _msg_out_mais_recente(db_session, telefone)
        assert msg_out is not None
        assert msg_out.conteudo == resultado.resposta
        assert msg_out.pendente_aprovacao is False
        assert msg_out.aprovador_id is not None
    finally:
        _limpar(db_session, telefone)


def test_conversa_controlada_fica_pendente_sem_envio(db_session, processador):
    telefone = "5511999988002"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.CONVERSA_CONTROLADA.value)
        resultado = asyncio.run(
            processador.processar(db_session, telefone, "Quero orçamento de catraca")
        )
        assert resultado.resposta == ""

        msg_out = _msg_out_mais_recente(db_session, telefone)
        assert msg_out is not None
        assert msg_out.conteudo != ""  # texto completo preservado para aprovação posterior
        assert msg_out.pendente_aprovacao is True
        assert msg_out.aprovador_id is None
    finally:
        _limpar(db_session, telefone)


def test_simulacao_fica_pendente_sem_envio(db_session, processador):
    telefone = "5511999988003"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.SIMULACAO.value)
        resultado = asyncio.run(
            processador.processar(db_session, telefone, "Quero orçamento de catraca")
        )
        assert resultado.resposta == ""

        msg_out = _msg_out_mais_recente(db_session, telefone)
        assert msg_out is not None
        assert msg_out.pendente_aprovacao is True
    finally:
        _limpar(db_session, telefone)


def test_aprovar_mensagem_pendente_libera_conteudo_original(db_session, processador):
    """A mensagem pendente preserva o texto completo — aprovar via
    `/api/mensagens/{id}/aprovar` (fora do escopo deste teste) é o que de fato libera o
    envio; aqui validamos que o texto não se perde enquanto pendente."""
    telefone = "5511999988004"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.CONVERSA_CONTROLADA.value)
        asyncio.run(processador.processar(db_session, telefone, "Quero orçamento de catraca"))

        msg_out = _msg_out_mais_recente(db_session, telefone)
        assert msg_out.conteudo
        assert msg_out.feedback_aprovacao is None
        assert msg_out.segundos_pendente is not None
        assert msg_out.segundos_pendente >= 0
    finally:
        _limpar(db_session, telefone)
