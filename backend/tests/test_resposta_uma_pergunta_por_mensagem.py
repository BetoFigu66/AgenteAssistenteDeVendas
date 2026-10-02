"""Uma pergunta por mensagem de WhatsApp (decisão do Beto, 02/10).

Uma resposta composta de várias perguntas sai em várias mensagens, para o cliente poder
citar cada uma no "Responder" e responder em qualquer ordem. Partes sem pergunta vão
junto com a pergunta seguinte, para não virarem mensagens soltas. Cada mensagem tem a
sua aprovação (opção (a)), e no webhook cada uma vira uma tag `<Message>` com o próprio
`statusCallback`.

O modo de execução vem de um dublê, como em `test_processador_nome_perfil.py`: o banco é
compartilhado com o backend que estiver no ar.
"""

import asyncio

import pytest
from config import settings
from database import Database
from models import Mensagem, ModoExecucao, OrigemMensagem
from services.canal.factory import obter_canal
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem
from services.respostas import RespostaGerada

from tests.test_webhook_entrega import _CanalTwilioFake

_MENSAGEM_CLIENTE = "Bom dia, gostaria de informações sobre relógio de ponto."
_NOME_PERFIL = "Bob Figu"


# ----------------------------------------------------------------------
# RespostaGerada.mensagens(): onde a resposta é cortada
# ----------------------------------------------------------------------


def test_sem_partes_e_uma_mensagem_so():
    assert RespostaGerada(texto="Oi? Tudo bem?").mensagens() == ["Oi? Tudo bem?"]
    assert RespostaGerada(texto="").mensagens() == []


def test_cada_pergunta_em_uma_mensagem():
    resposta = RespostaGerada(texto="", partes=["Posso te chamar assim?", "Conhece?", "Qual a faixa?"])
    assert resposta.mensagens() == ["Posso te chamar assim?", "Conhece?", "Qual a faixa?"]


def test_parte_sem_pergunta_vai_junto_com_a_pergunta_seguinte():
    resposta = RespostaGerada(texto="", partes=["Olá!", "Vou precisar de informações.", "Qual o modelo?"])
    assert resposta.mensagens() == ["Olá!\n\nVou precisar de informações.\n\nQual o modelo?"]


def test_parte_sem_pergunta_no_fim_vai_com_a_ultima_mensagem():
    resposta = RespostaGerada(texto="", partes=["Qual o modelo?", "Qual a faixa?", "Obrigado."])
    assert resposta.mensagens() == ["Qual o modelo?", "Qual a faixa?\n\nObrigado."]


def test_nenhuma_pergunta_e_uma_mensagem_so():
    resposta = RespostaGerada(texto="", partes=["Anotado.", "Obrigado."])
    assert resposta.mensagens() == ["Anotado.\n\nObrigado."]


def test_dividir_de_novo_nao_muda_nada():
    """O motor junta fragmentos que já vieram divididos: dividir de novo tem que dar o
    mesmo resultado."""
    original = RespostaGerada(texto="", partes=["Olá!", "Conhece?", "Qual a faixa?", "Até."])
    redividida = RespostaGerada(texto="", partes=original.mensagens())
    assert redividida.mensagens() == original.mensagens()


# ----------------------------------------------------------------------
# Processador: uma Mensagem por pergunta, cada uma com a sua aprovação
# ----------------------------------------------------------------------


def _mensagens_saida(session, telefone):
    session.expire_all()
    return (
        session.query(Mensagem)
        .filter_by(telefone=telefone, origem=OrigemMensagem.SYSTEM)
        .order_by(Mensagem.id)
        .all()
    )


def _limpar(telefone):
    with Database().get_session() as session:
        apagar_dados_telefone(session, telefone)
        session.commit()


def _processar(monkeypatch, telefone, modo):
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: modo)
    with Database().get_session() as session:
        resultado = asyncio.run(
            ProcessadorMensagem().processar(session, telefone, _MENSAGEM_CLIENTE, nome_perfil=_NOME_PERFIL)
        )
        session.commit()
        return resultado


