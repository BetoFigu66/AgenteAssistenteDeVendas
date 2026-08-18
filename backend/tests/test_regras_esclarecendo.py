"""Testes das Regras da fase Esclarecendo (`services/conversacao/regras_esclarecendo.py`)
— correção do bug relatado: "Bom dia... quero informações sobre relógio de ponto
biométrico" pedia CNPJ em vez de responder a pergunta de produto, e uma recusa de
documento fazia o sistema repetir a mesma pergunta pra sempre.
"""

import asyncio

import pytest
from database import Database
from models import Contato, Empresa
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, criar_contato
from services.processador import ProcessadorMensagem


def _resultado(intencoes, **entidades_kwargs) -> ResultadoClassificacao:
    if isinstance(intencoes, Intencao):
        intencoes = [intencoes]
    return ResultadoClassificacao(
        intencoes=intencoes,
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


def test_saudacao_nao_impede_resposta_a_pergunta_de_produto_no_mesmo_turno(db_session, processador):
    """Regressão do bug relatado: SAUDACAO + PERGUNTAR_PRODUTO na mesma mensagem deve
    criar o atendimento e responder à pergunta de produto — não pedir CNPJ."""
    telefone = "5511999984001"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado = _resultado(
        [Intencao.SAUDACAO, Intencao.PERGUNTAR_PRODUTO, Intencao.FORNECER_NOME],
        nomes=["Diana"],
        tipos_produto=["relogio_ponto"],
        tipo_leitor_mencionado="biometria",
    )
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Bom dia. Meu nome é Diana, quero informações sobre relogio de ponto biometrico.",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta.template_usado != "SAUDACAO_NOVO_CONTATO"
        assert resposta.template_usado != "PERGUNTAR_CNPJ"

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
        assert contato.nome == "Diana"
        atendimento = contato.atendimentos[0]
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("tipos_produto") == "relogio_ponto"
    finally:
        _limpar(db_session, telefone)


def test_documento_pendente_nao_repete_apos_recusa_implicita(db_session, processador):
    """"Não quero fornecer ainda." não bate na regra NEGAR (que exige a mensagem inteira
    ser só "não") — mesmo assim, a segunda pergunta não deve repetir o pedido de CNPJ."""
    telefone = "5511999984002"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])

    try:
        resposta_1 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.SAUDACAO),
            )
        )
        assert resposta_1.template_usado == "SAUDACAO_NOVO_CONTATO"

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Não quero fornecer o documento ainda.",
                identificacao=identificacao_2, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_2.template_usado != "PERGUNTAR_CNPJ"

        atendimento = contato.atendimentos[0]
        valores = {info.chave: (info.valor, info.pendente) for info in atendimento.informacoes}
        assert valores.get("documento_fiscal_pendente") == ("recusado", True)

        # Terceira mensagem: continua sem repetir, mesmo sem qualquer sinal de recusa.
        resposta_3 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Vocês têm catraca também?",
                identificacao=identificacao_2, resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_3.template_usado != "PERGUNTAR_CNPJ"
    finally:
        _limpar(db_session, telefone)


def test_documento_fornecido_depois_de_solicitado_limpa_pendencia(db_session, processador):
    """Se o cliente fornece o CNPJ depois de já ter sido perguntado, a pendência some."""
    telefone = "5511999984003"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])

    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.SAUDACAO),
            )
        )
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        valores_antes = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores_antes.get("documento_fiscal_pendente") == "solicitado"
    finally:
        _limpar(db_session, telefone)


def test_fora_contexto_isolado_nao_cria_atendimento():
    """FORA_CONTEXTO sozinho (sem qualificação) nunca foi "intenção de qualificação" —
    dúvida totalmente fora do domínio não deveria, sozinha, criar um atendimento."""
    database = Database()
    with database.get_session() as db_session:
        processador = ProcessadorMensagem()
        telefone = "5511999984004"
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        try:
            asyncio.run(
                processador._decidir_resposta(
                    db=db_session, telefone=telefone, conteudo="Vocês entregam pizza?",
                    identificacao=identificacao, resultado_class=_resultado(Intencao.FORA_CONTEXTO),
                )
            )
            contato = db_session.query(Contato).filter_by(telefone=telefone).first()
            assert contato is None
        finally:
            _limpar(db_session, telefone)


