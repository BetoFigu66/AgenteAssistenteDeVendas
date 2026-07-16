"""Teste do feedback textual opcional na aprovação de mensagem (REQ-011.6, Fase 2)."""

import pytest
from database import Database
from fastapi.testclient import TestClient
from models import Mensagem, OrigemMensagem, User
from services.dev_limpeza_telefone import apagar_dados_telefone


@pytest.fixture
def client():
    import main

    with TestClient(main.app) as c:
        yield c


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


def _obter_ou_criar_user(db_session, nome: str) -> int:
    user = db_session.query(User).filter_by(nome=nome).first()
    if user is None:
        user = User(nome=nome)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user.id


def test_aprovar_com_feedback_persiste_texto(client, db_session):
    telefone = "5511999988101"
    try:
        mensagem_id = _criar_mensagem_pendente(db_session, telefone)
        user_id = _obter_ou_criar_user(db_session, "Testador Fase2")

        r = client.post(
            f"/api/mensagens/{mensagem_id}/aprovar",
            json={"aprovador_id": user_id, "feedback": "Correto, mas poderia ser mais direto"},
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
        user_id = _obter_ou_criar_user(db_session, "Testador Fase2")

        r = client.post(f"/api/mensagens/{mensagem_id}/aprovar", json={"aprovador_id": user_id})
        assert r.status_code == 200
        assert r.json()["feedback_aprovacao"] is None
    finally:
        _limpar(db_session, telefone)