def test_tres_perguntas_viram_tres_mensagens_pendentes(monkeypatch):
    """O caso que motivou a mudança: confirmação do nome + disponibilidade + faixa."""
    telefone = "+5511999977201"
    try:
        resultado = _processar(monkeypatch, telefone, ModoExecucao.SIMULACAO)
        assert resultado.resposta == ""
        assert resultado.partes_resposta == []

        with Database().get_session() as session:
            msgs = _mensagens_saida(session, telefone)
            assert [m.id for m in msgs] == resultado.mensagens_saida_ids
            assert len(msgs) == 3
            assert msgs[0].conteudo.startswith("Olá, Bob Figu!")
            assert msgs[0].conteudo.endswith("Posso te chamar assim ou seu nome é outro?")
            assert msgs[1].conteudo.startswith("Sim, vendemos.")
            assert msgs[2].conteudo == "Qual a faixa de pessoas que vão usar o relógio de ponto?"
            for msg in msgs:
                assert msg.conteudo.count("?") == 1
                assert msg.aprovador_id is None and msg.timestamp_aprovacao is None
    finally:
        _limpar(telefone)


def test_execucao_normal_auto_aprova_cada_mensagem(monkeypatch):
    telefone = "+5511999977202"
    try:
        resultado = _processar(monkeypatch, telefone, ModoExecucao.EXECUCAO_NORMAL)

        with Database().get_session() as session:
            msgs = _mensagens_saida(session, telefone)
            assert len(msgs) == 3
            assert resultado.partes_resposta == [m.conteudo for m in msgs]
            assert resultado.resposta == "\n\n".join(resultado.partes_resposta)
            assert all(m.aprovador_id is not None for m in msgs)
    finally:
        _limpar(telefone)


def test_aprovar_uma_nao_aprova_as_outras(monkeypatch, client, _canal_limpo):
    telefone = "+5511999977203"
    # Aprovar entrega: o canal simulado garante que nada sai para o WhatsApp.
    monkeypatch.setattr(settings, "CANAL_SAIDA", "simulado")
    try:
        resultado = _processar(monkeypatch, telefone, ModoExecucao.SIMULACAO)
        primeira, *demais = resultado.mensagens_saida_ids

        r = client.post(f"/api/mensagens/{primeira}/aprovar", json={})
        assert r.status_code == 200

        with Database().get_session() as session:
            msgs = {m.id: m for m in _mensagens_saida(session, telefone)}
            assert msgs[primeira].aprovador_id is not None
            assert all(msgs[i].aprovador_id is None for i in demais)
    finally:
        _limpar(telefone)


# ----------------------------------------------------------------------
# Webhook: uma tag <Message> por mensagem
# ----------------------------------------------------------------------


@pytest.fixture
def _canal_limpo():
    obter_canal.cache_clear()
    yield
    obter_canal.cache_clear()


def _post_webhook(client, telefone, **extra):
    dados = {"From": f"whatsapp:{telefone}", "Body": _MENSAGEM_CLIENTE, "ProfileName": _NOME_PERFIL}
    dados.update(extra)
    return client.post("/webhook", data=dados)


def test_chamada_local_recebe_uma_tag_por_mensagem(monkeypatch, client, _canal_limpo):
    telefone = "+5511999977204"
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    try:
        r = _post_webhook(client, telefone)
        assert r.status_code == 200
        assert r.text.count("<Message>") == 3
    finally:
        _limpar(telefone)


def test_twilio_modo_twiml_tem_status_callback_por_mensagem(monkeypatch, client, _canal_limpo):
    telefone = "+5511999977205"
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    canal = _CanalTwilioFake(modo_envio="twiml")
    monkeypatch.setattr("main.obter_canal", lambda: canal)
    try:
        r = _post_webhook(client, telefone, AccountSid="AC_real")
        assert r.status_code == 200

        with Database().get_session() as session:
            msgs = _mensagens_saida(session, telefone)
            assert len(msgs) == 3
            assert r.text.count("<Message statusCallback=") == 3
            # Na ordem de envio, cada tag apontando para a sua mensagem.
            posicoes = [r.text.index(f"mensagem_id={m.id}") for m in msgs]
            assert posicoes == sorted(posicoes)
            assert all(m.timestamp_envio is not None for m in msgs)
    finally:
        _limpar(telefone)


def test_twilio_modo_rest_envia_cada_mensagem_em_ordem(monkeypatch, client, _canal_limpo):
    telefone = "+5511999977206"
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    canal = _CanalTwilioFake(modo_envio="rest")
    monkeypatch.setattr("main.obter_canal", lambda: canal)
    try:
        r = _post_webhook(client, telefone, AccountSid="AC_real")
        assert "<Message" not in r.text

        with Database().get_session() as session:
            msgs = _mensagens_saida(session, telefone)
            assert [(t, mid) for _, t, mid in canal.enviados] == [(m.conteudo, m.id) for m in msgs]
            assert all(m.message_sid == f"SM_fake_{m.id}" for m in msgs)
    finally:
        _limpar(telefone)