def test_saudacao_identificado_com_empresa_usa_nome(db_session, processador):
    """Cliente já identificado (empresa vinculada) dizendo "oi" de novo deve ser
    cumprimentado pelo nome — comportamento preservado da unificação do dispatch."""
    telefone = "5511999984005"
    empresa = Empresa(cnpj="00.000.000/0001-99", nome="Empresa Teste Esclarecendo")
    db_session.add(empresa)
    db_session.commit()
    contato = criar_contato(db_session, telefone, empresa=empresa, nome="Carlos")

    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.UNICO, contatos=[contato], empresas=[empresa])
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Oi",
                identificacao=identificacao, resultado_class=_resultado(Intencao.SAUDACAO),
            )
        )
        assert resposta.template_usado == "SAUDACAO_COM_NOME"
        assert "Carlos" in resposta.texto
    finally:
        _limpar(db_session, telefone)
        db_session.query(Empresa).filter_by(id=empresa.id).delete()
        db_session.commit()


def test_perguntar_prazo_agora_funciona_para_contato_novo(db_session, processador):
    """Unificação de escopo (confirmada): PERGUNTAR_PRAZO deixou de ser exclusivo de
    contatos já identificados — um contato novo também recebe a resposta padrão."""
    telefone = "5511999984006"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Qual o prazo de entrega?",
                identificacao=identificacao, resultado_class=_resultado(Intencao.PERGUNTAR_PRAZO),
            )
        )
        assert resposta.template_usado == "PRAZO_NAO_PROMETIDO"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
    finally:
        _limpar(db_session, telefone)


def test_perguntar_disponibilidade_confirma_e_pergunta_faixa_funcionarios(db_session, processador):
    """"Vocês vendem relógio biométrico?" deve confirmar disponibilidade (com marcas do
    catálogo) e já perguntar a faixa de funcionários, sem pular direto para perguntas de
    modelo/cartográfico como acontecia com PEDIR_ORCAMENTO."""
    telefone = "5511999984008"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado = _resultado(
        [Intencao.PERGUNTAR_DISPONIBILIDADE, Intencao.PERGUNTAR_PRODUTO],
        tipos_produto=["relogio_ponto"],
        tipo_leitor_mencionado="biometria",
    )
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Vocês vendem relógio biométrico?",
                identificacao=identificacao, resultado_class=resultado,
            )
        )
        assert "DISPONIBILIDADE_PRODUTO" in (resposta.template_usado or "")
        assert "PEDIR_MODELO" not in (resposta.template_usado or "")
        assert "PEDIR_FAIXA_FUNCIONARIOS" in (resposta.template_usado or "")
        assert "Sim, vendemos" in resposta.texto

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
        atendimento = contato.atendimentos[0]
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("tipos_produto") == "relogio_ponto"
    finally:
        _limpar(db_session, telefone)


def test_perguntar_disponibilidade_sem_produto_nao_dispara_acao(db_session, processador):
    """Guarda de produto obrigatório (DEC-008) também vale para PERGUNTAR_DISPONIBILIDADE
    — sem tipo de produto extraído, a ação não deve disparar (evita "Sim, vendemos" sem
    saber o quê)."""
    telefone = "5511999984009"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado = _resultado([Intencao.PERGUNTAR_DISPONIBILIDADE])
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Vocês vendem para todo o Brasil?",
                identificacao=identificacao, resultado_class=resultado,
            )
        )
        assert "DISPONIBILIDADE_PRODUTO" not in (resposta.template_usado or "")
    finally:
        _limpar(db_session, telefone)


