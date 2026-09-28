"""
Testes do modulo de ajuda contextual do painel (FAQ por tela).

Cobre o que pode dar errado de forma silenciosa:
  - hierarquia de contexto (especifico ganha do global);
  - conteudo global sendo encontrado de qualquer tela;
  - pergunta sem resposta virando lacuna registrada;
  - contexto inexistente sendo recusado (typo nao vira conteudo global);
  - **isolamento**: nada em `ajuda_conteudos` aparece na base que responde cliente
    (`pares_qa`) e vice-versa;
  - degradacao graciosa quando o provider de embeddings esta indisponivel.

O provider real (API paga) e substituido por um duble deterministico, mesmo padrao
de `test_pares_qa_router.py`.
"""

from __future__ import annotations

import pytest
from database import Database
from models import AjudaConsulta, AjudaConteudo, AjudaContexto, ParQA
from services.embeddings.base import EmbeddingProvider, EmbeddingResponse

DIMENSOES = 1536


class _FakeEmbeddingProvider(EmbeddingProvider):
    """Embedding deterministico: vetores iguais => similaridade maxima."""

    async def embed(self, textos):
        vetor = [0.0] * DIMENSOES
        vetor[0] = 1.0
        return EmbeddingResponse(
            embeddings=[list(vetor) for _ in textos], modelo="fake", dimensoes=DIMENSOES
        )

    @property
    def nome(self) -> str:
        return "fake"

    @property
    def modelo(self) -> str:
        return "fake-model"

    @property
    def dimensoes(self) -> int:
        return DIMENSOES


class _ProviderQuebrado(EmbeddingProvider):
    """Simula API de embeddings fora do ar."""

    async def embed(self, textos):
        raise RuntimeError("provider indisponivel (simulado)")

    @property
    def nome(self) -> str:
        return "quebrado"

    @property
    def modelo(self) -> str:
        return "quebrado"

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


@pytest.fixture
def limpar_ajuda(db_session):
    """Remove o que o teste criou, mesmo se ele falhar no meio."""
    yield
    db_session.rollback()
    db_session.query(AjudaConsulta).delete(synchronize_session=False)
    db_session.query(AjudaConteudo).filter(
        AjudaConteudo.pergunta.like("[teste]%")
    ).delete(synchronize_session=False)
    db_session.commit()


