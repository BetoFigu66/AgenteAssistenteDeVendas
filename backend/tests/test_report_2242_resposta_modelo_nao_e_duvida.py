"""Report #2242: a resposta à pergunta de tecnologia ("reconhecimento facial") era tratada
como dúvida de produto.

O classificador marca qualquer menção a "facial", "biométrico", "cartão" etc. como
`perguntar_produto`. Em Finalizando, a mensagem resolvia o modelo certo (relógio facial)
e, mesmo assim, caía em `_retomar_apos_duvida`: o RAG respondia sobre catracas faciais e
a pergunta seguinte vinha como "Voltando ao orçamento". A cliente tinha pedido relógio de
ponto e só respondeu a pergunta feita.

Mesma estratégia de `test_processador_finalizando_coleta_ativa.py`: injeta o
`ResultadoClassificacao` e chama `_decidir_resposta` direto.
"""

import asyncio

import pytest
from database import Database
from models import AtributoAdicionalModelo, ItemAtendimento, Modelo, Produto
from services.classificador import Intencao
from services.identificador import ResultadoIdentificacao, StatusIdentificacao
from services.processador import ProcessadorMensagem

from tests.test_processador_finalizando_coleta_ativa import _iniciar_finalizando_com_software, _limpar, _resultado

_TECNOLOGIA = "facial_teste_2242"


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _catalogo_com_modelo_facial(db_session):
    """Produto + modelo de teste com `tecnologia_leitura` própria, para a resolução do
    modelo não depender do catálogo real."""
    produto = db_session.query(Produto).filter_by(descricao="Relógio de Ponto (teste 2242)").first()
    if produto is None:
        produto = Produto(descricao="Relógio de Ponto (teste 2242)", ativo=True)
        db_session.add(produto)
        db_session.commit()
    modelo = db_session.query(Modelo).filter_by(codigo="TESTE-REP-2242").first()
    if modelo is None:
        modelo = Modelo(
            produto_id=produto.id,
            codigo="TESTE-REP-2242",
            descricao="Relógio facial de teste (report 2242)",
            preco_tabela=0,
            ativo=True,
        )
        db_session.add(modelo)
        db_session.commit()
        db_session.add(
            AtributoAdicionalModelo(modelo_id=modelo.id, chave="tecnologia_leitura", valor=_TECNOLOGIA, ativo=True)
        )
        db_session.commit()
    return produto, modelo


def test_resposta_a_pergunta_de_tecnologia_nao_vira_duvida_de_produto(db_session, processador):
    telefone = "+5511999982242"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        produto, modelo = _catalogo_com_modelo_facial(db_session)
        # Item do relógio já criado, modelo ainda pendente (a pergunta de tecnologia foi feita).
        db_session.add(ItemAtendimento(atendimento_id=atendimento.id, produto_id=produto.id, quantidade=1))
        db_session.commit()

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.PERGUNTAR_PRODUTO, tipo_leitor_mencionado=_TECNOLOGIA)
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="reconhecimento facial",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )

        db_session.refresh(atendimento)
        assert atendimento.itens[0].modelo_id == modelo.id
        # Era resposta, não dúvida: segue para a próxima pergunta, sem RAG nem "Voltando ao orçamento".
        assert "RETOMAR_PERGUNTA_PENDENTE" not in resposta.template_usado
        assert not resposta.rag_utilizada
        assert "software" in resposta.texto.lower()
    finally:
        _limpar(db_session, telefone)


def test_resposta_com_sinal_de_modelo_e_pergunta_explicita_continua_duvida(db_session, processador):
    """O contrário não pode quebrar: sinal de modelo junto de uma pergunta de verdade
    ("?") ainda é dúvida, respondida antes de retomar a coleta."""
    telefone = "+5511999982243"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        produto, _ = _catalogo_com_modelo_facial(db_session)
        db_session.add(ItemAtendimento(atendimento_id=atendimento.id, produto_id=produto.id, quantidade=1))
        db_session.commit()

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.PERGUNTAR_PRODUTO, tipo_leitor_mencionado=_TECNOLOGIA)
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="facial, e qual a diferença para a biometria?",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        # Foi para o RAG (em teste, sem base, ele pede clarificação).
        assert "RAG" in resposta.template_usado
    finally:
        _limpar(db_session, telefone)
