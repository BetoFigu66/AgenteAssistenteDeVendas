"""Testes do roteamento D1 (REQ-002.1B): categoria 3 respondida via Q&A/RAG antes de pedir
documento, para telefones NOVO ou SEM_EMPRESA — independente do classificador (regra ou LLM)
ter reconhecido a intenção corretamente, o que importa aqui é: dado um `ResultadoClassificacao`
já pronto com intenção de categoria 3, o processador não deve mais cair no fallback genérico
`SAUDACAO_NOVO_CONTATO` / `PERGUNTAR_CNPJ`.

Usa a base real (não mocka RAG/QA) porque `_decidir_resposta` grava Contato/Atendimento de
verdade — cada teste usa um telefone único e limpa os dados criados ao final. Não há
pytest-asyncio instalado no projeto, então as corrotinas rodam via `asyncio.run(...)`.
"""

import asyncio

import pytest
from database import Database
from models import Contato
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


@pytest.mark.parametrize(
    "intencao,tipos_produto,telefone",
    [
        (Intencao.PERGUNTAR_PRODUTO, ["relogio_ponto"], "5511999960001"),
        (Intencao.PERGUNTAR_PRECO, ["relogio_ponto"], "5511999960002"),
        (Intencao.FORA_CONTEXTO, [], "5511999960003"),
    ],
)
def test_novo_categoria3_nao_cai_no_fallback_generico(db_session, processador, intencao, tipos_produto, telefone):
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(intencao, tipos_produto=tipos_produto)

    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="mensagem de teste",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta.template_usado != "SAUDACAO_NOVO_CONTATO"
    finally:
        _limpar(db_session, telefone)


def test_novo_pergunta_produto_registra_interesse_passivo_d2(db_session, processador):
    """D2: tipos_produto mencionado deve ser gravado em AtendimentoInfo mesmo em NOVO."""
    telefone = "5511999970001"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"])

    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Vocês têm relógio de ponto?",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
        atendimento = contato.atendimentos[0]
        assert atendimento.fase.value == "esclarecendo"
        chaves_valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert chaves_valores.get("tipos_produto") == "relogio_ponto"
    finally:
        _limpar(db_session, telefone)


def test_tecnologia_leitura_acumula_entre_mensagens_distintas(db_session, processador):
    """D6: se o cliente mencionar "biométrico" numa mensagem e "facial" em outra depois,
    `AtendimentoInfo` deve acumular os dois valores (união), não sobrescrever com o
    último — perder o sinal antigo travaria `_resolver_modelo`."""
    telefone = "5511999970004"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    try:
        resultado_1 = _resultado(
            Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"], atributos={"tecnologia_leitura": "biometria"},
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Quero relógio biométrico",
                identificacao=identificacao, resultado_class=resultado_1,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_2 = _resultado(
            Intencao.PERGUNTAR_PRODUTO, tipos_produto=["relogio_ponto"], atributos={"tecnologia_leitura": "facial"},
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="ou facial, qualquer um serve",
                identificacao=identificacao_2, resultado_class=resultado_2,
            )
        )
        db_session.commit()
        atendimento = contato.atendimentos[0]
        chaves_valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert set(chaves_valores.get("tecnologia_leitura", "").split(",")) == {"biometria", "facial"}
    finally:
        _limpar(db_session, telefone)


def test_novo_registra_software_leitor_e_faixa_passivamente_d3_d4(db_session, processador):
    """D3/D4: software, tipo de leitor e faixa de funcionários mencionados espontaneamente
    devem ser gravados em AtendimentoInfo (mesmas chaves do catálogo — CAMPO_SOFTWARE_PONTO,
    CAMPO_FAIXA_FUNCIONARIOS — e a chave provisória tipo_leitor_mencionado para a Fase F)."""
    telefone = "5511999970003"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(
        Intencao.PERGUNTAR_PRODUTO,
        tipos_produto=["relogio_ponto"],
        software_ponto="Domínio",
        tipo_leitor_mencionado="biometria",
        faixa_funcionarios=80,
    )

    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Preciso de relógio biométrico compatível com Domínio, uns 80 funcionários",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        chaves_valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert chaves_valores.get("software_controle_ponto") == "Domínio"
        assert chaves_valores.get("tipo_leitor_mencionado") == "biometria"
        assert chaves_valores.get("faixa_funcionarios") == "80"
    finally:
        _limpar(db_session, telefone)


def test_sem_empresa_fora_contexto_nao_pede_cnpj(db_session, processador):
    """D1: contato já existe (sem empresa) e pergunta fora de contexto não deve pedir CNPJ."""
    telefone = "5511999970002"
    contato = Contato(telefone=telefone, empresa_id=None)
    db_session.add(contato)
    db_session.commit()

    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
    resultado_class = _resultado(Intencao.FORA_CONTEXTO)

    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Vocês fazem entrega em outro estado?",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta.template_usado != "PERGUNTAR_CNPJ"
    finally:
        _limpar(db_session, telefone)
