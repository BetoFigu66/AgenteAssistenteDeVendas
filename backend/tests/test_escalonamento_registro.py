"""Registro do gatilho/evidências de cada escalonamento e avaliação humana (REQ-004.5B/5C).

Mesmo padrão de `test_escalonamento.py` (banco real, telefone único por caso, limpo ao
final). Nenhum teste grava em `parametros`: o limiar de funcionários é trocado por
`monkeypatch` em `ParametroService`.
"""

import asyncio
import json

import pytest
from database import Database
from fastapi.testclient import TestClient
from models import (
    Contato,
    Escalonamento,
    EventoAtendimento,
    GatilhoEscalonamento,
    Mensagem,
    ModoOperacao,
    MotivoEscalonamento,
    OrigemMensagem,
    TipoEventoAtendimento,
)
from services.atendimentos import obter_ou_criar_atendimento
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.conversacao.regras_globais import _gatilhos_projeto_complexo
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, identificar_por_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem


class _RetrievalFake:
    habilitado = True

    async def buscar_trechos(self, query, dlog=None):
        return []


class _QAFake:
    habilitado = True

    async def buscar_melhor(self, query, apenas_aprovados=True, dlog=None):
        return None


def _resultado(intencao, confianca_nivel=NivelConfianca.ALTA, origem="regra", **entidades_kwargs):
    return ResultadoClassificacao(
        intencoes=[intencao],
        confianca=0.9 if confianca_nivel == NivelConfianca.ALTA else 0.1,
        confianca_nivel=confianca_nivel,
        entidades=EntidadesExtraidas(**entidades_kwargs),
        origem=origem,
    )


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def limiar_funcionarios(monkeypatch):
    """Fixa o limiar de funcionários do projeto complexo sem gravar em `parametros`."""
    valor = {"limiar": 50}
    original = ParametroService.get_int

    def _get_int(self, nome, default=0):
        if nome == "escalonamento_limiar_funcionarios":
            return valor["limiar"]
        return original(self, nome, default)

    monkeypatch.setattr(ParametroService, "get_int", _get_int)
    return valor


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _novo(telefone):
    return ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])


def _decidir(p, db_session, telefone, conteudo, resultado_class, identificacao=None):
    return asyncio.run(
        p._decidir_resposta(
            db=db_session,
            telefone=telefone,
            conteudo=conteudo,
            identificacao=identificacao or _novo(telefone),
            resultado_class=resultado_class,
        )
    )


def _escalonamentos(db_session, telefone):
    contato = db_session.query(Contato).filter_by(telefone=telefone).first()
    assert contato is not None
    atendimento = contato.atendimentos[0]
    db_session.refresh(atendimento)
    return atendimento, atendimento.escalonamentos


def _assert_sem_texto(escalonamento, *textos):
    serializado = json.dumps(escalonamento.evidencias, ensure_ascii=False).lower()
    for texto in textos:
        assert texto.lower() not in serializado


def _assert_vinculado_ao_evento(db_session, escalonamento):
    evento = db_session.get(EventoAtendimento, escalonamento.evento_id)
    assert evento is not None
    assert evento.tipo == TipoEventoAtendimento.ESCALADO.value
    assert evento.atendimento_id == escalonamento.atendimento_id
    assert evento.motivo == escalonamento.motivo


# ----------------------------------------------------------------------
# Gatilhos de projeto complexo (sem banco)
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entidades", "esperado"),
    [
        (EntidadesExtraidas(quantidades=[2, 3]), []),
        (EntidadesExtraidas(quantidades=[1, 2, 3, 20, 25]), [GatilhoEscalonamento.QUANTIDADE_MINIMA]),
        (EntidadesExtraidas(faixa_funcionarios=45), []),
        (EntidadesExtraidas(faixa_funcionarios=80), [GatilhoEscalonamento.FAIXA_FUNCIONARIOS]),
        (EntidadesExtraidas(tipo_leitor_mencionado="facial"), [GatilhoEscalonamento.LEITOR_FACIAL]),
        (
            EntidadesExtraidas(quantidades=[10], faixa_funcionarios=80, tipo_leitor_mencionado="facial"),
            [
                GatilhoEscalonamento.QUANTIDADE_MINIMA,
                GatilhoEscalonamento.FAIXA_FUNCIONARIOS,
                GatilhoEscalonamento.LEITOR_FACIAL,
            ],
        ),
    ],
)
def test_gatilhos_projeto_complexo_lista_todas_as_condicoes(entidades, esperado):
    assert _gatilhos_projeto_complexo(entidades, limiar_funcionarios=50) == esperado


