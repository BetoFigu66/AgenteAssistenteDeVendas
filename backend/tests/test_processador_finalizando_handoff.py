"""Testes do handoff Finalizando → Em orçamentação (Fase G — G1/G2/G3).

Mesma estratégia das demais suítes de `_decidir_resposta`: injeta um
`ResultadoClassificacao` já pronto e chama via `asyncio.run`, sem depender do
classificador (regra ou LLM) acertar a intenção.
"""

import asyncio

import pytest
from database import Database
from models import Contato, FaseAtendimento, ItemAtendimento, Modelo, ModoOperacao, Produto
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


def _atendimento_pronto_para_resumo(db_session, processador, telefone):
    """Leva um contato anônimo até Finalizando com modelo resolvido e software=Domínio
    (faixa não se aplica) — tudo capturado, pronto para o resumo (F4) e a confirmação (G)."""
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"], software_ponto="Domínio")
    asyncio.run(
        processador._decidir_resposta(
            db=db_session,
            telefone=telefone,
            conteudo="Quero orçamento de relogio de ponto, ja uso o Dominio",
            identificacao=identificacao,
            resultado_class=resultado,
        )
    )
    contato = db_session.query(Contato).filter_by(telefone=telefone).first()
    atendimento = contato.atendimentos[0]

    produto = db_session.query(Produto).filter_by(descricao="Relógio de Ponto (teste G)").first()
    if produto is None:
        produto = Produto(descricao="Relógio de Ponto (teste G)", ativo=True)
        db_session.add(produto)
        db_session.commit()
    modelo = db_session.query(Modelo).filter_by(codigo="TESTE-REP-G001").first()
    if modelo is None:
        modelo = Modelo(
            produto_id=produto.id, codigo="TESTE-REP-G001", descricao="Modelo de teste (Fase G)",
            preco_tabela=0, ativo=True,
        )
        db_session.add(modelo)
        db_session.commit()
    db_session.add(
        ItemAtendimento(atendimento_id=atendimento.id, produto_id=produto.id, modelo_id=modelo.id, quantidade=1)
    )
    db_session.commit()
    return contato, atendimento


def test_g1_g2_g3_confirmar_resumo_transiciona_e_escala_humano(db_session, processador):
    """G1+G2+G3: depois do resumo (F4), o cliente confirmando transita fase para
    EM_ORCAMENTACAO, escala modo_operacao para HUMANO e envia a mensagem de handoff."""
    telefone = "5511999982001"
    try:
        contato, atendimento = _atendimento_pronto_para_resumo(db_session, processador, telefone)
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])

        # Primeira mensagem pós-tudo-capturado: gera o resumo (F4), ainda não confirma.
        resultado_resumo = _resultado(Intencao.DESCONHECIDO)
        resposta_resumo = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="ok",
                identificacao=identificacao, resultado_class=resultado_resumo,
            )
        )
        assert resposta_resumo.template_usado == "RESUMO_FINALIZANDO"
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
        assert atendimento.modo_operacao == ModoOperacao.AGENTE

        # Cliente confirma o resumo → G1/G2/G3.
        resultado_confirma = _resultado(Intencao.CONFIRMAR)
        resposta_confirma = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Sim, pode ser",
                identificacao=identificacao, resultado_class=resultado_confirma,
            )
        )
        assert resposta_confirma.template_usado == "ORCAMENTO_ENCAMINHADO"
        assert "orçamento" in resposta_confirma.texto.lower()
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.EM_ORCAMENTACAO
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
    finally:
        _limpar(db_session, telefone)


