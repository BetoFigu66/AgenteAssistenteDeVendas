"""Testes do reply-to (REQ-008, Fase 10): "esta mensagem responde àquela".

Duas origens, um campo só: o "Responder" do WhatsApp (`OriginalRepliedMessageSid`,
resolvido por `Mensagem.message_sid`) e o "Responder" da interface web (id direto). É o
desempate determinístico (0) previsto para a pilha de perguntas pendentes, então o que
importa aqui é que ele seja *confiável*: resolve quando deve, e devolve `None` em vez de
apontar para a mensagem errada quando não dá.
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


def _limpar(db_session, *telefones):
    db_session.commit()
    for telefone in telefones:
        apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _msg_in_mais_recente(db_session, telefone):
    return (
        db_session.query(Mensagem)
        .filter_by(telefone=telefone, origem=OrigemMensagem.USER)
        .order_by(Mensagem.id.desc())
        .first()
    )


def test_reply_por_id_da_interface_web(db_session, processador):
    telefone = "+5511999977001"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        primeiro = asyncio.run(processador.processar(db_session, telefone, "Quero orçamento de catraca"))
        assert primeiro.mensagem_saida_id is not None

        asyncio.run(
            processador.processar(
                db_session,
                telefone,
                "17/06/1966",
                responde_a_mensagem_id=primeiro.mensagem_saida_id,
            )
        )

        msg_in = _msg_in_mais_recente(db_session, telefone)
        assert msg_in.resposta_a_mensagem_id == primeiro.mensagem_saida_id
    finally:
        _limpar(db_session, telefone)


def test_reply_por_sid_do_whatsapp(db_session, processador):
    """O caminho real: o `statusCallback` já gravou o SID na mensagem de saída, e a
    resposta citada chega com esse mesmo SID."""
    telefone = "+5511999977002"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        primeiro = asyncio.run(processador.processar(db_session, telefone, "Quero orçamento de catraca"))

        msg_out = db_session.query(Mensagem).filter_by(id=primeiro.mensagem_saida_id).first()
        msg_out.message_sid = "SM_pergunta_teste_001"
        db_session.commit()

        asyncio.run(
            processador.processar(
                db_session,
                telefone,
                "17/06/1966",
                responde_a_message_sid="SM_pergunta_teste_001",
            )
        )

        msg_in = _msg_in_mais_recente(db_session, telefone)
        assert msg_in.resposta_a_mensagem_id == msg_out.id
        assert msg_in.resposta_a_message_sid == "SM_pergunta_teste_001"
    finally:
        _limpar(db_session, telefone)


def test_sid_desconhecido_guarda_o_cru_sem_resolver(db_session, processador):
    """O `statusCallback` pode não ter chegado. Guardar o SID cru é o que distingue
    "não citou nada" de "citou algo que não conhecemos"."""
    telefone = "+5511999977003"
    try:
        asyncio.run(
            processador.processar(
                db_session,
                telefone,
                "17/06/1966",
                responde_a_message_sid="SM_nunca_visto",
            )
        )

        msg_in = _msg_in_mais_recente(db_session, telefone)
        assert msg_in.resposta_a_mensagem_id is None
        assert msg_in.resposta_a_message_sid == "SM_nunca_visto"
    finally:
        _limpar(db_session, telefone)


def test_nao_aceita_citar_mensagem_de_outra_conversa(db_session, processador):
    """O id vem do navegador e o SID, de um POST público: sem filtro por telefone,
    apontar para a mensagem de outro cliente seria só trocar um número."""
    telefone_a = "+5511999977004"
    telefone_b = "+5511999977005"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        de_a = asyncio.run(processador.processar(db_session, telefone_a, "Quero orçamento de catraca"))
        assert de_a.mensagem_saida_id is not None

        asyncio.run(
            processador.processar(
                db_session,
                telefone_b,
                "17/06/1966",
                responde_a_mensagem_id=de_a.mensagem_saida_id,
            )
        )

        msg_in = _msg_in_mais_recente(db_session, telefone_b)
        assert msg_in.resposta_a_mensagem_id is None
    finally:
        _limpar(db_session, telefone_a, telefone_b)


def test_sem_reply_nao_preenche_nada(db_session, processador):
    telefone = "+5511999977006"
    try:
        asyncio.run(processador.processar(db_session, telefone, "Quero orçamento de catraca"))
        msg_in = _msg_in_mais_recente(db_session, telefone)
        assert msg_in.resposta_a_mensagem_id is None
        assert msg_in.resposta_a_message_sid is None
    finally:
        _limpar(db_session, telefone)


def test_modo_humano_nao_devolve_mensagem_de_saida(db_session, processador):
    """`mensagem_saida_id` é o que o webhook usa para montar o `statusCallback` — sem
    resposta gerada não existe mensagem de saída para rastrear."""
    telefone = "+5511999977007"
    try:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.CONVERSA_CONTROLADA.value)
        resultado = asyncio.run(processador.processar(db_session, telefone, "Quero orçamento de catraca"))
        # Em conversa_controlada a resposta é suprimida na entrega, mas a mensagem de
        # saída existe (fica pendente de aprovação) — é ela que será entregue no /aprovar.
        assert resultado.resposta == ""
        assert resultado.mensagem_saida_id is not None
    finally:
        ParametroService(db_session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        _limpar(db_session, telefone)