# ----------------------------------------------------------------------
# Registro por motivo
# ----------------------------------------------------------------------


def test_solicitado_cliente_registra_gatilho_e_classificacao(db_session):
    telefone = "+5511999964001"
    conteudo = "quero falar com um atendente agora"
    try:
        _decidir(ProcessadorMensagem(), db_session, telefone, conteudo, _resultado(Intencao.ESCALAR_HUMANO))
        db_session.commit()
        atendimento, escalonamentos = _escalonamentos(db_session, telefone)

        # O fluxo de antes continua igual.
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.SOLICITADO_CLIENTE.value

        assert len(escalonamentos) == 1
        esc = escalonamentos[0]
        assert esc.motivo == MotivoEscalonamento.SOLICITADO_CLIENTE.value
        assert esc.gatilhos == [GatilhoEscalonamento.INTENCAO_ESCALAR_HUMANO.value]
        assert esc.ator == "cliente"
        assert esc.evidencias == {
            "intencoes": ["escalar_humano"],
            "confianca": 0.9,
            "confianca_nivel": "alta",
            "origem_classificacao": "regra",
        }
        assert esc.avaliacao is None
        _assert_vinculado_ao_evento(db_session, esc)
        _assert_sem_texto(esc, conteudo, "atendente")
    finally:
        _limpar(db_session, telefone)


def test_reclamacao_registra_origem_llm(db_session):
    telefone = "+5511999964002"
    try:
        _decidir(
            ProcessadorMensagem(),
            db_session,
            telefone,
            "isso não funciona, que absurdo",
            _resultado(Intencao.RECLAMAR, origem="llm"),
        )
        db_session.commit()
        _, escalonamentos = _escalonamentos(db_session, telefone)
        esc = escalonamentos[0]
        assert esc.motivo == MotivoEscalonamento.RECLAMACAO.value
        assert esc.gatilhos == [GatilhoEscalonamento.INTENCAO_RECLAMAR.value]
        assert esc.evidencias["intencoes"] == ["reclamar"]
        assert esc.evidencias["origem_classificacao"] == "llm"
        _assert_sem_texto(esc, "absurdo")
    finally:
        _limpar(db_session, telefone)


def test_projeto_complexo_duas_condicoes_registra_ambas_com_valores_e_limiares(db_session, limiar_funcionarios):
    telefone = "+5511999964003"
    limiar_funcionarios["limiar"] = 60
    try:
        _decidir(
            ProcessadorMensagem(),
            db_session,
            telefone,
            "preciso de 10 catracas com facial, somos 45 funcionários",
            _resultado(
                Intencao.DESCONHECIDO,
                quantidades=[10],
                faixa_funcionarios=45,
                tipo_leitor_mencionado="facial",
            ),
        )
        db_session.commit()
        atendimento, escalonamentos = _escalonamentos(db_session, telefone)
        assert atendimento.motivo_escalonamento == MotivoEscalonamento.PROJETO_COMPLEXO.value

        esc = escalonamentos[0]
        assert esc.gatilhos == [
            GatilhoEscalonamento.QUANTIDADE_MINIMA.value,
            GatilhoEscalonamento.LEITOR_FACIAL.value,
        ]
        ev = esc.evidencias
        assert ev["quantidades"] == [10]
        assert ev["quantidade_minima"] == 4
        # Faixa abaixo do limiar vigente: registrada, mas não entrou nos gatilhos.
        assert ev["faixa_funcionarios"] == 45
        assert ev["limiar_funcionarios"] == 60
        assert ev["tipo_leitor_mencionado"] == "facial"
        assert ev["origem_classificacao"] == "regra"
        _assert_vinculado_ao_evento(db_session, esc)
        _assert_sem_texto(esc, "catracas", "funcionários")
    finally:
        _limpar(db_session, telefone)