def test_g1_primeira_mensagem_apos_tudo_capturado_nao_conclui_mesmo_se_confirmar(db_session, processador):
    """Regressão descoberta em smoke test manual: um "ok"/"sim" solto pode ser
    classificado como CONFIRMAR mesmo sendo a *primeira* mensagem a chegar depois de tudo
    capturado — nesse caso o cliente nunca viu o resumo, então não é uma confirmação dele.
    Só um CONFIRMAR posterior a um resumo já apresentado (G1) deve concluir o handoff."""
    telefone = "5511999982005"
    try:
        contato, atendimento = _atendimento_pronto_para_resumo(db_session, processador, telefone)
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])

        resultado = _resultado(Intencao.CONFIRMAR)
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="ok",
                identificacao=identificacao, resultado_class=resultado,
            )
        )
        assert resposta.template_usado == "RESUMO_FINALIZANDO"
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
        assert atendimento.modo_operacao == ModoOperacao.AGENTE

        # Agora sim, um CONFIRMAR posterior ao resumo já apresentado conclui o handoff.
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="ok",
                identificacao=identificacao, resultado_class=_resultado(Intencao.CONFIRMAR),
            )
        )
        assert resposta_2.template_usado == "ORCAMENTO_ENCAMINHADO"
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.EM_ORCAMENTACAO
    finally:
        _limpar(db_session, telefone)


def test_g_mensagem_nao_confirmatoria_repete_resumo_sem_transicionar(db_session, processador):
    """G1 (negativo): uma mensagem que não é CONFIRMAR não deve disparar o handoff — só
    repete o resumo, mantendo fase/modo inalterados."""
    telefone = "5511999982002"
    try:
        contato, atendimento = _atendimento_pronto_para_resumo(db_session, processador, telefone)
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])

        resultado = _resultado(Intencao.DESCONHECIDO)
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="deixa eu pensar",
                identificacao=identificacao, resultado_class=resultado,
            )
        )
        assert resposta.template_usado == "RESUMO_FINALIZANDO"
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
    finally:
        _limpar(db_session, telefone)


def test_g_confirmar_sem_tipo_produto_conhecido_nao_conclui(db_session, processador):
    """Regressão: se o tipo de produto ainda não foi identificado, `campos_pendentes()`
    também retorna vazio — mas isso não é "tudo capturado". Um "sim" nesse estágio não
    pode disparar o handoff (G); deve reapresentar PEDIR_TIPO_PRODUTO."""
    telefone = "5511999982003"
    try:
        identificacao_1 = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        resultado_1 = _resultado(Intencao.PEDIR_ORCAMENTO)  # sem tipos_produto
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Quero orçamento",
                identificacao=identificacao_1, resultado_class=resultado_1,
            )
        )
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.fase == FaseAtendimento.FINALIZANDO

        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_2 = _resultado(Intencao.CONFIRMAR)
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="sim",
                identificacao=identificacao_2, resultado_class=resultado_2,
            )
        )
        assert resposta_2.template_usado == "PEDIR_TIPO_PRODUTO"
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
    finally:
        _limpar(db_session, telefone)


def test_tipo_produto_pode_ser_informado_apos_ja_estar_em_finalizando(db_session, processador):
    """Regressão: o guard que trava `tipos_produto` contra reescrita (Fase F) não pode
    bloquear a primeira gravação legítima quando o produto só é informado numa mensagem
    posterior — ex.: bot pergunta PEDIR_TIPO_PRODUTO (fase já é Finalizando) e só então o
    cliente responde "relógio de ponto"."""
    telefone = "5511999982004"
    try:
        identificacao_1 = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        resultado_1 = _resultado(Intencao.PEDIR_ORCAMENTO)
        resposta_1 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Quero orçamento",
                identificacao=identificacao_1, resultado_class=resultado_1,
            )
        )
        assert resposta_1.template_usado == "SAUDACAO_NOVO_CONTATO+PEDIR_TIPO_PRODUTO"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.fase == FaseAtendimento.FINALIZANDO

        identificacao_2 = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_2 = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"])
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="Relógio de ponto",
                identificacao=identificacao_2, resultado_class=resultado_2,
            )
        )
        assert resposta_2.template_usado == "PEDIR_MODELO"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("tipos_produto") == "relogio_ponto"
    finally:
        _limpar(db_session, telefone)
