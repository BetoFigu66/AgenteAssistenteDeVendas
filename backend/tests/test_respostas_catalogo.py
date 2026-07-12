"""Testes dos templates de pergunta de campo (MVP Continuidade, passo B5)."""

from services.respostas.catalogo import MensagemId, renderizar_mensagem


def test_pedir_modelo_renderiza():
    texto, codigo = renderizar_mensagem(MensagemId.PEDIR_MODELO)
    assert codigo == "PEDIR_MODELO"
    assert "cartográfico" in texto and "eletrônico" in texto


def test_pedir_software_ponto_renderiza():
    texto, codigo = renderizar_mensagem(MensagemId.PEDIR_SOFTWARE_PONTO)
    assert codigo == "PEDIR_SOFTWARE_PONTO"
    assert "software de ponto" in texto


def test_pedir_faixa_funcionarios_renderiza():
    texto, codigo = renderizar_mensagem(MensagemId.PEDIR_FAIXA_FUNCIONARIOS)
    assert codigo == "PEDIR_FAIXA_FUNCIONARIOS"
    assert "funcionários" in texto