def test_projeto_complexo_so_faixa_funcionarios_usa_limiar_do_parametro(db_session, limiar_funcionarios):
    telefone = "+5511999964004"
    limiar_funcionarios["limiar"] = 30
    try:
        _decidir(
            ProcessadorMensagem(),
            db_session,
            telefone,
            "somos 45 funcionários",
            _resultado(Intencao.DESCONHECIDO, faixa_funcionarios=45),
        )
        db_session.commit()
        _, escalonamentos = _escalonamentos(db_session, telefone)
        esc = escalonamentos[0]
        assert esc.gatilhos == [GatilhoEscalonamento.FAIXA_FUNCIONARIOS.value]
        assert esc.evidencias["limiar_funcionarios"] == 30
        assert esc.evidencias["quantidades"] == []
    finally:
        _limpar(db_session, telefone)


def test_baixa_confianca_registra_ocorrencias_e_limiar(db_session):
    telefone = "+5511999964005"
    try:
        contato = Contato(telefone=telefone, nome="Cliente Baixa Confiança")
        db_session.add(contato)
        db_session.commit()
        obter_ou_criar_atendimento(db_session, contato)
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        p = ProcessadorMensagem(retrieval=_RetrievalFake(), qa=_QAFake())
        resultado = _resultado(Intencao.DESCONHECIDO, confianca_nivel=NivelConfianca.BAIXA)

        # Mesma sequência de `test_escalonamento.py`: CNPJ, 1ª ocorrência, 2ª → escala.
        for conteudo in ("asdkj confuso", "ainda confuso qwoi", "mais confuso kqpw"):
            _decidir(p, db_session, telefone, conteudo, resultado, identificacao)
            db_session.commit()

        _, escalonamentos = _escalonamentos(db_session, telefone)
        esc = escalonamentos[0]
        assert esc.motivo == MotivoEscalonamento.BAIXA_CONFIANCA.value
        assert esc.gatilhos == [GatilhoEscalonamento.BAIXA_CONFIANCA_REPETIDA.value]
        assert esc.evidencias["ocorrencias_consecutivas"] == 2
        assert esc.evidencias["confianca_nivel"] == "baixa"
        assert esc.evidencias["confianca"] == 0.1
        assert esc.evidencias["limiar_confianca_baixa"] == ParametroService(db_session).limiares_classificador()[
            "baixa_max"
        ]
        _assert_sem_texto(esc, "confuso")
    finally:
        _limpar(db_session, telefone)


def test_base_insuficiente_registra_estado_da_busca(db_session):
    telefone = "+5511999964006"
    try:
        contato = Contato(telefone=telefone, nome="Cliente Base Insuficiente")
        db_session.add(contato)
        db_session.commit()
        obter_ou_criar_atendimento(db_session, contato)
        p = ProcessadorMensagem(retrieval=_RetrievalFake(), qa=_QAFake())
        resultado = _resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"])

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        _decidir(p, db_session, telefone, "funciona debaixo d'água?", resultado, identificacao)
        db_session.commit()
        identificacao = identificar_por_telefone(db_session, telefone)
        _decidir(p, db_session, telefone, "e sobre isso especificamente?", resultado, identificacao)
        db_session.commit()

        _, escalonamentos = _escalonamentos(db_session, telefone)
        esc = escalonamentos[0]
        assert esc.motivo == MotivoEscalonamento.BASE_INSUFICIENTE.value
        assert esc.gatilhos == [GatilhoEscalonamento.BASE_SEM_RESPOSTA.value]
        ev = esc.evidencias
        assert ev["qa_encontrado"] is False
        assert ev["trechos_rag"] == 0
        assert ev["rag_habilitado"] is True
        assert "rag_score_minimo" in ev  # o fake não tem limiar: None
        assert ev["clarificacoes_pedidas"] == 1
        assert ev["intencoes"] == ["perguntar_produto"]
        _assert_sem_texto(esc, "debaixo", "especificamente")
    finally:
        _limpar(db_session, telefone)