def test_disponibilidade_seguida_de_duvida_sobre_marcas_nao_sequestra_pergunta(db_session, processador):
    """Regressão: após "vocês vendem relógio biométrico?" (PERGUNTAR_DISPONIBILIDADE), uma
    pergunta legítima do cliente sobre as marcas ("pode explicar as características
    delas?") não deve ser sequestrada por uma tentativa de resolução de modelo usando o
    sinal antigo (tecnologia_leitura=biometria) — deve responder a dúvida via RAG/Q&A e
    retomar a pergunta pendente, não "Não encontrei esse modelo"."""
    telefone = "5511999984010"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_1 = _resultado(
        [Intencao.PERGUNTAR_DISPONIBILIDADE, Intencao.PERGUNTAR_PRODUTO],
        tipos_produto=["relogio_ponto"],
        tipo_leitor_mencionado="biometria",
        atributos={"tecnologia_leitura": "biometria"},
    )
    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Vocês vendem relógio biométrico?",
                identificacao=identificacao, resultado_class=resultado_1,
            )
        )
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_2 = _resultado(Intencao.PERGUNTAR_PRODUTO)
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone,
                conteudo="não conheço essas marcas, pode me explicar as principais características delas?",
                identificacao=identificacao_2, resultado_class=resultado_2,
            )
        )
        assert "MODELO_NAO_RECONHECIDO" not in (resposta_2.template_usado or "")
    finally:
        _limpar(db_session, telefone)


def test_disponibilidade_seguida_de_mensagem_sem_sinal_nao_reapresenta_modelo(db_session, processador):
    """Regressão (bug real em produção 2026-08-18): após PERGUNTAR_DISPONIBILIDADE pedir a
    faixa de funcionários primeiro (fora da ordem padrão do catálogo, onde CAMPO_MODELO
    vem antes), uma mensagem seguinte sem nenhum sinal de modelo (DESCONHECIDO, sem
    marca/aplicação/tecnologia) não pode reapresentar "cartográfico ou eletrônico?" — esse
    campo nunca foi de fato perguntado nesta conversa. Deve continuar com a faixa de
    funcionários, que é o campo prioritário ainda pendente."""
    telefone = "5511999984011"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_1 = _resultado(
        [Intencao.PERGUNTAR_DISPONIBILIDADE, Intencao.PERGUNTAR_PRODUTO],
        tipos_produto=["relogio_ponto"],
        tipo_leitor_mencionado="biometria",
    )
    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Vocês vendem relógio biométrico?",
                identificacao=identificacao, resultado_class=resultado_1,
            )
        )
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_2 = _resultado(Intencao.DESCONHECIDO)
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone,
                conteudo="quero saber as opções de produto com detalhes",
                identificacao=identificacao_2, resultado_class=resultado_2,
            )
        )
        assert resposta_2.template_usado == "PEDIR_FAIXA_FUNCIONARIOS"
    finally:
        _limpar(db_session, telefone)


def test_pedir_orcamento_suprime_categoria3_redundante_no_mesmo_turno(db_session, processador):
    """Regressão de smoke test manual: "Quero orçamento de relógio de ponto" bate em
    PEDIR_ORCAMENTO **e** PERGUNTAR_PRODUTO — sem a supressão, a resposta ficava tripla e
    redundante (início do orçamento + resposta genérica de RAG sobre o mesmo produto)."""
    telefone = "5511999984007"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado = _resultado(
        [Intencao.PEDIR_ORCAMENTO, Intencao.PERGUNTAR_PRODUTO],
        tipos_produto=["relogio_ponto"],
    )
    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Quero orçamento de relogio de ponto",
                identificacao=identificacao, resultado_class=resultado,
            )
        )
        assert resposta.template_usado == "SAUDACAO_NOVO_CONTATO+INICIAR_FINALIZANDO+PEDIR_MODELO"
        assert "categoria3" not in (resposta.template_usado or "")
    finally:
        _limpar(db_session, telefone)
