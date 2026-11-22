"""Regressão do report #7: pergunta cadastrada na base Q&A, feita no meio da coleta do
orçamento (fase Finalizando), era ignorada.

"Quais produtos a Inforrel vende?" é exatamente a pergunta de um par Q&A aprovado, mas o
classificador por regras não a reconhece como dúvida (intenção `desconhecido`). Fora de
Finalizando isso cai no fallback do processador, que consulta a base Q&A antes do
NAO_ENTENDI. Em Finalizando o `tratamento_principal` sempre produz uma resposta (repete a
pergunta pendente) e o fallback nunca roda: o cliente recebia de novo "Que tipo de
equipamento você precisa?" em vez da resposta cadastrada.

Classificação REAL (só regras, sem LLM) e um buscador Q&A falso injetado: o assunto é o
roteamento, não o conteúdo da base nem o ranking do full-text.
"""

import asyncio

import pytest
from database import Database
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.processador import ProcessadorMensagem
from services.rag.qa_service import ParRecuperado

_PERGUNTA_CADASTRADA = "Quais produtos a Inforrel vende?"
_RESPOSTA_CADASTRADA = "A Inforrel trabalha com catracas, controladores de acesso e relógios de ponto (teste report 7)."


class _QAFalso:
    """Responde só a pergunta cadastrada, como a base real (que a acha por full-text)."""

    habilitado = True

    async def buscar_melhor(self, query, *, apenas_aprovados=True, dlog=None):
        if query.strip().lower() != _PERGUNTA_CADASTRADA.lower():
            return None
        return ParRecuperado(
            id=-7,
            id_externo="teste_report_7",
            pergunta=_PERGUNTA_CADASTRADA,
            resposta=_RESPOSTA_CADASTRADA,
            contexto="geral",
            tags=[],
            score=0.46,
            distancia=0.54,
        )


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    return ProcessadorMensagem(qa=_QAFalso())


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _conversar(processador, db_session, telefone, mensagens):
    return [
        asyncio.run(processador.processar(db=db_session, telefone=telefone, conteudo=m)) for m in mensagens
    ]


def test_pergunta_cadastrada_antes_de_saber_o_tipo_de_produto(db_session, processador):
    """O caso do report: orçamento pedido sem dizer o produto, e a pergunta cadastrada."""
    telefone = "+5500000070701"
    _limpar(db_session, telefone)
    try:
        respostas = _conversar(
            processador,
            db_session,
            telefone,
            ["olá", "Meu nome é Carlos", "quero um orçamento novo", _PERGUNTA_CADASTRADA],
        )
        assert _RESPOSTA_CADASTRADA in respostas[-1].resposta
    finally:
        _limpar(db_session, telefone)


def test_pergunta_cadastrada_no_meio_da_coleta_responde_e_retoma(db_session, processador):
    """Com uma pergunta da coleta pendente: responde a cadastrada e retoma a pendente."""
    telefone = "+5500000070702"
    _limpar(db_session, telefone)
    try:
        respostas = _conversar(
            processador,
            db_session,
            telefone,
            ["olá", "Meu nome é Carlos", "quero orçamento de relógio de ponto", _PERGUNTA_CADASTRADA],
        )
        pergunta_pendente = respostas[-2].resposta.strip().splitlines()[-1]
        assert _RESPOSTA_CADASTRADA in respostas[-1].resposta
        assert pergunta_pendente in respostas[-1].resposta
    finally:
        _limpar(db_session, telefone)


def test_mensagem_sem_par_cadastrado_continua_repetindo_a_pendente(db_session, processador):
    """Sem par Q&A, nada muda: a pergunta pendente é repetida."""
    telefone = "+5500000070703"
    _limpar(db_session, telefone)
    try:
        respostas = _conversar(
            processador,
            db_session,
            telefone,
            ["olá", "Meu nome é Carlos", "quero um orçamento novo", "hmm deixa eu ver aqui"],
        )
        assert _RESPOSTA_CADASTRADA not in respostas[-1].resposta
        assert "Que tipo de equipamento" in respostas[-1].resposta
    finally:
        _limpar(db_session, telefone)