def test_modelo_nao_reconhecido_registra_tentativas_e_sinais(db_session):
    telefone = "+5511999964007"
    p = ProcessadorMensagem()
    try:
        # Mesmo roteiro de `test_f2_modelo_escala_para_humano_apos_tentativas_sem_correspondencia`.
        _decidir(p, db_session, telefone, "Quero orçamento de relógio de ponto",
                 _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"]))
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        for conteudo in ("Seria biométrico", "Biométrico mesmo"):
            _decidir(p, db_session, telefone, conteudo,
                     _resultado(Intencao.DESCONHECIDO, tipo_leitor_mencionado="biometria_inexistente_teste"),
                     identificacao)
        db_session.commit()

        atendimento, escalonamentos = _escalonamentos(db_session, telefone)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        esc = escalonamentos[0]
        assert esc.motivo == MotivoEscalonamento.MODELO_NAO_RECONHECIDO.value
        assert esc.gatilhos == [GatilhoEscalonamento.TENTATIVAS_ESGOTADAS.value]
        assert esc.ator == "sistema:resolucao_modelo"
        ev = esc.evidencias
        assert ev["tentativas"] == 2
        assert ev["tentativas_maximas"] == 2
        assert ev["sinais_extraidos"]["tipo_leitor"] == "biometria_inexistente_teste"
        assert ev["origem_classificacao"] == "regra"
        _assert_sem_texto(esc, "biométrico mesmo")
    finally:
        _limpar(db_session, telefone)


# ----------------------------------------------------------------------
# Vínculo com mensagem e processamento (caminho real, `processar()`)
# ----------------------------------------------------------------------


def test_processar_vincula_escalonamento_a_mensagem_processamento_e_evento(db_session):
    telefone = "+5511999964008"
    try:
        _limpar(db_session, telefone)
        asyncio.run(ProcessadorMensagem().processar(db_session, telefone, "quero falar com um atendente"))
        db_session.commit()

        msg_in = (
            db_session.query(Mensagem)
            .filter_by(telefone=telefone, origem=OrigemMensagem.USER)
            .order_by(Mensagem.id.desc())
            .first()
        )
        _, escalonamentos = _escalonamentos(db_session, telefone)
        assert len(escalonamentos) == 1, "a mensagem deveria ter escalado (pedido de humano)"
        esc = escalonamentos[0]
        assert esc.mensagem_id == msg_in.id
        assert esc.processamento_id == msg_in.processamento_id is not None
        evento = db_session.get(EventoAtendimento, esc.evento_id)
        assert evento.mensagem_id == msg_in.id
        assert evento.processamento_id == msg_in.processamento_id
        assert "origem_classificacao" in esc.evidencias
        _assert_sem_texto(esc, "atendente")
    finally:
        _limpar(db_session, telefone)


# ----------------------------------------------------------------------
# API: takeover manual, leitura e avaliação
# ----------------------------------------------------------------------


def _atendimento_escalado_manual(client, db_session, telefone):
    contato = Contato(telefone=telefone, nome="Cliente Avaliação")
    db_session.add(contato)
    db_session.commit()
    atendimento = obter_ou_criar_atendimento(db_session, contato)
    db_session.commit()
    r = client.patch(f"/api/atendimentos/{atendimento.id}/modo-operacao", json={"modo_operacao": "humano"})
    assert r.status_code == 200, r.text
    return atendimento.id


def test_takeover_manual_registra_sem_mensagem_e_aparece_na_leitura(client, db_session):
    telefone = "+5511999964009"
    try:
        atendimento_id = _atendimento_escalado_manual(client, db_session, telefone)

        r = client.get(f"/api/atendimentos/{atendimento_id}/escalonamentos")
        assert r.status_code == 200
        lista = r.json()["escalonamentos"]
        assert len(lista) == 1
        esc = lista[0]
        assert esc["motivo"] == MotivoEscalonamento.MANUAL_VENDEDOR.value
        assert esc["gatilhos"] == [GatilhoEscalonamento.ASSUMIDO_PELO_VENDEDOR.value]
        assert esc["ator"] == "Pytest Runner"
        assert esc["evidencias"] == {"ator": "Pytest Runner", "origem_acao": "painel"}
        assert esc["mensagem_id"] is None
        assert esc["processamento_id"] is None
        assert esc["evento_id"] is not None
        assert esc["avaliacao"] is None

        detalhe = client.get(f"/api/atendimentos/{atendimento_id}").json()
        assert [e["id"] for e in detalhe["escalonamentos"]] == [esc["id"]]

        assert client.get("/api/atendimentos/999999999/escalonamentos").status_code == 404
    finally:
        _limpar(db_session, telefone)


def test_avaliacao_grava_altera_e_desfaz(client, db_session):
    telefone = "+5511999964010"
    try:
        atendimento_id = _atendimento_escalado_manual(client, db_session, telefone)
        esc_id = client.get(f"/api/atendimentos/{atendimento_id}/escalonamentos").json()["escalonamentos"][0]["id"]
        url = f"/api/escalonamentos/{esc_id}/avaliacao"

        r = client.patch(url, json={"avaliacao": "procedente", "comentario": "  cliente grande mesmo  "})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["avaliacao"] == "procedente"
        assert body["avaliacao_comentario"] == "cliente grande mesmo"
        assert body["avaliado_por"] == "Pytest Runner"
        assert body["avaliado_em"] is not None

        # Vale a última.
        r = client.patch(url, json={"avaliacao": "indevido", "comentario": None})
        assert r.status_code == 200
        assert r.json()["avaliacao"] == "indevido"
        assert r.json()["avaliacao_comentario"] is None

        # null desfaz.
        r = client.patch(url, json={"avaliacao": None})
        assert r.status_code == 200
        body = r.json()
        assert body["avaliacao"] is None
        assert body["avaliado_por"] is None
        assert body["avaliado_em"] is None

        db_session.expire_all()
        assert db_session.get(Escalonamento, esc_id).avaliacao is None
    finally:
        _limpar(db_session, telefone)


def test_avaliacao_invalida_ou_ausente_retorna_422_e_id_inexistente_404(client, db_session):
    telefone = "+5511999964011"
    try:
        atendimento_id = _atendimento_escalado_manual(client, db_session, telefone)
        esc_id = client.get(f"/api/atendimentos/{atendimento_id}/escalonamentos").json()["escalonamentos"][0]["id"]
        url = f"/api/escalonamentos/{esc_id}/avaliacao"

        assert client.patch(url, json={"avaliacao": "talvez"}).status_code == 422
        assert client.patch(url, json={"comentario": "sem o campo avaliacao"}).status_code == 422
        r = client.patch("/api/escalonamentos/999999999/avaliacao", json={"avaliacao": "indevido"})
        assert r.status_code == 404

        db_session.expire_all()
        assert db_session.get(Escalonamento, esc_id).avaliacao is None
    finally:
        _limpar(db_session, telefone)


def test_endpoints_de_escalonamento_exigem_login(client, db_session):
    import main

    telefone = "+5511999964012"
    try:
        atendimento_id = _atendimento_escalado_manual(client, db_session, telefone)
        esc_id = client.get(f"/api/atendimentos/{atendimento_id}/escalonamentos").json()["escalonamentos"][0]["id"]

        with TestClient(main.app) as anonimo:
            assert anonimo.get(f"/api/atendimentos/{atendimento_id}/escalonamentos").status_code == 401
            r = anonimo.patch(f"/api/escalonamentos/{esc_id}/avaliacao", json={"avaliacao": "indevido"})
            assert r.status_code == 401

        db_session.expire_all()
        assert db_session.get(Escalonamento, esc_id).avaliacao is None
    finally:
        _limpar(db_session, telefone)
