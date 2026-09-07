"""Testes de `ProcessadorMensagem._responder_com_rag` e do fluxo REQ-003.7/REQ-003.11
(clarificação única antes de escalar para humano, e envio de catálogo) — zero cobertura
antes desta Fase 3.

`RetrievalService`/`QAService` são substituídos por dublês controláveis (retornam listas
fixas, sem rede) — o que se testa aqui é a lógica de decisão em `processador.py`, não a
qualidade de busca (isso já é coberto por `test_retrieval_service.py`). O restante segue o
padrão dos demais testes do projeto: base real (`Database()`), sem pytest-asyncio
(`asyncio.run`), limpando os dados do telefone de teste ao final.
"""

import asyncio

import pytest
from database import Database
from models import Contato, ModoOperacao
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, identificar_por_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem
from services.rag.qa_service import ParRecuperado
from services.rag.retrieval import DocumentoRecuperado
from services.respostas import MensagemId


class _RetrievalFake:
    def __init__(self, resultados=None):
        self.habilitado = True
        self.resultados = resultados or []

    async def buscar_trechos(self, query, dlog=None):
        return self.resultados


class _QAFake:
    def __init__(self, resultados=None):
        self.habilitado = True
        self.resultados = resultados or []

    async def buscar_melhor(self, query, apenas_aprovados=True, dlog=None):
        return self.resultados[0] if self.resultados else None


def _doc(titulo="Doc de teste", score=0.9):
    return DocumentoRecuperado(
        id=1,
        id_externo="doc:teste",
        id_documento_origem="doc:teste:origem",
        tipo="produto",
        titulo=titulo,
        conteudo="Conteúdo de teste sobre o produto.",
        score=score,
        distancia=1 - score,
    )


def _par_qa(score=0.9):
    return ParRecuperado(
        id=1,
        id_externo="qa:teste",
        pergunta="Pergunta de teste?",
        resposta="Resposta curada de teste.",
        contexto=None,
        tags=[],
        score=score,
        distancia=1 - score,
    )


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


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


# ---------------------------------------------------------------------------
# _responder_com_rag: prioridade QA > RAG > fallback genérico
# ---------------------------------------------------------------------------


def test_responder_com_rag_prioriza_qa_sobre_rag():
    p = ProcessadorMensagem(retrieval=_RetrievalFake([_doc()]), qa=_QAFake([_par_qa()]))
    resposta = asyncio.run(
        p._responder_com_rag(conteudo_cliente="dúvida", template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO)
    )
    assert resposta.texto == "Resposta curada de teste."
    assert resposta.template_usado == "qa_pair"
    assert resposta.rag_utilizada is True


def test_responder_com_rag_usa_rag_quando_qa_vazio():
    p = ProcessadorMensagem(retrieval=_RetrievalFake([_doc()]), qa=_QAFake([]))
    resposta = asyncio.run(
        p._responder_com_rag(conteudo_cliente="dúvida", template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO)
    )
    # Sem LLM (usar_llm=False, nenhum LLM injetado), gerar_com_rag devolve o texto do
    # fallback, mas com os metadados de RAG preenchidos — é isso que audita "achou algo".
    assert resposta.rag_utilizada is True
    assert resposta.trechos_rag and resposta.trechos_rag[0]["titulo"] == "Doc de teste"


def test_responder_com_rag_sem_nada_cai_no_fallback_generico():
    p = ProcessadorMensagem(retrieval=_RetrievalFake([]), qa=_QAFake([]))
    resposta = asyncio.run(
        p._responder_com_rag(conteudo_cliente="dúvida", template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO)
    )
    assert resposta.template_usado == "PRODUTO_SEM_CONTEXTO"
    assert resposta.trechos_rag == []


# ---------------------------------------------------------------------------
# REQ-003.7: 1 pergunta de clarificação antes de escalar para humano
# ---------------------------------------------------------------------------


def test_pergunta_produto_sem_base_pede_clarificacao_depois_escala(db_session):
    telefone = "5511999985001"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"])
    p = ProcessadorMensagem(retrieval=_RetrievalFake([]), qa=_QAFake([]))

    try:
        # 1ª vez: nada encontrado -> pergunta de clarificação, sem escalar ainda.
        resposta1 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="isso funciona debaixo d'água?",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta1.template_usado.startswith("RAG_PEDIR_CLARIFICACAO")
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.modo_operacao == ModoOperacao.AGENTE

        # 2ª vez: ainda nada encontrado -> escala para humano. Reidentifica o telefone
        # (agora já tem Contato/Atendimento) em vez de reusar `identificacao` (NOVO),
        # senão o processador tenta recriar o Contato e colide no telefone único.
        identificacao2 = identificar_por_telefone(db_session, telefone)
        resposta2 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="mas e sobre isso especificamente?",
                identificacao=identificacao2,
                resultado_class=resultado_class,
            )
        )
        assert resposta2.template_usado.startswith("RAG_ESCALADO_SEM_BASE")
        db_session.commit()
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
    finally:
        _limpar(db_session, telefone)


