"""Despacho da ponte reports → goals (`scripts/ponte_reports_goals.py::despachar_um`).

Caso real de 22/11/2026: o goal saiu do `goal novo` como rascunho (o padrão), o `goal disparar`
recusou, e o report já tinha o goal_id gravado: ficou fora da fila e sem executor.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ponte_reports_goals as ponte

REPORT = SimpleNamespace(id=7, descricao="bot disse que não entendeu", severidade=SimpleNamespace(value="media"))


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    chamadas, vinculos = [], []
    estado = {"status": None, "disparar_falha": False}

    def goal_falso(*args, entrada=None):
        chamadas.append(args)
        if args[0] == "disparar" and estado["disparar_falha"]:
            raise RuntimeError("goal disparar falhou")
        return "ok"

    monkeypatch.setattr(ponte, "GOALS_PESSOAIS", tmp_path)
    monkeypatch.setattr(ponte, "goal", goal_falso)
    monkeypatch.setattr(ponte, "status_do_goal", lambda gid: estado["status"], raising=False)
    monkeypatch.setattr(ponte, "preparar_worktree", lambda repo, gid, branch: Path("/wt") / gid)
    monkeypatch.setattr(ponte.svc, "contexto_markdown", lambda session, rid: "contexto")
    monkeypatch.setattr(ponte.svc, "vincular_goal", lambda session, rid, gid: vinculos.append((rid, gid)))
    return SimpleNamespace(chamadas=chamadas, vinculos=vinculos, estado=estado, raiz=tmp_path)


def _comandos(chamadas):
    return [c[0] for c in chamadas]


def test_goal_novo_nasce_pronto_e_vincula_depois_do_disparo(ambiente):
    assert ponte.despachar_um(None, REPORT, Path("/repo"), "py") == "report-7"
    novo = next(c for c in ambiente.chamadas if c[0] == "novo")
    assert novo[novo.index("--status") + 1] == "pronto"
    assert _comandos(ambiente.chamadas)[-1] == "disparar"
    assert ambiente.vinculos == [(7, "report-7")]


def test_disparo_que_falha_nao_vincula(ambiente):
    ambiente.estado["disparar_falha"] = True
    with pytest.raises(RuntimeError):
        ponte.despachar_um(None, REPORT, Path("/repo"), "py")
    assert ambiente.vinculos == []  # o report continua na fila para a próxima rodada


def test_goal_reaproveitado_em_rascunho_volta_a_pronto(ambiente):
    (ambiente.raiz / "report-7").mkdir()
    ambiente.estado["status"] = "rascunho"
    ponte.despachar_um(None, REPORT, Path("/repo"), "py")
    assert "novo" not in _comandos(ambiente.chamadas)
    assert ("status", "report-7", "pronto") == ambiente.chamadas[0][:3]
    assert ambiente.vinculos == [(7, "report-7")]


def test_goal_reaproveitado_ja_pronto_nao_muda_status(ambiente):
    (ambiente.raiz / "report-7").mkdir()
    ambiente.estado["status"] = "pronto"
    ponte.despachar_um(None, REPORT, Path("/repo"), "py")
    assert "status" not in _comandos(ambiente.chamadas)


def test_goal_do_proprio_report_na_fila_nao_ocupa_vaga(monkeypatch):
    goals = [{"id": "report-7", "status": "pronto"}, {"id": "report-9", "status": "executando"}]
    monkeypatch.setattr(ponte, "goals_de_report", lambda: goals)
    fila = [SimpleNamespace(id=7)]
    assert [g["id"] for g in ponte.ocupando_vaga(fila)] == ["report-9"]
    assert [g["id"] for g in ponte.ocupando_vaga([])] == ["report-7", "report-9"]


def test_duvida_vira_goal_que_so_responde(ambiente):
    duvida = SimpleNamespace(
        id=8,
        descricao="Por que o bot pediu o CNPJ antes do nome?",
        severidade=SimpleNamespace(value="baixa"),
        categoria=SimpleNamespace(value="duvida"),
    )
    ponte.despachar_um(None, duvida, Path("/repo"), "py")
    novo = next(c for c in ambiente.chamadas if c[0] == "novo")
    objetivo = novo[novo.index("--objetivo") + 1]
    assert "responder 8 --goal report-8" in objetivo
    assert "deploy_auto" not in objetivo and "git push" not in objetivo
    # Sem push nem deploy na trava do executor.
    assert ("set", "report-8", f"permite={ponte.PERMITE_DUVIDA}") in ambiente.chamadas
    assert "push" not in ponte.PERMITE_DUVIDA and "deploy" not in ponte.PERMITE_DUVIDA
    assert ambiente.vinculos == [(8, "report-8")]
