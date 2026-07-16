"""Testes da continuação de atendimento encerrado (REQ-016.7/016.9, Fase 1).

Mesma estratégia das demais suítes de `_decidir_resposta`: injeta um
`ResultadoClassificacao` já pronto e chama via `asyncio.run`, sem depender do
classificador (regra ou LLM) acertar a intenção.
"""

import asyncio

import pytest
from database import Database
from models import Atendimento, FaseAtendimento, MotivoEncerramento, StatusAtendimento
from services import atendimentos as atendimentos_svc
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, criar_contato_sem_empresa
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


def _atendimento_encerrado_com_interesse(
    db_session, telefone, motivo=MotivoEncerramento.MANUAL_VENDEDOR
) -> Atendimento:
    """Cria um atendimento com `tipos_produto` capturado e o encerra com `motivo`."""
    contato = criar_contato_sem_empresa(db_session, telefone, nome=None)
    atendimento = atendimentos_svc.obter_ou_criar_atendimento(db_session, contato)
    processador_auxiliar = ProcessadorMensagem()
    asyncio.run(
        processador_auxiliar._atualizar_infos_atendimento(
            db_session, atendimento, _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"])
        )
    )
    atendimentos_svc.encerrar_atendimento(db_session, atendimento, motivo=motivo, ator="vendedor")
    return atendimento


def _identificacao(contato) -> ResultadoIdentificacao:
    return ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])


def test_atendimento_encerrado_dispara_pergunta_continuacao(db_session, processador):
    telefone = "5511999984001"
    try:
        atendimento = _atendimento_encerrado_com_interesse(db_session, telefone)
        contato = atendimento.contato

        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Aquele relógio ainda tá disponível?",
                identificacao=_identificacao(contato),
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta.template_usado == "PERGUNTA_CONTINUACAO_ATENDIMENTO"
        assert "relogio" in resposta.texto.lower()
        db_session.refresh(atendimento)
        assert atendimento.status == StatusAtendimento.ENCERRADO  # ainda não decidiu
    finally:
        _limpar(db_session, telefone)


def test_continuar_reabre_e_pergunta_confirma_interesse(db_session, processador):
    telefone = "5511999984002"
    try:
        atendimento = _atendimento_encerrado_com_interesse(db_session, telefone)
        contato = atendimento.contato
        identificacao = _identificacao(contato)

        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )

        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="1) Continuar",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta.template_usado == "CONFIRMAR_INTERESSE_ANTERIOR"
        db_session.refresh(atendimento)
        assert atendimento.status == StatusAtendimento.ATIVO
        assert atendimento.motivo_encerramento is None
        assert atendimento.reaberto_por == "cliente"
    finally:
        _limpar(db_session, telefone)


def test_manter_interesse_preserva_dados_capturados(db_session, processador):
    telefone = "5511999984003"
    try:
        atendimento = _atendimento_encerrado_com_interesse(db_session, telefone)
        contato = atendimento.contato
        identificacao = _identificacao(contato)

        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="continuar",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="sim, isso mesmo",
                identificacao=identificacao, resultado_class=_resultado(Intencao.CONFIRMAR),
            )
        )
        valor = processador._info_atendimento(db_session, atendimento.id, "tipos_produto")
        assert valor == "relogio_ponto"
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.ESCLARECENDO
    finally:
        _limpar(db_session, telefone)


def test_mudou_de_ideia_reinicia_qualificacao(db_session, processador):
    telefone = "5511999984004"
    try:
        atendimento = _atendimento_encerrado_com_interesse(db_session, telefone)
        contato = atendimento.contato
        identificacao = _identificacao(contato)

        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="continuar",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="mudei de ideia, quero outra coisa",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert processador._info_atendimento(db_session, atendimento.id, "tipos_produto") is None
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.ESCLARECENDO
        assert len(atendimento.itens) == 0
    finally:
        _limpar(db_session, telefone)


def test_novo_pedido_cria_atendimento_novo(db_session, processador):
    telefone = "5511999984005"
    try:
        atendimento_1 = _atendimento_encerrado_com_interesse(db_session, telefone)
        contato = atendimento_1.contato
        identificacao = _identificacao(contato)
        numero_1 = atendimento_1.numero_atendimento_cliente

        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="2) Novo pedido",
                identificacao=identificacao, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        # Mensagem seguinte com intenção comercial real cria o atendimento novo.
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Quero orçamento de catraca",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["catraca"]),
            )
        )
        db_session.refresh(atendimento_1)
        assert atendimento_1.status == StatusAtendimento.ENCERRADO  # não foi reaberto

        novo = atendimentos_svc.atendimento_ativo(db_session, contato)
        assert novo is not None
        assert novo.id != atendimento_1.id
        assert novo.numero_atendimento_cliente == numero_1 + 1
    finally:
        _limpar(db_session, telefone)


def test_concluido_conversao_nao_pergunta_cria_atendimento_direto(db_session, processador):
    telefone = "5511999984006"
    try:
        atendimento_1 = _atendimento_encerrado_com_interesse(
            db_session, telefone, motivo=MotivoEncerramento.CONCLUIDO_CONVERSAO
        )
        contato = atendimento_1.contato
        identificacao = _identificacao(contato)
        numero_1 = atendimento_1.numero_atendimento_cliente

        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Quero mais 3 catracas",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["catraca"]),
            )
        )
        assert resposta.template_usado != "PERGUNTA_CONTINUACAO_ATENDIMENTO"
        db_session.refresh(atendimento_1)
        assert atendimento_1.status == StatusAtendimento.ENCERRADO  # nunca reaberto

        novo = atendimentos_svc.atendimento_ativo(db_session, contato)
        assert novo is not None
        assert novo.id != atendimento_1.id
        assert novo.numero_atendimento_cliente == numero_1 + 1
    finally:
        _limpar(db_session, telefone)
