"""Dúvidas do cliente que caem numa ação exclusiva (`services/conversacao/duvidas_pendentes.py`).

Decisão do Beto (11/10/2026): a ação exclusiva (aqui, o pedido de atendente) descarta o
resto da mensagem, e a dúvida que vinha junto é registrada para o operador, que a
responde e marca como resolvida.
"""

import asyncio

import pytest
from database import Database
from models import DuvidaPendente, ModoExecucao, ModoOperacao, StatusDuvida
from services.conversacao import duvidas_pendentes
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    with Database().get_session() as session:
        yield session
        session.rollback()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _processar(db_session, telefone, texto):
    resultado = asyncio.run(ProcessadorMensagem().processar(db_session, telefone, texto))
    db_session.commit()
    return resultado


def test_duvida_junto_do_pedido_de_atendente_vai_para_o_operador(db_session):
    telefone = "+5500900000311"
    _limpar(db_session, telefone)
    try:
        resultado = _processar(db_session, telefone, "quero falar com um atendente, e vocês têm catraca facial?")

        (duvida,) = db_session.query(DuvidaPendente).filter_by(atendimento_id=resultado.atendimento_id).all()
        assert duvida.texto == "quero falar com um atendente, e vocês têm catraca facial?"
        assert duvida.intencao == "perguntar_produto"
        assert duvida.acao_exclusiva == "escalar_humano"
        assert duvida.mensagem_id is not None
        assert duvida.atendimento.modo_operacao == ModoOperacao.HUMANO

        duvidas_pendentes.resolver(db_session, duvida, usuario_id=None)
        assert duvida.status == StatusDuvida.RESOLVIDA.value
        assert duvidas_pendentes.pendentes(db_session, resultado.atendimento_id) == []
    finally:
        _limpar(db_session, telefone)


def test_pedido_de_atendente_sem_duvida_nao_registra(db_session):
    telefone = "+5500900000312"
    _limpar(db_session, telefone)
    try:
        resultado = _processar(db_session, telefone, "quero falar com um atendente")
        assert db_session.query(DuvidaPendente).filter_by(atendimento_id=resultado.atendimento_id).count() == 0
    finally:
        _limpar(db_session, telefone)
