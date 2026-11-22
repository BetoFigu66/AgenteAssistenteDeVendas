"""Report #1435: "pode me explicar melhor como cada modelo de catraca funciona?" recebia o
pedido de clarificação ("Pode me explicar com outras palavras...") e, na insistência, era
escalado por base insuficiente.

Pergunta de visão geral ("cada modelo", "quais modelos") não se parece com nenhum trecho
isolado da base, então a RAG nunca passa do limiar; mas o catálogo (`modelos`) tem
justamente o que o cliente pediu: marca, tecnologia de leitura e aplicação de cada modelo.

Mesma estratégia de `test_processador_responder_com_rag.py`: RAG e Q&A substituídos por
dublês vazios (o defeito é a decisão, não a busca), base real, `asyncio.run`.
"""

import asyncio

import pytest
from database import Database
from models import AtributoAdicionalModelo, Contato, FaseAtendimento, Modelo, ModoOperacao, Produto
from services.classificador import (
    EntidadesExtraidas,
    Intencao,
    NivelConfianca,
    ResultadoClassificacao,
    pedido_visao_geral_modelos,
)
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, identificar_por_telefone
from services.processador import ProcessadorMensagem

from tests.apoio_pilha import documento_ja_pedido


class _RetrievalVazio:
    habilitado = True

    async def buscar_trechos(self, query, dlog=None):
        return []


class _QAVazio:
    habilitado = True

    async def buscar_melhor(self, query, apenas_aprovados=True, dlog=None):
        return None


def _resultado(intencao: Intencao, **entidades_kwargs) -> ResultadoClassificacao:
    return ResultadoClassificacao(
        intencoes=[intencao],
        confianca=0.75,
        confianca_nivel=NivelConfianca.ALTA,
        entidades=EntidadesExtraidas(**entidades_kwargs),
        origem="regra",
    )


_PRODUTO_TESTE = "Catraca (teste 1435)"
_MODELOS_TESTE = [
    ("TESTE-1435-A", "Catraca Alfa 1435", "MarcaUm", "Academias", "facial"),
    ("TESTE-1435-B", "Catraca Beta 1435", "MarcaDois", "Condomínios", "biometria"),
]


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def catalogo_teste(db_session):
    produto = Produto(descricao=_PRODUTO_TESTE, ativo=True)
    db_session.add(produto)
    db_session.flush()
    for codigo, descricao, marca, aplicacao, tecnologia in _MODELOS_TESTE:
        modelo = Modelo(
            produto_id=produto.id, codigo=codigo, descricao=descricao, marca=marca,
            aplicacao=aplicacao, preco_tabela=0, ativo=True,
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


@pytest.mark.parametrize(
    "texto",
    [
        "pode me explicar melhor como cada modelo de catraca funciona?",
        "quero saber características e detalhes sobre cada tipo de catraca",
        "quais modelos de catraca vocês têm?",
        "qual a diferença entre os modelos?",
    ],
)
def test_detecta_pedido_de_visao_geral(texto):
    assert pedido_visao_geral_modelos(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "como funciona a catraca facial?",
        "a catraca tem nobreak?",
        "quero uma catraca para 100 pessoas",
    ],
)
def test_pergunta_especifica_nao_e_visao_geral(texto):
    assert not pedido_visao_geral_modelos(texto)


def test_cada_modelo_de_catraca_responde_com_o_catalogo_em_finalizando(db_session, catalogo_teste):
    """O caso do report: em Finalizando (coleta da catraca), a dúvida de visão geral é
    respondida com os modelos do catálogo, sem pedir clarificação nem escalar, e a coleta
    continua."""
    telefone = "+5511999981435"
    p = ProcessadorMensagem(retrieval=_RetrievalVazio(), qa=_QAVazio())
    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento de catraca",
                identificacao=ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[]),
                resultado_class=_resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["catraca"]),
            )
        )
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        documento_ja_pedido(db_session, atendimento)
        db_session.commit()
        assert atendimento.fase == FaseAtendimento.FINALIZANDO

        resposta = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="pode me explicar melhor como cada modelo de catraca funciona?",
                identificacao=identificar_por_telefone(db_session, telefone),
                resultado_class=_resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["catraca"]),
            )
        )

        assert "RAG_PEDIR_CLARIFICACAO" not in resposta.template_usado
        assert resposta.template_usado.startswith("MODELOS_DO_PRODUTO")
        for _codigo, descricao, marca, aplicacao, _tecnologia in _MODELOS_TESTE:
            assert descricao in resposta.texto
            assert marca in resposta.texto
            assert aplicacao.lower() in resposta.texto.lower()
        assert "reconhecimento facial" in resposta.texto
        assert "biometria" in resposta.texto
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
    finally:
        _limpar(db_session, telefone)
