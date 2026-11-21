"""Correção automática de reports por goals do Claude (`services/correcao_automatica.py`).

A ponte (`backend/scripts/ponte_reports_goals.py`) depende de três coisas do lado do
banco, verificadas aqui: a flag marcada na triagem pelo PATCH (com histórico), a fila
(quem entra e quem não), e o vínculo/resolução feitos pela automação respeitando o
workflow de status. Mais o mascaramento do contexto, que vai para uma sessão do Claude.
"""

from datetime import timedelta

import pytest
from database import Database
from models import HistoricoStatusReport, ProcessamentoMensagem
from services import correcao_automatica as svc


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def report_id(client, db_session):
    proc = ProcessamentoMensagem(intencao="saudacao")
    db_session.add(proc)
    db_session.commit()
    r = client.post(
        f"/api/processamentos/{proc.id}/reports",
        json={"descricao": "Perguntou o nome de novo, CPF 123.456.789-09 já informado"},
    )
    assert r.status_code == 201, r.text
    yield r.json()["id"]
    db_session.rollback()
    db_session.query(ProcessamentoMensagem).filter_by(id=proc.id).delete(synchronize_session=False)
    db_session.commit()


def _ids_na_fila(db_session):
    db_session.expire_all()
    return {r.id for r in svc.listar_fila(db_session, carencia=timedelta(0))}


def test_patch_marca_correcao_automatica_com_historico(client, report_id):
    r = client.patch(f"/api/reports/{report_id}", json={"correcao_automatica": True})
    assert r.status_code == 200, r.text
    assert r.json()["correcao_automatica"] is True
    assert r.json()["goal_id"] is None

    historico = client.get(f"/api/reports/{report_id}/contexto").json()["historico_status"]
    assert [(h["campo"], h["valor_anterior"], h["valor_novo"]) for h in historico] == [
        ("correcao_automatica", "false", "true")
    ]

    # Reenviar o mesmo valor (a tela manda o formulário inteiro) não polui o histórico.
    client.patch(f"/api/reports/{report_id}", json={"correcao_automatica": True})
    assert len(client.get(f"/api/reports/{report_id}/contexto").json()["historico_status"]) == 1


def test_fila_so_tem_marcados_sem_goal_e_fora_da_carencia(client, db_session, report_id):
    assert report_id not in _ids_na_fila(db_session)

    client.patch(f"/api/reports/{report_id}", json={"correcao_automatica": True})
    assert report_id in _ids_na_fila(db_session)
    # Recém-alterado: ainda dentro da carência padrão, a ponte não pega.
    db_session.expire_all()
    assert report_id not in {r.id for r in svc.listar_fila(db_session)}

    svc.vincular_goal(db_session, report_id, "report-teste")
    assert report_id not in _ids_na_fila(db_session)


def test_vincular_e_resolver_seguem_o_workflow(client, db_session, report_id):
    client.patch(f"/api/reports/{report_id}", json={"correcao_automatica": True})

    r = svc.vincular_goal(db_session, report_id, "report-teste")
    assert (r.goal_id, r.status.value) == ("report-teste", "em_analise")

    r = svc.resolver(db_session, report_id, "corrigido no commit abc")
    assert r.status.value == "resolvido"
    assert r.resolvido_por == svc.ATOR
    assert r.resolucao == "corrigido no commit abc"

    historico = client.get(f"/api/reports/{report_id}/contexto").json()["historico_status"]
    automacao = [(h["campo"], h["valor_novo"]) for h in reversed(historico) if h["ator"] == svc.ATOR]
    assert automacao == [("goal_id", "report-teste"), ("status", "em_analise"), ("status", "resolvido")]


def test_resolver_report_aberto_passa_por_em_analise(db_session, report_id):
    # `aberto` não vai direto para `resolvido` no workflow de triagem (REQ-012.6).
    r = svc.resolver(db_session, report_id, "ok")
    assert r.status.value == "resolvido"
    estados = [
        h.valor_novo
        for h in db_session.query(HistoricoStatusReport)
        .filter_by(report_id=report_id, campo="status")
        .order_by(HistoricoStatusReport.id)
    ]
    assert estados == ["em_analise", "resolvido"]


def test_contexto_mascara_dados_pessoais(db_session, report_id):
    texto = svc.contexto_markdown(db_session, report_id)
    assert "123.456.789-09" not in texto
    assert "<documento 11 dígitos>" in texto


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("cnpj 12.345.678/0001-90", "cnpj <documento 14 dígitos>"),
        ("12345678000190", "<documento 14 dígitos>"),
        ("cpf 12345678909", "cpf <documento 11 dígitos>"),
        ("fulano@empresa.com.br", "<email>"),
        ("nasci em 28/12/1965", "nasci em <data>"),
        ("quero 3 catracas para 150 funcionários", "quero 3 catracas para 150 funcionários"),
    ],
)
def test_mascarar(entrada, esperado):
    assert svc.mascarar(entrada) == esperado
