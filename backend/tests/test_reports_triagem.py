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
    telefone = "+5511999987201"
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


# ---------------------------------------------------------------------------
# REQ-012.6 — matriz de transição (achado A3 da auditoria 2026-08: divergia do
# requisito e não tinha cobertura nenhuma)
# ---------------------------------------------------------------------------

# Transcrito de artefatos/requisitos_formais/REQ-012-...md:132-137, NÃO do código:
# é o requisito que manda, e é contra ele que a matriz tem que ser conferida.
_MATRIZ_DO_REQUISITO = {
    "aberto": {"em_analise", "descartado"},
    "em_analise": {"aguardando_fix", "resolvido", "descartado"},
    "aguardando_fix": {"resolvido", "em_analise"},
    "resolvido": {"em_analise"},
    "descartado": {"em_analise"},
}


def test_matriz_de_transicao_espelha_o_requisito():
    """Pino contra edição acidental da matriz. Compara por valor de string para não
    depender do enum e deixar o diff legível quando falhar."""
    import main

    atual = {
        origem.value: {destino.value for destino in destinos}
        for origem, destinos in main._TRANSICOES_STATUS_REPORT.items()
    }
    assert atual == _MATRIZ_DO_REQUISITO


def _reportar(client, proc_id: int) -> int:
    r = client.post(
        f"/api/processamentos/{proc_id}/reports",
        json={"descricao": "Report para exercitar o workflow de status"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_aberto_nao_pula_direto_para_aguardando_fix(client, db_session):
    """Era permitido antes do achado A3 e pulava a etapa de análise."""
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _reportar(client, proc_id)
        r = client.patch(f"/api/reports/{report_id}", json={"status": "aguardando_fix"})
        assert r.status_code == 409, r.text
    finally:
        _limpar_processamento(db_session, proc_id)


def test_resolvido_reabre_para_em_analise_e_nao_para_aberto(client, db_session):
    """O caso que a auditoria citou: `resolvido` reaberto ia para `aberto`.

    `aberto` significa "ainda não triado" (REQ-012.6) — um report que já passou por
    análise e resolução não volta a ser não-triado."""
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _reportar(client, proc_id)
        assert client.patch(f"/api/reports/{report_id}", json={"status": "em_analise"}).status_code == 200
        assert client.patch(f"/api/reports/{report_id}", json={"status": "resolvido"}).status_code == 200

        assert client.patch(f"/api/reports/{report_id}", json={"status": "aberto"}).status_code == 409

        r = client.patch(f"/api/reports/{report_id}", json={"status": "em_analise"})
        assert r.status_code == 200
        assert r.json()["status"] == "em_analise"
    finally:
        _limpar_processamento(db_session, proc_id)


def test_descartado_reabre_apenas_para_em_analise(client, db_session):
    proc_id = _criar_processamento(db_session)
    try:
        report_id = _reportar(client, proc_id)
        assert client.patch(f"/api/reports/{report_id}", json={"status": "descartado"}).status_code == 200

        assert client.patch(f"/api/reports/{report_id}", json={"status": "aberto"}).status_code == 409

        r = client.patch(f"/api/reports/{report_id}", json={"status": "em_analise"})
        assert r.status_code == 200
    finally:
        _limpar_processamento(db_session, proc_id)