def _criar(client, pergunta, resposta, contexto=None, prioridade=0):
    r = client.post(
        "/api/ajuda/conteudos",
        json={
            "pergunta": pergunta,
            "resposta": resposta,
            "contexto_chave": contexto,
            "prioridade": prioridade,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Hierarquia de contexto
# ---------------------------------------------------------------------------


def test_contextos_candidatos_expande_do_especifico_ao_generico():
    from services.ajuda import contextos_candidatos

    assert contextos_candidatos("reports.detalhe") == ["reports.detalhe", "reports"]
    assert contextos_candidatos("chat") == ["chat"]
    assert contextos_candidatos(None) == []
    assert contextos_candidatos("") == []


def test_seed_criou_os_contextos_das_telas(client):
    r = client.get("/api/ajuda/contextos")
    assert r.status_code == 200
    chaves = {c["chave"] for c in r.json()["contextos"]}
    assert {"chat", "acompanhamento", "reports", "qa-base", "parametros"} <= chaves


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------


def test_encontra_conteudo_do_contexto_da_tela(client, fake_embeddings, limpar_ajuda):
    _criar(
        client,
        "[teste] Como aprovo uma mensagem pendente?",
        "Clique em Aprovar no cartao da mensagem.",
        contexto="acompanhamento",
    )
    r = client.post(
        "/api/ajuda/perguntar",
        json={"pergunta": "aprovar mensagem pendente", "contexto": "acompanhamento"},
    )
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["encontrou"] is True
    assert "Aprovar" in corpo["resultados"][0]["resposta"]


def test_conteudo_global_e_encontrado_de_qualquer_tela(client, fake_embeddings, limpar_ajuda):
    _criar(client, "[teste] Como troco minha senha?", "Fale com o administrador.")
    r = client.post(
        "/api/ajuda/perguntar", json={"pergunta": "trocar senha", "contexto": "parametros"}
    )
    assert r.json()["encontrou"] is True
    assert r.json()["resultados"][0]["contexto_chave"] is None


def test_conteudo_especifico_vence_o_global(client, fake_embeddings, limpar_ajuda):
    """Ajuda contextual precisa priorizar a tela, senao o 'contextual' nao significa nada."""
    _criar(client, "[teste] Como exporto os dados?", "Resposta generica.", prioridade=99)
    _criar(
        client,
        "[teste] Como exporto os dados do report?",
        "Resposta do report.",
        contexto="reports",
        prioridade=0,
    )
    r = client.post(
        "/api/ajuda/perguntar", json={"pergunta": "exportar dados", "contexto": "reports"}
    )
    resultados = r.json()["resultados"]
    assert resultados[0]["contexto_chave"] == "reports", (
        "o conteudo do contexto pedido deveria vir primeiro, mesmo com prioridade menor"
    )


def test_pergunta_sem_resposta_registra_lacuna(client, fake_embeddings, limpar_ajuda, db_session):
    pergunta = "[teste] como faco para viajar no tempo"
    r = client.post(
        "/api/ajuda/perguntar", json={"pergunta": pergunta, "contexto": "parametros"}
    )
    assert r.status_code == 200
    assert r.json()["encontrou"] is False

    db_session.commit()
    lacuna = (
        db_session.query(AjudaConsulta)
        .filter(AjudaConsulta.pergunta == pergunta)
        .first()
    )
    assert lacuna is not None
    assert lacuna.encontrou is False
    assert lacuna.contexto == "parametros"

    listagem = client.get("/api/ajuda/consultas?encontrou=false").json()
    assert any(c["pergunta"] == pergunta for c in listagem["consultas"])


def test_pergunta_vazia_retorna_400(client):
    r = client.post("/api/ajuda/perguntar", json={"pergunta": "   "})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Isolamento entre a base de ajuda e a base que responde ao cliente
# ---------------------------------------------------------------------------


def test_ajuda_nao_vaza_para_a_base_do_cliente(client, fake_embeddings, limpar_ajuda, db_session):
    """
    O conteudo de ajuda do painel nunca pode ser enviado a um cliente no WhatsApp.
    Por isso a base e separada: aqui garantimos que criar ajuda nao cria par Q&A.
    """
    antes = db_session.query(ParQA).count()
    _criar(
        client,
        "[teste] Como reprovo uma mensagem?",
        "Clique em Reprovar e justifique.",
        contexto="acompanhamento",
    )
    db_session.commit()
    assert db_session.query(ParQA).count() == antes, (
        "criar conteudo de ajuda nao deve inserir nada em pares_qa"
    )


def test_par_qa_do_cliente_nao_aparece_na_ajuda(client, fake_embeddings, limpar_ajuda, db_session):
    """O inverso: conteudo de venda nao deve ser oferecido como ajuda do painel."""
    par = ParQA(
        id_externo="teste:isolamento_ajuda",
        pergunta="Qual o preco da catraca Revolution?",
        resposta="Depende do modelo.",
        ativo=True,
        aprovado=True,
    )
    db_session.add(par)
    db_session.commit()
    try:
        r = client.post(
            "/api/ajuda/perguntar",
            json={"pergunta": "preco da catraca Revolution", "contexto": "chat"},
        )
        assert r.json()["encontrou"] is False, (
            "a ajuda do painel nao deve responder com conteudo de venda"
        )
    finally:
        db_session.query(ParQA).filter_by(id_externo="teste:isolamento_ajuda").delete()
        db_session.commit()


# ---------------------------------------------------------------------------
# CRUD e validacoes
# ---------------------------------------------------------------------------


def test_contexto_inexistente_e_recusado(client):
    """Typo no contexto tem que falhar alto: senao o conteudo viraria global e
    nunca apareceria na tela pretendida."""
    r = client.post(
        "/api/ajuda/conteudos",
        json={
            "pergunta": "[teste] pergunta qualquer",
            "resposta": "resposta",
            "contexto_chave": "parametro",  # falta o 's'
        },
    )
    assert r.status_code == 400
    assert "nao existe" in r.json()["detail"].lower()


def test_atualizar_e_desativar_conteudo(client, fake_embeddings, limpar_ajuda):
    criado = _criar(client, "[teste] Pergunta original?", "Resposta original.", contexto="chat")

    r = client.patch(
        f"/api/ajuda/conteudos/{criado['id']}",
        json={"resposta": "Resposta corrigida.", "prioridade": 7},
    )
    assert r.status_code == 200, r.text
    assert r.json()["resposta"] == "Resposta corrigida."
    assert r.json()["prioridade"] == 7

    r = client.delete(f"/api/ajuda/conteudos/{criado['id']}")
    assert r.status_code == 200
    assert r.json()["ativo"] is False

    # Soft delete: sai da busca, mas o registro permanece.
    r = client.post(
        "/api/ajuda/perguntar", json={"pergunta": "Pergunta original", "contexto": "chat"}
    )
    assert r.json()["encontrou"] is False

    # Segunda desativacao e conflito, nao erro silencioso.
    assert client.delete(f"/api/ajuda/conteudos/{criado['id']}").status_code == 409


def test_desativado_nao_aparece_nas_sugestoes(client, fake_embeddings, limpar_ajuda):
    criado = _criar(client, "[teste] Some das sugestoes?", "Resposta.", contexto="qa-base")
    antes = client.get("/api/ajuda/sugestoes?contexto=qa-base").json()["sugestoes"]
    assert any(s["conteudo_id"] == criado["id"] for s in antes)

    client.delete(f"/api/ajuda/conteudos/{criado['id']}")
    depois = client.get("/api/ajuda/sugestoes?contexto=qa-base").json()["sugestoes"]
    assert all(s["conteudo_id"] != criado["id"] for s in depois)


def test_conteudo_id_invalido_na_rota_nao_quebra_reindexar(client):
    """Regressao: /conteudos/reindexar precisa ser declarada antes de
    /conteudos/{id}, senao casa com o matcher de int e devolve 422."""
    r = client.post("/api/ajuda/conteudos/reindexar")
    assert r.status_code == 200
    assert set(r.json()) == {"pendentes", "indexados", "falhas"}


# ---------------------------------------------------------------------------
# Degradacao graciosa
# ---------------------------------------------------------------------------


def test_embeddings_fora_do_ar_nao_impede_cadastro_nem_busca(client, monkeypatch, limpar_ajuda):
    """
    Sem embeddings, o conteudo continua sendo criado e encontravel por full-text.
    Bloquear a edicao porque a API de embeddings caiu seria pior que salvar com
    busca semantica degradada.
    """
    monkeypatch.setattr(
        "services.embeddings.get_embedding_provider", lambda: _ProviderQuebrado()
    )

    criado = _criar(
        client,
        "[teste] Como reinicio o servidor de homologacao?",
        "Rode docker compose restart.",
        contexto="parametros",
    )
    assert criado["tem_embedding"] is False

    # Termos que compartilham radical com a pergunta cadastrada — ver o teste
    # seguinte para o caso que o full-text sozinho NAO resolve.
    r = client.post(
        "/api/ajuda/perguntar",
        json={"pergunta": "servidor homologacao", "contexto": "parametros"},
    )
    assert r.json()["encontrou"] is True, "full-text deve continuar funcionando sem embeddings"


def test_full_text_sozinho_nao_cobre_variacao_de_radical(client, monkeypatch, limpar_ajuda):
    """
    Documenta *por que* a camada de embeddings existe, com um caso real.

    O stemmer portugues reduz "reinicio" a `reinici` e "reiniciar" a `reinic` —
    radicais diferentes. Como `plainto_tsquery` combina os termos com AND, basta um
    nao casar para a busca falhar, mesmo sendo a mesma palavra para uma pessoa.

    Se algum dia este teste passar a encontrar, otimo: significa que o dicionario
    melhorou ou a busca deixou de depender so de radical. O `xfail` avisa
    (`XPASS`) em vez de quebrar a suite.
    """
    monkeypatch.setattr(
        "services.embeddings.get_embedding_provider", lambda: _ProviderQuebrado()
    )
    _criar(
        client,
        "[teste] Como reinicio o servidor de homologacao?",
        "Rode docker compose restart.",
        contexto="parametros",
    )
    r = client.post(
        "/api/ajuda/perguntar",
        json={"pergunta": "reiniciar servidor homologacao", "contexto": "parametros"},
    )
    if r.json()["encontrou"]:
        pytest.xfail("full-text passou a casar 'reiniciar' com 'reinicio' — limitacao superada")
    assert r.json()["encontrou"] is False
