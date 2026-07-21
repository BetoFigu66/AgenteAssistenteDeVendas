"""Testes da Fase 8 (REQ-012 — Reports de Problema): severidade default da
reprovação automática, validação de transição de status (+ histórico), validação
de tamanho mínimo da descrição, e filtros de autor/período/busca textual.
"""

import pytest
from database import Database
from models import Mensagem, OrigemMensagem, ProcessamentoMensagem
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


def _criar_processamento(db_session) -> int:
    proc = ProcessamentoMensagem(intencao="saudacao")
    db_session.add(proc)
    db_session.commit()
    db_session.refresh(proc)
    return proc.id


def _limpar_processamento(db_session, proc_id):
    # Cascata via FK (ondelete=CASCADE): apagar o processamento já remove o
    # report vinculado, e apagar o report remove seu histórico de status.
    db_session.commit()
    db_session.query(ProcessamentoMensagem).filter_by(id=proc_id).delete(synchronize_session=False)
    db_session.commit()


def test_reprovacao_automatica_cria_report_severidade_media(client, db_session):
    telefone = "5511999987201"
    try:
        mensagem_id = _criar_mensagem_pendente(db_session, telefone)

        r = client.post(
            f"/api/mensagens/{mensagem_id}/reprovar",
            json={"justificativa": "Resposta não fazia sentido"},
        )
        assert r.status_code == 201, r.text
        report_id = r.json()["report_id"]

        r_ctx = client.get(f"/api/reports/{report_id}/contexto")
        assert r_ctx.status_code == 200
        assert r_ctx.json()["report"]["severidade"] == "media"
    finally:
        _limpar(db_session, telefone)


def test_transicao_status_invalida_e_bloqueada(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        r = client.post(
            f"/api/processamentos/{proc_id}/reports",
            json={"descricao": "Intenção classificada errada neste caso"},
        )
        assert r.status_code == 201, r.text
        report_id = r.json()["id"]
        assert r.json()["status"] == "aberto"

        # aberto -> resolvido direto não é permitido (precisa passar por análise/fix)
        r_invalida = client.patch(f"/api/reports/{report_id}", json={"status": "resolvido"})
        assert r_invalida.status_code == 409

        # aberto -> em_analise é permitido, e gera histórico
        r_valida = client.patch(f"/api/reports/{report_id}", json={"status": "em_analise"})
        assert r_valida.status_code == 200
        assert r_valida.json()["status"] == "em_analise"

        r_ctx = client.get(f"/api/reports/{report_id}/contexto")
        historico = r_ctx.json()["historico_status"]
        assert len(historico) == 1
        assert historico[0]["status_anterior"] == "aberto"
        assert historico[0]["status_novo"] == "em_analise"
    finally:
        _limpar_processamento(db_session, proc_id)


def test_descricao_curta_e_rejeitada(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        r = client.post(
            f"/api/processamentos/{proc_id}/reports",
            json={"descricao": "curta"},
        )
        assert r.status_code == 400
    finally:
        _limpar_processamento(db_session, proc_id)


def test_filtros_autor_e_busca_textual(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        r = client.post(
            f"/api/processamentos/{proc_id}/reports",
            json={"descricao": "Termo exclusivo xyzabc para busca textual"},
        )
        assert r.status_code == 201, r.text
        report_id = r.json()["id"]

        r_busca = client.get("/api/reports", params={"q_busca": "xyzabc"})
        assert r_busca.status_code == 200
        assert any(rep["id"] == report_id for rep in r_busca.json()["reports"])

        r_autor = client.get("/api/reports", params={"autor": "Runner"})
        assert r_autor.status_code == 200
        assert any(rep["id"] == report_id for rep in r_autor.json()["reports"])

        r_sem_match = client.get(
            "/api/reports", params={"q_busca": "termo-que-nao-existe-em-nenhum-report"}
        )
        assert r_sem_match.status_code == 200
        assert all(rep["id"] != report_id for rep in r_sem_match.json()["reports"])
    finally:
        _limpar_processamento(db_session, proc_id)
