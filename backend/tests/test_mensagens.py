"""Testes do catálogo estruturado de mensagens."""

from services.respostas.catalogo import CATALOGO, MensagemId, renderizar_mensagem
from services.respostas.transformers import montar_saudacao_novo


def test_catalogo_contem_todos_os_ids():
    for mensagem_id in MensagemId:
        assert int(mensagem_id) in CATALOGO
        tpl = CATALOGO[int(mensagem_id)]
        assert tpl.id == int(mensagem_id)
        assert tpl.codigo == mensagem_id.name


def test_saudacao_novo_sem_nome_pede_identificacao():
    texto, codigo = renderizar_mensagem(MensagemId.SAUDACAO_NOVO_CONTATO, {"modo": "identificacao"})
    assert codigo == "SAUDACAO_NOVO_CONTATO"
    assert texto.startswith("Olá!")
    assert "o seu nome" in texto
    assert "CNPJ" in texto
    assert "data de nascimento" not in texto.lower()


def test_saudacao_novo_com_nome_nao_repete_nome():
    texto, _ = renderizar_mensagem(
        MensagemId.SAUDACAO_NOVO_CONTATO,
        {"nome": "Kika", "modo": "identificacao"},
    )
    assert "Olá, Kika!" in texto
    assert "o seu nome" not in texto
    assert "CNPJ" in texto


def test_saudacao_novo_modo_orcamento_sem_pedido_documento():
    texto, _ = renderizar_mensagem(
        MensagemId.SAUDACAO_NOVO_CONTATO,
        {"nome": "Kika", "modo": "orcamento"},
    )
    assert "Olá, Kika!" in texto
    assert "CNPJ" not in texto
    assert "poderia me informar" not in texto


def test_perguntar_cnpj_sem_data_nascimento():
    texto, codigo = renderizar_mensagem(MensagemId.PERGUNTAR_CNPJ, {"nome": "Kika"})
    assert codigo == "PERGUNTAR_CNPJ"
    assert "o seu nome" not in texto
    assert "data de nascimento" not in texto.lower()
    assert "CNPJ" in texto


def test_montar_saudacao_novo_preserva_contexto():
    ctx = montar_saudacao_novo({"nome": "Ana", "modo": "identificacao"})
    assert ctx["saudacao"] == "Olá, Ana!"
    assert "linha_pedido" in ctx
