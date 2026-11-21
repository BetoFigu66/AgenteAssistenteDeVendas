"""Perguntas do roteiro com texto por produto (`services/perguntas_produto.py`): a
pergunta do modelo de cada produto vem do painel, e sem texto cadastrado vale o do
código."""

import pytest
from database import Database
from models import Produto
from services import perguntas_produto
from services.respostas.catalogo import MensagemId, renderizar_mensagem


@pytest.fixture
def db_session():
    with Database().get_session() as session:
        yield session


@pytest.fixture(autouse=True)
def cache_limpo():
    perguntas_produto.invalidar()
    yield
    perguntas_produto.invalidar()


def test_texto_cadastrado_substitui_o_corpo_e_mantem_o_codigo():
    contexto = {"produto": "a catraca", "texto_cadastrado": "Quantas pessoas usam {produto}?"}
    texto, codigo = renderizar_mensagem(MensagemId.PEDIR_FAIXA_FUNCIONARIOS, contexto)
    assert (texto, codigo) == ("Quantas pessoas usam a catraca?", "PEDIR_FAIXA_FUNCIONARIOS")


def test_sem_texto_ou_sem_tipo_vale_o_do_codigo(db_session):
    assert perguntas_produto.texto_para(db_session, "modelo_produto", None) is None
    assert perguntas_produto.texto_para(db_session, "campo_que_nao_existe", "catraca") is None


def test_banco_fora_vale_o_do_codigo(db_session, monkeypatch):
    def falha():
        raise RuntimeError("banco fora")

    monkeypatch.setattr(perguntas_produto, "_ler_banco", falha)
    assert perguntas_produto.texto_para(db_session, "modelo_produto", "relogio_ponto") is None


def test_api_cadastra_altera_e_exclui(client, db_session):
    produto = Produto(descricao="Produto Teste Pergunta Por Produto", ativo=True)
    db_session.add(produto)
    db_session.commit()
    pid = None
    try:
        opcoes = client.get("/api/perguntas-produto").json()
        assert any(p["id"] == produto.id for p in opcoes["produtos"])
        assert any(c["chave"] == "modelo_produto" for c in opcoes["campos"])

        base = {"produto_id": produto.id, "campo": "modelo_produto"}
        # Uma pergunta por mensagem: dois "?" não passam.
        assert client.post("/api/perguntas-produto", json={**base, "texto": "A? Ou B?"}).status_code == 422
        assert client.post("/api/perguntas-produto", json={**base, "campo": "x", "texto": "A?"}).status_code == 422

        criada = client.post("/api/perguntas-produto", json={**base, "texto": "Pergunta teste por produto?"})
        assert criada.status_code == 201, criada.text
        pid = criada.json()["id"]
        assert criada.json()["produto"] == produto.descricao
        assert client.post("/api/perguntas-produto", json={**base, "texto": "Outra?"}).status_code == 409

        # Vale na hora, sem esperar a releitura do cache.
        tipo = "produto_teste_pergunta_por_produto"
        assert perguntas_produto.texto_para(db_session, "modelo_produto", tipo) == "Pergunta teste por produto?"

        desligada = client.patch(f"/api/perguntas-produto/{pid}", json={"ativo": False})
        assert desligada.status_code == 200 and desligada.json()["ativo"] is False
        assert perguntas_produto.texto_para(db_session, "modelo_produto", tipo) is None
    finally:
        if pid is not None:
            assert client.delete(f"/api/perguntas-produto/{pid}").status_code == 204
        db_session.delete(db_session.get(Produto, produto.id))
        db_session.commit()
