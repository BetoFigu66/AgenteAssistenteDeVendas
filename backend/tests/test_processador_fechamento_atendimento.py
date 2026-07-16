"""Testes da pergunta de fechamento do atendimento (REQ-016.10, Fase 1).

Mesma estratégia das demais suítes de `_decidir_resposta`: injeta um
`ResultadoClassificacao` já pronto e chama via `asyncio.run`.
"""

import asyncio

import pytest
from database import Database
from models import ModoOperacao, StatusAtendimento
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao
from services.processador import ProcessadorMensagem


def _resultado(intencao: Intencao, **entidades_kwargs) -> ResultadoClassificacao:
    return ResultadoClassificacao(
        intencoes=[intencao],
        confianca=0.9,
        confianca_nivel=NivelConfianca.ALTA,
        entidades=EntidadesExtraidas(**entidades_kwargs),
        origem="regra",
    )


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def test_duvida_pura_dispara_pergunta_fechamento(db_session, processador):
    telefone = "5511999985001"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Qual o modelo de catraca vocês tem?",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["catraca"]),
            )
        )
        assert "PERGUNTA_FECHAMENTO_ATENDIMENTO" in (resposta.template_usado or "")
        assert "mais alguma coisa" in resposta.texto.lower()
    finally:
        _limpar(db_session, telefone)


def test_resposta_negativa_encerra_atendimento(db_session, processador):
    telefone = "5511999985002"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Qual o modelo de catraca vocês tem?",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["catraca"]),
            )
        )

        from models import Contato

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao2 = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        atendimento = contato.atendimentos[0]

        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Não, obrigado",
                identificacao=identificacao2, resultado_class=_resultado(Intencao.NEGAR),
            )
        )
        assert resposta.template_usado == "DESPEDIDA_ATENDIMENTO_ENCERRADO"
        db_session.refresh(atendimento)
        assert atendimento.status == StatusAtendimento.ENCERRADO
        assert atendimento.motivo_encerramento == "concluido_pelo_cliente"
        assert atendimento.encerrado_por == "cliente"
    finally:
        _limpar(db_session, telefone)


def test_resposta_afirmativa_mantem_ativo_e_segue_fluxo(db_session, processador):
    telefone = "5511999985003"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Qual o modelo de catraca vocês tem?",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["catraca"]),
            )
        )

        from models import Contato

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao2 = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        atendimento = contato.atendimentos[0]

        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Sim, tenho outra dúvida",
                identificacao=identificacao2, resultado_class=_resultado(Intencao.CONFIRMAR),
            )
        )
        db_session.refresh(atendimento)
        assert atendimento.status == StatusAtendimento.ATIVO
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
        assert processador._info_atendimento(db_session, atendimento.id, "fechamento_atendimento_pendente") is None
        assert resposta is not None  # alguma resposta (fallback/QA) — não a de fechamento
    finally:
        _limpar(db_session, telefone)
