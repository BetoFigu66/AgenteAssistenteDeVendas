"""Testes de escalonamento para humano (REQ-004, Fase 5) — zero cobertura antes desta
fase. Padrão de integração real (base real via `Database()`, sem pytest-asyncio, telefone
de teste único por caso, limpo ao final) — mesma convenção de `test_regras_esclarecendo.py`
e `test_processador_categoria3_pre_identificacao.py`.
"""

import asyncio

import pytest
from database import Database
from models import Contato, ModoOperacao, MotivoEscalonamento
from services.atendimentos import obter_ou_criar_atendimento
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, identificar_por_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem
from services.rag.retrieval import DocumentoRecuperado


class _RetrievalFake:
    def __init__(self, resultados=None):
        self._score_minimo_padrao = 0.70
        self.habilitado = True
        self.resultados = resultados or []

    async def buscar(self, query, tipo=None, **kwargs):
        return self.resultados


class _QAFake:
    def __init__(self, resultados=None):
        self._score_minimo_padrao = 0.80
        self.habilitado = True
        self.resultados = resultados or []

    async def buscar(self, query, apenas_aprovados=True, **kwargs):
        return self.resultados


def _doc(score=0.9):
    return DocumentoRecuperado(
        id=1,
        id_externo="doc:teste",
        id_documento_origem="doc:teste:origem",
        tipo="produto",
        titulo="Doc de teste",
        conteudo="Conteúdo de teste sobre o produto.",
        score=score,
        distancia=1 - score,
    )


def _resultado(intencao: Intencao, confianca_nivel=NivelConfianca.ALTA, **entidades_kwargs) -> ResultadoClassificacao:
    return ResultadoClassificacao(
        intencoes=[intencao],
        confianca=0.9 if confianca_nivel == NivelConfianca.ALTA else 0.1,
        confianca_nivel=confianca_nivel,
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


def test_escalar_humano_seta_modo_humano_e_persiste_dados(db_session):
    telefone = "5511999987001"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.ESCALAR_HUMANO)
    p = ProcessadorMensagem()

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="quero falar com um atendente",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
        atendimento = contato.atendimentos[0]
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.SOLICITADO_CLIENTE.value
        assert atendimento.escalado_por == "cliente"
        assert atendimento.escalado_em is not None
        assert atendimento.resumo_escalonamento
        assert telefone in atendimento.resumo_escalonamento
    finally:
        _limpar(db_session, telefone)


def test_reclamar_seta_modo_humano(db_session):
    telefone = "5511999987002"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.RECLAMAR)
    p = ProcessadorMensagem()

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="isso não funciona, que problema",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.RECLAMACAO.value
    finally:
        _limpar(db_session, telefone)


def test_quantidade_grande_escala_sem_intencao_explicita(db_session):
    telefone = "5511999987003"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.DESCONHECIDO, quantidades=[10])
    p = ProcessadorMensagem()

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="preciso de 10 catracas",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.PROJETO_COMPLEXO.value
    finally:
        _limpar(db_session, telefone)


def test_quantidade_pequena_nao_escala(db_session):
    telefone = "5511999987004"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.DESCONHECIDO, quantidades=[2])
    p = ProcessadorMensagem()

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="preciso de 2 catracas",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        if contato:
            for atendimento in contato.atendimentos:
                assert atendimento.modo_operacao == ModoOperacao.AGENTE
    finally:
        _limpar(db_session, telefone)


def test_faixa_funcionarios_acima_limiar_escala(db_session):
    telefone = "5511999987005"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.DESCONHECIDO, faixa_funcionarios=80)
    p = ProcessadorMensagem()

    svc = ParametroService(db_session)
    limiar_original = svc.get_str("escalonamento_limiar_funcionarios")
    try:
        svc.set("escalonamento_limiar_funcionarios", "50")
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="temos uns 80 funcionários",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.PROJETO_COMPLEXO.value
    finally:
        svc.set("escalonamento_limiar_funcionarios", limiar_original or "50")
        _limpar(db_session, telefone)


def test_leitor_facial_escala(db_session):
    telefone = "5511999987006"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.DESCONHECIDO, tipo_leitor_mencionado="facial")
    p = ProcessadorMensagem()

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="quero controle facial na porta",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.PROJETO_COMPLEXO.value
    finally:
        _limpar(db_session, telefone)


def test_projeto_complexo_nao_repete_quando_ja_humano(db_session):
    telefone = "5511999987007"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    p = ProcessadorMensagem()

    try:
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="preciso de 10 catracas",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO, quantidades=[10]),
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        escalado_em_1 = atendimento.escalado_em

        identificacao2 = identificar_por_telefone(db_session, telefone)
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="e mais 10 catracas também",
                identificacao=identificacao2,
                resultado_class=_resultado(Intencao.DESCONHECIDO, quantidades=[10]),
            )
        )
        db_session.commit()
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.escalado_em == escalado_em_1
    finally:
        _limpar(db_session, telefone)


def test_confianca_baixa_escala_na_segunda_ocorrencia_consecutiva(db_session):
    telefone = "5511999987008"
    try:
        contato = Contato(telefone=telefone, nome="Cliente Confiança Baixa")
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)
        atendimento = obter_ou_criar_atendimento(db_session, contato)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        p = ProcessadorMensagem(retrieval=_RetrievalFake([]), qa=_QAFake([]))
        resultado_class = _resultado(Intencao.DESCONHECIDO, confianca_nivel=NivelConfianca.BAIXA)

        resposta1 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="asdkjaslkdj confuso",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta1.template_usado == "NAO_ENTENDI"
        db_session.commit()
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.AGENTE

        resposta2 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="ainda confuso pqoiwjeqwoi",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta2.template_usado == "ESCALADO_BAIXA_CONFIANCA"
        db_session.commit()
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.BAIXA_CONFIANCA.value
    finally:
        _limpar(db_session, telefone)


def test_retrofit_rag_escalado_sem_base_preenche_motivo(db_session):
    telefone = "5511999987009"
    try:
        contato = Contato(telefone=telefone, nome="Cliente RAG Sem Base")
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)
        atendimento = obter_ou_criar_atendimento(db_session, contato)

        p = ProcessadorMensagem(retrieval=_RetrievalFake([]), qa=_QAFake([]))
        resultado_class = _resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"])
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])

        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="isso funciona debaixo d'água?",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()

        identificacao2 = identificar_por_telefone(db_session, telefone)
        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="mas e sobre isso especificamente?",
                identificacao=identificacao2,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.BASE_INSUFICIENTE.value
        assert atendimento.resumo_escalonamento
    finally:
        _limpar(db_session, telefone)


def test_manual_takeover_endpoint_registra_motivo(client, db_session):
    telefone = "5511999987010"
    try:
        contato = Contato(telefone=telefone, nome="Cliente Takeover Manual")
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)
        atendimento = obter_ou_criar_atendimento(db_session, contato)

        r = client.patch(
            f"/api/atendimentos/{atendimento.id}/modo-operacao",
            json={"modo_operacao": "humano"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["modo_operacao"] == "humano"
        assert body["motivo_escalonamento"] == MotivoEscalonamento.MANUAL_VENDEDOR.value
        assert body["escalado_por"] == "Pytest Runner"
        assert body["resumo_escalonamento"]
    finally:
        _limpar(db_session, telefone)
