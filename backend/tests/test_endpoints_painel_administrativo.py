"""Testes dos endpoints novos/ajustados da Fase 4 (REQ-010 — Painel Administrativo):
filtro+paginação de atendimentos e reports, dados de Pessoa (PJ/PF) no cabeçalho de
conversa, e o endpoint de campos pendentes. Zero cobertura antes desta fase.
"""

import pytest
from database import Database
from models import Contato, Pessoa
from services.atendimentos import obter_ou_criar_atendimento
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


def test_atendimentos_ativas_filtro_status_e_busca(client, db_session):
    telefone = "5511999986001"
    try:
        contato = Contato(telefone=telefone, nome="Cliente Filtro Teste")
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)
        obter_ou_criar_atendimento(db_session, contato)

        r = client.get("/api/atendimentos/ativas", params={"q": "Cliente Filtro Teste"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert any(a["telefone"] == telefone for a in body["atendimentos"])
        assert "page" in body and "limit" in body

        r_encerrado = client.get(
            "/api/atendimentos/ativas", params={"q": "Cliente Filtro Teste", "status": "encerrado"}
        )
        assert r_encerrado.status_code == 200
        assert all(a["telefone"] != telefone for a in r_encerrado.json()["atendimentos"])
    finally:
        _limpar(db_session, telefone)


def test_atendimentos_ativas_status_invalido_400(client):
    r = client.get("/api/atendimentos/ativas", params={"status": "bagunca"})
    assert r.status_code == 400


def test_atendimentos_ativas_limit_invalido_400(client):
    r = client.get("/api/atendimentos/ativas", params={"limit": 0})
    assert r.status_code == 400
    r2 = client.get("/api/atendimentos/ativas", params={"limit": 999})
    assert r2.status_code == 400


def test_reports_paginacao_shape(client):
    r = client.get("/api/reports", params={"page": 1, "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert set(["total", "page", "limit", "reports"]) <= set(body.keys())
    assert body["page"] == 1
    assert body["limit"] == 5
    assert len(body["reports"]) <= 5


def test_historico_limit_invalido_400(client):
    r = client.get("/api/historico/5511999986999", params={"limit": 0})
    assert r.status_code == 400
    r2 = client.get("/api/historico/5511999986999", params={"offset": -1})
    assert r2.status_code == 400


def test_conversa_retorna_pessoa_com_cpf_mascarado(client, db_session):
    telefone = "5511999986002"
    try:
        contato = Contato(telefone=telefone, nome="Cliente PF Teste")
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)

        pessoa = Pessoa(cpf="52998224725", nome="Fulano de Tal")
        db_session.add(pessoa)
        db_session.commit()
        db_session.refresh(pessoa)

        obter_ou_criar_atendimento(db_session, contato, pessoa=pessoa)

        r = client.get(f"/api/conversa/{telefone}")
        assert r.status_code == 200
        body = r.json()
        assert body["empresa"] is None
        assert body["pessoa"] is not None
        assert body["pessoa"]["nome"] == "Fulano de Tal"
        assert body["pessoa"]["cpf_mascarado"] == "***.982.247-**"
        assert "cpf" not in body["pessoa"]
    finally:
        _limpar(db_session, telefone)
        db_session.query(Pessoa).filter_by(cpf="52998224725").delete()
        db_session.commit()


def test_campos_pendentes_endpoint(client, db_session):
    from models import AtendimentoInfo

    telefone = "5511999986003"
    try:
        contato = Contato(telefone=telefone, nome="Cliente Campos Pendentes")
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)

        atendimento = obter_ou_criar_atendimento(db_session, contato)
        db_session.add(AtendimentoInfo(atendimento_id=atendimento.id, chave="tipos_produto", valor="relogio_ponto"))
        db_session.commit()

        r = client.get(f"/api/atendimentos/{atendimento.id}/campos-pendentes")
        assert r.status_code == 200
        body = r.json()
        assert "campos_pendentes" in body
        chaves = {c["chave"] for c in body["campos_pendentes"]}
        assert "modelo_produto" in chaves
    finally:
        _limpar(db_session, telefone)


def test_campos_pendentes_atendimento_inexistente_404(client):
    r = client.get("/api/atendimentos/999999999/campos-pendentes")
    assert r.status_code == 404