def test_pergunta_produto_encontra_conteudo_na_segunda_tentativa_nao_escala(db_session):
    """Se a clarificação trouxer conteúdo suficiente, responde normalmente e não escala."""
    telefone = "5511999985002"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"])
    retrieval = _RetrievalFake([])
    p = ProcessadorMensagem(retrieval=retrieval, qa=_QAFake([]))

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="pergunta vaga",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()

        # Agora a base "encontra" conteúdo relevante para a resposta à clarificação.
        retrieval.resultados = [_doc()]
        identificacao2 = identificar_por_telefone(db_session, telefone)
        resposta2 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="pergunta mais específica",
                identificacao=identificacao2,
                resultado_class=resultado_class,
            )
        )
        assert resposta2.rag_utilizada is True
        assert resposta2.trechos_rag

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
    finally:
        _limpar(db_session, telefone)


# ---------------------------------------------------------------------------
# REQ-003.11: envio de catálogo
# ---------------------------------------------------------------------------


def test_pedir_catalogo_tipo_ambiguo_pergunta_qual(db_session):
    p = ProcessadorMensagem()
    resultado_class = _resultado(Intencao.PEDIR_CATALOGO)
    resposta = asyncio.run(p._responder_pedir_catalogo(db_session, resultado_class))
    assert resposta.template_usado == "PEDIR_TIPO_CATALOGO"


def test_pedir_catalogo_dois_tipos_mencionados_pergunta_qual(db_session):
    p = ProcessadorMensagem()
    resultado_class = _resultado(Intencao.PEDIR_CATALOGO, tipos_produto=["catraca", "relogio_ponto"])
    resposta = asyncio.run(p._responder_pedir_catalogo(db_session, resultado_class))
    assert resposta.template_usado == "PEDIR_TIPO_CATALOGO"


def test_pedir_catalogo_link_configurado_envia_link(db_session):
    svc = ParametroService(db_session)
    original = svc.get_str("catalogo_link_catraca")
    try:
        svc.set("catalogo_link_catraca", "https://exemplo.test/catalogo-catracas.pdf")
        p = ProcessadorMensagem()
        resultado_class = _resultado(Intencao.PEDIR_CATALOGO, tipos_produto=["catraca"])
        resposta = asyncio.run(p._responder_pedir_catalogo(db_session, resultado_class))
        assert resposta.template_usado == "CATALOGO_ENVIADO"
        assert "https://exemplo.test/catalogo-catracas.pdf" in resposta.texto
    finally:
        svc.set("catalogo_link_catraca", original or "")


def test_pedir_catalogo_link_nao_configurado_avisa_indisponivel(db_session):
    svc = ParametroService(db_session)
    original = svc.get_str("catalogo_link_relogio_ponto")
    try:
        svc.set("catalogo_link_relogio_ponto", "")
        p = ProcessadorMensagem()
        resultado_class = _resultado(Intencao.PEDIR_CATALOGO, tipos_produto=["relogio_ponto"])
        resposta = asyncio.run(p._responder_pedir_catalogo(db_session, resultado_class))
        assert resposta.template_usado == "CATALOGO_INDISPONIVEL"
    finally:
        svc.set("catalogo_link_relogio_ponto", original or "")


def test_pedir_catalogo_fluxo_completo_pergunta_depois_resolve(db_session):
    """"Você tem catálogo?" -> pergunta qual; "catracas" (sem repetir "catálogo") ->
    resolve sozinho via `catalogo_pendente` (resposta "solta" à pergunta anterior)."""
    telefone = "5511999985003"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    svc = ParametroService(db_session)
    original = svc.get_str("catalogo_link_catraca")
    p = ProcessadorMensagem()

    try:
        svc.set("catalogo_link_catraca", "https://exemplo.test/catalogo-catracas.pdf")

        resultado1 = _resultado(Intencao.PEDIR_CATALOGO)
        resposta1 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Você tem catálogo?",
                identificacao=identificacao,
                resultado_class=resultado1,
            )
        )
        assert resposta1.template_usado == "PEDIR_TIPO_CATALOGO"
        db_session.commit()

        resultado2 = _resultado(Intencao.DESCONHECIDO, tipos_produto=["catraca"])
        identificacao2 = identificar_por_telefone(db_session, telefone)
        resposta2 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="catracas",
                identificacao=identificacao2,
                resultado_class=resultado2,
            )
        )
        assert resposta2.template_usado == "CATALOGO_ENVIADO"
        assert "https://exemplo.test/catalogo-catracas.pdf" in resposta2.texto
    finally:
        svc.set("catalogo_link_catraca", original or "")
        _limpar(db_session, telefone)
