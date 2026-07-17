"""Testes dos endpoints de modo de execução (REQ-011.1/011.3, Fase 2)."""

import pytest
from database import Database
from models import HistoricoModoExecucao, ModoExecucao
from services.parametro_service import MODO_EXECUCAO, ParametroService


@pytest.fixture(autouse=True)
def _reset_modo_execucao():
    database = Database()
    with database.get_session() as session:
        ParametroService(session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
    yield
    with database.get_session() as session:
        ParametroService(session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        session.query(HistoricoModoExecucao).delete()
        session.commit()


def test_get_config_execucao_default(client):
    r = client.get("/api/config/execucao")
    assert r.status_code == 200
    body = r.json()
    assert body["modo_execucao"] == "execucao_normal"
    assert body["sla_aprovacao_minutos"] == 10


def test_patch_config_execucao_troca_modo_e_audita(client):
    r = client.patch("/api/config/execucao", json={"modo_execucao": "conversa_controlada"})
    assert r.status_code == 200
    assert r.json() == {"modo_execucao": "conversa_controlada", "alterado": True}

    r2 = client.get("/api/config/execucao")
    body = r2.json()
    assert body["modo_execucao"] == "conversa_controlada"
    assert len(body["historico"]) == 1
    assert body["historico"][0]["modo_anterior"] == "execucao_normal"
    assert body["historico"][0]["modo_novo"] == "conversa_controlada"
    assert body["historico"][0]["ator"] == "Pytest Runner"


def test_patch_config_execucao_mesmo_modo_nao_gera_evento(client):
    r = client.patch("/api/config/execucao", json={"modo_execucao": "execucao_normal"})
    assert r.status_code == 200
    assert r.json()["alterado"] is False

    r2 = client.get("/api/config/execucao")
    assert r2.json()["historico"] == []


def test_patch_config_execucao_modo_invalido(client):
    r = client.patch("/api/config/execucao", json={"modo_execucao": "modo_qualquer"})
    assert r.status_code == 422
