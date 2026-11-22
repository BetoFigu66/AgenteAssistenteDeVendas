"""Categorias Dúvida/Sugestão e respostas a reports (`RespostaReport`).

A Dúvida é respondida pelo Claude (ponte dos goals, `ponte_reports_goals responder`) ou pela
equipe (`POST /api/reports/{id}/respostas`); a tela mostra quem respondeu pela `origem`.
"""

from types import SimpleNamespace

import pytest
from database import Database
from models import OrigemRespostaReport, ProcessamentoMensagem
from services import correcao_automatica as svc


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def proc_id(db_session):
    proc = ProcessamentoMensagem(intencao="saudacao")
    db_session.add(proc)
    db_session.commit()
    yield proc.id
    db_session.rollback()
    db_session.query(ProcessamentoMensagem).filter_by(id=proc.id).delete(synchronize_session=False)
    db_session.commit()


def _criar(client, proc_id, categoria):
    r = client.post(
        f"/api/processamentos/{proc_id}/reports",
        json={"descricao": "Por que o bot perguntou o nome duas vezes?", "categoria": categoria},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize("categoria", ["duvida", "sugestao"])
def test_categorias_novas_sao_aceitas(client, proc_id, categoria):
    assert _criar(client, proc_id, categoria)["categoria"] == categoria


def test_resposta_da_equipe_resolve_a_duvida_e_diz_quem_respondeu(client, proc_id):
    rep = _criar(client, proc_id, "duvida")
    assert rep["respostas"] == []

    r = client.post(f"/api/reports/{rep['id']}/respostas", json={"texto": "  Porque o perfil não tinha nome.  "})
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["status"] == "resolvido"
    [resp] = corpo["respostas"]
    assert resp["texto"] == "Porque o perfil não tinha nome."
    assert resp["origem"] == "equipe"
    assert resp["autor"]  # usuário logado do client de teste
    assert corpo["resolvido_por"] == resp["autor"]

    historico = client.get(f"/api/reports/{rep['id']}/contexto").json()["historico_status"]
    assert [(h["valor_novo"], h["ator"]) for h in reversed(historico)] == [
        ("em_analise", resp["autor"]),
        ("resolvido", resp["autor"]),
    ]

    # Também na listagem do processamento (modal "Raciocínio do cérebro").
    lista = client.get(f"/api/processamentos/{proc_id}/reports").json()["reports"]
    assert lista[0]["respostas"][0]["origem"] == "equipe"


def test_resposta_do_claude_e_complemento_da_equipe(client, db_session, proc_id):
    rep = _criar(client, proc_id, "duvida")
    svc.adicionar_resposta(db_session, rep["id"], "Resposta do Claude", OrigemRespostaReport.CLAUDE,
                           "Claude (goal report-1)")
    corpo = client.post(f"/api/reports/{rep['id']}/respostas", json={"texto": "Complemento"}).json()
    assert [(r["origem"], r["texto"]) for r in corpo["respostas"]] == [
        ("claude", "Resposta do Claude"),
        ("equipe", "Complemento"),
    ]
    assert corpo["respostas"][0]["autor"] == "Claude (goal report-1)"
    assert corpo["status"] == "resolvido"


def test_resposta_em_report_que_nao_e_duvida_nao_muda_status(client, proc_id):
    rep = _criar(client, proc_id, "sugestao")
    corpo = client.post(f"/api/reports/{rep['id']}/respostas", json={"texto": "Boa ideia, vamos avaliar"}).json()
    assert corpo["status"] == "aberto"
    assert len(corpo["respostas"]) == 1


def test_resposta_vazia_ou_report_inexistente(client, proc_id):
    rep = _criar(client, proc_id, "duvida")
    assert client.post(f"/api/reports/{rep['id']}/respostas", json={"texto": "   "}).status_code == 400
    assert client.post("/api/reports/999999999/respostas", json={"texto": "oi"}).status_code == 404


def test_ponte_responder_grava_como_claude(client, proc_id, tmp_path):
    from scripts import ponte_reports_goals as ponte

    rep = _criar(client, proc_id, "duvida")
    arquivo = tmp_path / "resposta.md"
    arquivo.write_text("O nome é pedido de novo quando o perfil do WhatsApp vem vazio.", encoding="utf-8")
    ponte.cmd_responder(SimpleNamespace(report_id=rep["id"], goal="report-x", arquivo=str(arquivo), texto=None))

    corpo = client.get(f"/api/reports/{rep['id']}/contexto").json()["report"]
    [resp] = corpo["respostas"]
    assert (resp["origem"], resp["autor"]) == ("claude", "Claude (goal report-x)")
    assert corpo["status"] == "resolvido"
