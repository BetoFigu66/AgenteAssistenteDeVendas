"""Report #1736: "quero saber quais produtos vocês vendem para controle de acesso" recebia
"Sim, vendemos. Trabalhamos com as marcas Control-ID e Topdata de controle de acesso."

"quais produtos vocês vendem" não é "vocês vendem X?": o cliente pede a lista do que há na
linha (catraca biométrica, catraca facial, cancela...), e as marcas ainda não interessam. O
"vendem" fazia a regra de PERGUNTAR_DISPONIBILIDADE bater e a resposta confirmava a venda.

Ponta a ponta via `processar()`, no mesmo padrão de `test_report_1583_pode_explicar.py`.
"""

import asyncio

import pytest
from database import Database
from models import AtributoAdicionalModelo, Modelo, ModoExecucao, ProcessamentoMensagem, Produto
from services.classificador import Intencao, classificar_por_regras
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem

# CPF sintético válido (passa no dígito verificador), sem relação com pessoa real.
_CPF_SINTETICO = "52998224725"
_PERGUNTA = "quero saber quais produtos vocês vendem para controle de acesso"
_MARCA_TESTE = "MarcaTeste1736"


@pytest.mark.parametrize(
    "texto",
    [
        _PERGUNTA,
        "quais produtos de controle de acesso vocês vendem?",
        "que equipamentos vocês vendem para controle de acesso?",
    ],
)
def test_quais_produtos_vendem_nao_e_pergunta_de_disponibilidade(texto):
    intencoes = [i for i, _ in classificar_por_regras(texto)]
    assert Intencao.PERGUNTAR_DISPONIBILIDADE not in intencoes
    assert Intencao.PERGUNTAR_PRODUTO in intencoes


def test_vendem_um_produto_continua_disponibilidade():
    intencoes = [i for i, _ in classificar_por_regras("vocês vendem catraca?")]
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in intencoes


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    database = Database()
    with database.get_session() as session:
        yield session
        session.rollback()


@pytest.fixture
def catalogo_teste(db_session):
    produto = Produto(descricao="Catraca (teste 1736)", ativo=True)
    db_session.add(produto)
    db_session.flush()
    for codigo, tecnologia in (("TESTE-1736-A", "facial"), ("TESTE-1736-B", "biometria")):
        modelo = Modelo(
            produto_id=produto.id, codigo=codigo, descricao=f"Catraca {codigo}", marca=_MARCA_TESTE,
            preco_tabela=0, ativo=True,
        )
        modelo.atributos.append(AtributoAdicionalModelo(chave="tecnologia_leitura", valor=tecnologia))
        db_session.add(modelo)
    db_session.commit()
    yield produto
    db_session.rollback()
    db_session.query(Modelo).filter(Modelo.produto_id == produto.id).delete(synchronize_session=False)
    db_session.query(Produto).filter(Produto.id == produto.id).delete(synchronize_session=False)
    db_session.commit()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def test_quais_produtos_de_controle_de_acesso_lista_os_produtos(db_session, catalogo_teste):
    telefone = "+5500900001736"
    processador = ProcessadorMensagem()
    _limpar(db_session, telefone)
    try:
        for texto in ("olá", f"Maria Cristina CPF {_CPF_SINTETICO}"):
            asyncio.run(processador.processar(db_session, telefone, texto))
        resultado = asyncio.run(processador.processar(db_session, telefone, _PERGUNTA))

        proc = db_session.get(ProcessamentoMensagem, resultado.processamento_id)
        resposta = resultado.resposta
        print("\nRESPOSTA:", resposta, "\nTEMPLATE:", proc.template_usado)
        assert "Sim, vendemos" not in resposta
        assert "DISPONIBILIDADE_PRODUTO" not in (proc.template_usado or "")
        # A lista é dos produtos da linha, pela tecnologia, sem as marcas.
        assert "Catraca facial" in resposta
        assert "Catraca biométrica" in resposta
        assert _MARCA_TESTE not in resposta
    finally:
        _limpar(db_session, telefone)
