"""Teste do feedback textual opcional na aprovação de mensagem (REQ-011.6, Fase 2)."""

import pytest
from database import Database
from models import Mensagem, OrigemMensagem
from services.dev_limpeza_telefone import apagar_dados_telefone


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _criar_mensagem_pendente(db_session, telefone) -> int:
    msg = Mensagem(telefone=telefone, conteudo="Resposta gerada pela IA", origem=OrigemMensagem.SYSTEM)
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    return msg.id


def test_aprovar_com_feedback_persiste_texto(client, db_session):
    telefone = "5511999988101"
    try:
        mensagem_id = _criar_mensagem_pendente(db_session, telefone)

        r = client.post(
            f"/api/mensagens/{mensagem_id}/aprovar",
            json={"feedback": "Correto, mas poderia ser mais direto"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["feedback_aprovacao"] == "Correto, mas poderia ser mais direto"
        assert body["pendente_aprovacao"] is False
    finally:
        _limpar(db_session, telefone)


def test_aprovar_sem_feedback_fica_none(client, db_session):
    telefone = "5511999988102"
    try:
        mensagem_id = _criar_mensagem_pendente(db_session, telefone)

        r = client.post(f"/api/mensagens/{mensagem_id}/aprovar", json={})
        assert r.status_code == 200
        assert r.json()["feedback_aprovacao"] is None
    finally:
        _limpar(db_session, telefone)
