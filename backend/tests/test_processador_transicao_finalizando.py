"""Testes da transição Esclarecendo → Finalizando (Fase E — E1/E2/E3).

Injeta um `ResultadoClassificacao` já pronto (mesma estratégia de
`test_processador_categoria3_pre_identificacao.py`) — não depende do classificador
(regra ou LLM) acertar a intenção, só verifica o comportamento de `_decidir_resposta`
e `_iniciar_ou_continuar_finalizando` dado um `PEDIR_ORCAMENTO` já classificado.
"""

import asyncio

import pytest
from database import Database
from models import Contato, FaseAtendimento, ItemAtendimento, Modelo, Produto
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao
from services.processador import ProcessadorMensagem
from services.respostas import MensagemId


def _produto_relogio_ponto(db_session) -> Produto:
    """Get-or-create — tabela de catálogo ainda está vazia neste ambiente (Fase F futura)."""
    produto = db_session.query(Produto).filter_by(descricao="Relógio de Ponto (teste)").first()
    if produto is None:
        produto = Produto(descricao="Relógio de Ponto (teste)", ativo=True)
        db_session.add(produto)
        db_session.commit()
    return produto


def _modelo_relogio_ponto_teste(db_session, produto: Produto) -> Modelo:
    modelo = db_session.query(Modelo).filter_by(codigo="TESTE-REP-001").first()
    if modelo is None:
        modelo = Modelo(
            produto_id=produto.id,
            codigo="TESTE-REP-001",
            descricao="Modelo de teste (Fase E)",
            preco_tabela=0,
            ativo=True,
        )
        db_session.add(modelo)
        db_session.commit()
    return modelo


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


def test_novo_pedir_orcamento_transita_fase_e_pergunta_modelo(db_session, processador):
    """E1 + E3: telefone novo pedindo orçamento com produto já mencionado vira Finalizando
    e a próxima pergunta é o modelo (nada mais foi capturado ainda)."""
    telefone = "5511999980001"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"])

    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento de relógio de ponto",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta.template_usado == "SAUDACAO_NOVO_CONTATO+INICIAR_FINALIZANDO+PEDIR_MODELO"

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
    finally:
        _limpar(db_session, telefone)


def test_novo_pedir_orcamento_sem_produto_ainda_pede_tipo(db_session, processador):
    """E3: sem tipo de produto identificado, cai no fallback PEDIR_TIPO_PRODUTO (sem
    INICIAR_FINALIZANDO) — mas a fase já muda para Finalizando (E1)."""
    telefone = "5511999980002"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(Intencao.PEDIR_ORCAMENTO)

    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta.template_usado == "SAUDACAO_NOVO_CONTATO+PEDIR_TIPO_PRODUTO"

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
    finally:
        _limpar(db_session, telefone)


def test_composta_orcamento_com_software_junto_captura_no_mesmo_turno(db_session, processador):
    """E3: 'quero orçamento, já uso o Domínio' captura software no mesmo turno da transição;
    a próxima pergunta é modelo (ainda pendente)."""
    telefone = "5511999980003"
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_class = _resultado(
        Intencao.PEDIR_ORCAMENTO,
        tipos_produto=["relogio_ponto"],
        software_ponto="Domínio",
    )

    try:
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento de relógio de ponto, já uso o Domínio",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        assert resposta.template_usado == "SAUDACAO_NOVO_CONTATO+INICIAR_FINALIZANDO+PEDIR_MODELO"

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        chaves_valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert chaves_valores.get("software_controle_ponto") == "Domínio"
    finally:
        _limpar(db_session, telefone)


def test_transicao_e_idempotente_segunda_mensagem_ja_finalizando(db_session, processador):
    """E1: se o atendimento já está em Finalizando, uma nova PEDIR_ORCAMENTO não deveria
    re-disparar a transição nem quebrar — só decide a próxima pergunta de novo."""
    telefone = "5511999980004"
    identificacao_1 = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado_1 = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"])

    try:
        asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento de relógio de ponto",
                identificacao=identificacao_1,
                resultado_class=resultado_1,
            )
        )
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.fase == FaseAtendimento.FINALIZANDO

        # Simula que o modelo já foi resolvido (Fase F faria isso) para variar a próxima pergunta.
        produto = _produto_relogio_ponto(db_session)
        modelo = _modelo_relogio_ponto_teste(db_session, produto)
        item = ItemAtendimento(
            atendimento_id=atendimento.id,
            produto_id=produto.id,
            modelo_id=modelo.id,
            quantidade=1,
        )
        db_session.add(item)
        db_session.commit()

        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_2 = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"])
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento",
                identificacao=identificacao_2,
                resultado_class=resultado_2,
            )
        )
        # Fase F: já em Finalizando, a coleta ativa (F1) responde direto — sem repetir o
        # INICIAR_FINALIZANDO a cada turno; modelo já resolvido → pergunta software.
        assert resposta_2.template_usado == "PEDIR_SOFTWARE_PONTO"
    finally:
        _limpar(db_session, telefone)


def test_mensagem_id_pedir_faixa_funcionarios_renderiza_com_produto():
    """Confirma que o template de faixa renderiza com o nome do produto no contexto."""
    from services.respostas.catalogo import renderizar_mensagem

    texto, codigo = renderizar_mensagem(
        MensagemId.PEDIR_FAIXA_FUNCIONARIOS, {"produto": "o relógio de ponto"}
    )
    assert codigo == "PEDIR_FAIXA_FUNCIONARIOS"
    assert "pessoas" in texto
    assert "Qual a faixa de pessoas que vão usar o relógio de ponto?" == texto
