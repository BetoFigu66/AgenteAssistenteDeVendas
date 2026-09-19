"""Histórico de alterações de um report (REQ-012.8).

O REQ-012.8 exige que a edição de categoria/severidade durante a triagem fique
registrada, não só a transição de status. A tabela `historico_status_report`
passou a guardar `campo`/`valor_anterior`/`valor_novo`, uma linha por alteração,
e é isso que se verifica aqui: o que gera linha, o que não gera, e o que o
histórico de status de antes continua devolvendo.
"""

import pytest
from database import Database
from models import ProcessamentoMensagem


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _criar_processamento(db_session) -> int:
    proc = ProcessamentoMensagem(intencao="saudacao")
    db_session.add(proc)
    db_session.commit()
    db_session.refresh(proc)
    return proc.id


def _limpar_processamento(db_session, proc_id):
    # Cascata via FK (ondelete=CASCADE): apagar o processamento remove o report
    # vinculado, e apagar o report remove seu histórico.
    db_session.commit()
    db_session.query(ProcessamentoMensagem).filter_by(id=proc_id).delete(synchronize_session=False)
    db_session.commit()


def _novo_report(client, proc_id) -> int:
    r = client.post(
        f"/api/processamentos/{proc_id}/reports",
        json={"descricao": "Classificou a intenção errada nesta conversa"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _historico(client, report_id):
    r = client.get(f"/api/reports/{report_id}/contexto")
    assert r.status_code == 200, r.text
    # Vem do mais recente para o mais antigo; aqui interessa a ordem cronológica.
    return list(reversed(r.json()["historico_status"]))


def test_edicao_de_categoria_gera_historico(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _novo_report(client, proc_id)

        r = client.patch(f"/api/reports/{report_id}", json={"categoria": "fluxo"})
        assert r.status_code == 200
        assert r.json()["categoria"] == "fluxo"

        historico = _historico(client, report_id)
        assert len(historico) == 1
        linha = historico[0]
        assert linha["campo"] == "categoria"
        assert linha["valor_anterior"] == "outro"
        assert linha["valor_novo"] == "fluxo"
        assert linha["ator"] == "Pytest Runner"
        assert linha["timestamp"] is not None
        # Linha que não é de status não finge ter mexido em status.
        assert linha["status_anterior"] is None
        assert linha["status_novo"] is None
    finally:
        _limpar_processamento(db_session, proc_id)


def test_edicao_de_severidade_gera_historico(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _novo_report(client, proc_id)

        r = client.patch(f"/api/reports/{report_id}", json={"severidade": "critica"})
        assert r.status_code == 200
        assert r.json()["severidade"] == "critica"

        historico = _historico(client, report_id)
        assert len(historico) == 1
        assert historico[0]["campo"] == "severidade"
        assert historico[0]["valor_anterior"] == "media"
        assert historico[0]["valor_novo"] == "critica"
    finally:
        _limpar_processamento(db_session, proc_id)


def test_edicao_que_nao_muda_nada_nao_gera_historico(client, db_session):
    """A tela manda o formulário inteiro no PATCH: repetir o valor atual é o caso
    comum, e não é alteração nenhuma."""
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _novo_report(client, proc_id)

        r = client.patch(
            f"/api/reports/{report_id}",
            json={"categoria": "outro", "severidade": "media", "status": "aberto"},
        )
        assert r.status_code == 200

        assert _historico(client, report_id) == []
    finally:
        _limpar_processamento(db_session, proc_id)


def test_alteracoes_no_mesmo_patch_geram_uma_linha_cada(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _novo_report(client, proc_id)

        r = client.patch(
            f"/api/reports/{report_id}",
            json={"status": "em_analise", "categoria": "llm", "severidade": "alta"},
        )
        assert r.status_code == 200

        historico = _historico(client, report_id)
        assert {linha["campo"] for linha in historico} == {"status", "categoria", "severidade"}
        assert len(historico) == 3
    finally:
        _limpar_processamento(db_session, proc_id)


def test_historico_de_status_continua_como_antes(client, db_session):
    """Regressão: a transição de status segue gerando a mesma linha, com as chaves
    antigas preenchidas para quem já lia o histórico."""
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _novo_report(client, proc_id)

        r = client.patch(f"/api/reports/{report_id}", json={"status": "em_analise"})
        assert r.status_code == 200
        assert r.json()["status"] == "em_analise"

        historico = _historico(client, report_id)
        assert len(historico) == 1
        linha = historico[0]
        assert linha["campo"] == "status"
        assert linha["status_anterior"] == "aberto"
        assert linha["status_novo"] == "em_analise"
        assert (linha["valor_anterior"], linha["valor_novo"]) == ("aberto", "em_analise")
    finally:
        _limpar_processamento(db_session, proc_id)


def test_transicao_invalida_nao_grava_alteracao_nenhuma(client, db_session):
    """A alteração e o registro dela estão na mesma transação: se o PATCH é recusado,
    nem o campo nem o histórico ficam pela metade."""
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _novo_report(client, proc_id)

        # aberto -> resolvido é transição inválida; a categoria vai no mesmo PATCH.
        r = client.patch(
            f"/api/reports/{report_id}", json={"status": "resolvido", "categoria": "dados"}
        )
        assert r.status_code == 409

        r_report = client.get(f"/api/reports/{report_id}/contexto")
        assert r_report.json()["report"]["categoria"] == "outro"
        assert _historico(client, report_id) == []
    finally:
        _limpar_processamento(db_session, proc_id)
