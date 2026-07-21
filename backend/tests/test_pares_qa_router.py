"""Testes da Fase 9 (REQ-013 — Pares Q&A Curados): workflow de lazy embedding
(rascunho sem embedding -> aprovação gera embedding), soft delete, filtro por tag,
e a correção de ordenação de rotas de `/api/pares-qa/pendentes-aprovacao` (antes
retornava 422 por casar com `/{par_id}` primeiro).

O provider de embeddings real (API paga) é substituído por um dublê determinístico
via monkeypatch em `services.embeddings.get_embedding_provider`.
"""

from __future__ import annotations

import pytest
from database import Database
from models import ParQA
from services.embeddings.base import EmbeddingProvider, EmbeddingResponse

DIMENSOES = 1536


class _FakeEmbeddingProvider(EmbeddingProvider):
    """Embedding determinístico (não depende de API externa) para testes."""

    async def embed(self, textos):
        vetor = [0.001] * DIMENSOES
        return EmbeddingResponse(embeddings=[vetor for _ in textos], modelo="fake", dimensoes=DIMENSOES)

    @property
    def nome(self) -> str:
        return "fake"

    @property
    def modelo(self) -> str:
        return "fake-model"

    @property
    def dimensoes(self) -> int:
        return DIMENSOES


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def fake_embeddings(monkeypatch):
    provider = _FakeEmbeddingProvider()
    monkeypatch.setattr("services.embeddings.get_embedding_provider", lambda: provider)
    return provider


def _limpar_par(db_session, par_id):
    db_session.commit()
    db_session.query(ParQA).filter_by(id=par_id).delete(synchronize_session=False)
    db_session.commit()


def test_pendentes_aprovacao_nao_retorna_422(client):
    """Regressão: rota literal precisa vir antes de /{par_id} (bug real encontrado
    na Fase 9 — GET .../pendentes-aprovacao caia no matcher de /{par_id} e
    devolvia 422 'not a valid integer')."""
    r = client.get("/api/pares-qa/pendentes-aprovacao")
    assert r.status_code == 200
    assert "pares" in r.json()


def test_criar_rascunho_sem_embedding_e_aprovar_gera_embedding(client, db_session, fake_embeddings):
    r = client.post(
        "/api/pares-qa",
        json={
            "id_externo": "teste:lazy_embedding_1",
            "pergunta": "Pergunta de teste para lazy embedding?",
            "resposta": "Resposta de teste.",
        },
    )
    assert r.status_code == 201, r.text
    par = r.json()
    par_id = par["id"]
    try:
        assert par["aprovado"] is False
        assert par["ativo"] is True

        # embedding não é exposto no to_dict, mas o registro no banco deve estar None
        registro = db_session.query(ParQA).filter_by(id=par_id).first()
        assert registro.embedding is None

        r_aprovar = client.post(f"/api/pares-qa/{par_id}/aprovar")
        assert r_aprovar.status_code == 200, r_aprovar.text
        assert r_aprovar.json()["aprovado"] is True

        db_session.expire_all()
        registro = db_session.query(ParQA).filter_by(id=par_id).first()
        assert registro.embedding is not None

        # aprovar de novo é rejeitado (409)
        r_aprovar_2 = client.post(f"/api/pares-qa/{par_id}/aprovar")
        assert r_aprovar_2.status_code == 409
    finally:
        _limpar_par(db_session, par_id)


def test_criar_par_duplicado_id_externo_e_rejeitado(client, db_session):
    r1 = client.post(
        "/api/pares-qa",
        json={
            "id_externo": "teste:duplicata_1",
            "pergunta": "Pergunta única de teste?",
            "resposta": "Resposta.",
        },
    )
    assert r1.status_code == 201
    par_id = r1.json()["id"]
    try:
        r2 = client.post(
            "/api/pares-qa",
            json={
                "id_externo": "teste:duplicata_1",
                "pergunta": "Outra pergunta qualquer",
                "resposta": "Outra resposta",
            },
        )
        assert r2.status_code == 409
    finally:
        _limpar_par(db_session, par_id)


def test_soft_delete_e_idempotente(client, db_session):
    r = client.post(
        "/api/pares-qa",
        json={
            "id_externo": "teste:soft_delete_1",
            "pergunta": "Pergunta para soft delete?",
            "resposta": "Resposta.",
        },
    )
    par_id = r.json()["id"]
    try:
        r_del = client.delete(f"/api/pares-qa/{par_id}")
        assert r_del.status_code == 200
        assert r_del.json()["ativo"] is False

        db_session.expire_all()
        registro = db_session.query(ParQA).filter_by(id=par_id).first()
        assert registro.ativo is False

        # segunda desativação é rejeitada (409) — soft delete não é "any->any"
        r_del_2 = client.delete(f"/api/pares-qa/{par_id}")
        assert r_del_2.status_code == 409
    finally:
        _limpar_par(db_session, par_id)


def test_filtro_por_tag(client, db_session):
    r = client.post(
        "/api/pares-qa",
        json={
            "id_externo": "teste:tag_filtro_1",
            "pergunta": "Pergunta com tag exclusiva de teste?",
            "resposta": "Resposta.",
            "tags": ["tag-exclusiva-teste-xyz"],
        },
    )
    par_id = r.json()["id"]
    try:
        r_com_tag = client.get("/api/pares-qa", params={"tag": "tag-exclusiva-teste-xyz", "ativo": "true"})
        assert r_com_tag.status_code == 200
        assert any(p["id"] == par_id for p in r_com_tag.json()["pares"])

        r_sem_tag = client.get("/api/pares-qa", params={"tag": "tag-que-nao-existe-em-nada"})
        assert r_sem_tag.status_code == 200
        assert all(p["id"] != par_id for p in r_sem_tag.json()["pares"])
    finally:
        _limpar_par(db_session, par_id)


def test_config_rag_expoe_qa_score_minimo(client):
    r = client.get("/api/config/rag")
    assert r.status_code == 200
    body = r.json()
    assert "qa_score_minimo" in body
    assert isinstance(body["qa_score_minimo"], float)
