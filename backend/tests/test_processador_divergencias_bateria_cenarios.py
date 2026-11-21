"""Regressões das duas divergências vistas na 1ª bateria de 16 cenários do
`testador_conversas` (set/2026).

Estratégia: classificação REAL (só regras, sem LLM — `ProcessadorMensagem()` sem
provider) em vez de `ResultadoClassificacao` fabricado. Injetar intenção já pronta foi
exatamente o que escondeu o bug corrigido em `175ab15`, e no cenário
`preco_direto_sem_identificacao` a intenção fabricada esconderia o ponto central: o tipo
de produto é extraído CERTO ("catraca") e mesmo assim a pergunta que sai fala de relógio
de ponto.

Divergência A (`preco_direto_sem_identificacao`): o texto da pergunta do modelo por tipo
de produto foi corrigido em 02/11 (`perguntas_produto`); o limite de repetição de uma
pergunta obrigatória segue documentado e não corrigido (decisão de produto), como
`xfail(strict=True)`, que vira falha no dia em que alguém corrigir e esquecer de remover
o marcador.

Divergência B (`mensagens_quebradas_em_rajada`): corrigida. O rótulo de auditoria da 1ª
ocorrência de confiança baixa (REQ-004.9) não cabia em
`ProcessamentoMensagem.resultado_fallback` (`String(30)`), o INSERT estourava, e
`processar()` inteiro levantava — era isso que o webhook traduzia em "Desculpe, tive um
problema ao processar sua mensagem".
"""

import asyncio

import pytest
from database import Database
from models import Atendimento, Contato, ModoOperacao, ProcessamentoMensagem
from services.classificador import classificar
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.processador import ROTULOS_FALLBACK, ProcessadorMensagem

from tests.apoio_perguntas import pergunta_modelo


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    """Sem LLM de propósito: o classificador vira determinístico (só regras)."""
    return ProcessadorMensagem()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _conversar(processador, db_session, telefone, mensagens):
    """Roda a sequência inteira por `processar()` e devolve os resultados na ordem."""
    return [
        asyncio.run(processador.processar(db=db_session, telefone=telefone, conteudo=m)) for m in mensagens
    ]


def _ultimo_processamento(db_session, telefone):
    contato = db_session.query(Contato).filter_by(telefone=telefone).first()
    assert contato is not None
    return (
        db_session.query(ProcessamentoMensagem)
        .filter_by(contato_id_identificado=contato.id)
        .order_by(ProcessamentoMensagem.id.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Divergência B — exceção engolida no cérebro
# ---------------------------------------------------------------------------


def test_rotulos_de_resultado_fallback_cabem_na_coluna():
    """Guarda contra a classe do bug: qualquer rótulo novo precisa caber na coluna,
    senão o INSERT de auditoria derruba o turno inteiro do cliente.

    Os dois lados vêm do código de produção de propósito: os rótulos de
    `ROTULOS_FALLBACK` (não uma tupla copiada à mão, que deixaria rótulo novo de fora e
    continuaria verde) e o tamanho declarado no modelo (não um 30 escrito aqui, que
    mentiria no dia em que a coluna mudar).
    """
    limite = ProcessamentoMensagem.__table__.c.resultado_fallback.type.length
    assert ROTULOS_FALLBACK, "a constante ficou vazia — o teste deixaria de verificar qualquer coisa"
    for rotulo in sorted(ROTULOS_FALLBACK):
        assert len(rotulo) <= limite, f"{rotulo!r} não cabe em String({limite})"


def test_primeira_confianca_baixa_persiste_auditoria_sem_estourar(db_session, processador):
    """Sem o fix, este turno levanta `DataError` (value too long for character
    varying(30)) e o webhook responde com o fallback de erro."""
    telefone = "+5511999977101"
    try:
        # "tudo bem?" era o exemplo original, mas virou cortesia (SAUDACAO) em 08/10.
        _conversar(processador, db_session, telefone, ["bom dia", "pois é"])

        proc = _ultimo_processamento(db_session, telefone)
        assert proc.fallback_req003 is True
        assert proc.resultado_fallback == "nao_entendi_aguardando_2a"
        assert proc.template_usado == "NAO_ENTENDI"
    finally:
        _limpar(db_session, telefone)


def test_rajada_nao_cai_no_fallback_de_erro_e_escala_na_segunda_baixa(db_session, processador):
    """Cenário `mensagens_quebradas_em_rajada` inteiro.

    Além de não levantar, verifica o efeito colateral que o estouro escondia: como a 1ª
    ocorrência de confiança baixa era revertida junto com a transação, o contador do
    REQ-004.9 nunca persistia e o escalonamento na 2ª ocorrência nunca acontecia.
    """
    telefone = "+5511999977102"
    # "pois é" no lugar do "tudo bem?" do cenário, que virou cortesia (SAUDACAO) em 08/10.
    mensagens = ["bom dia", "pois é", "é o seguinte", "preciso de um controle de acesso", "pra uma academia"]
    try:
        resultados = _conversar(processador, db_session, telefone, mensagens)

        assert all("problema ao processar" not in (r.resposta or "") for r in resultados)
        assert "assistente da Inforrel" in resultados[0].resposta
        assert "não entendi" in resultados[1].resposta.lower()
        assert "transferir" in resultados[2].resposta.lower()

        atendimento = (
            db_session.query(Atendimento)
            .join(Contato, Atendimento.contato_id == Contato.id)
            .filter(Contato.telefone == telefone)
            .order_by(Atendimento.id.desc())
            .first()
        )
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
    finally:
        _limpar(db_session, telefone)


# ---------------------------------------------------------------------------
# Divergência A — pergunta de relógio para quem perguntou de catraca
# ---------------------------------------------------------------------------


def test_classificador_extrai_catraca_da_pergunta_de_preco():
    """Descarta a suspeita "o tipo de produto foi identificado errado": a extração
    acerta, o problema está no texto do template escolhido depois."""
    resultado = asyncio.run(classificar("quanto custa a catraca de balcão?"))
    assert resultado.entidades.tipos_produto == ["catraca"]


def test_pergunta_de_modelo_para_catraca_nao_fala_de_relogio(db_session, processador):
    """Divergência A, primeira metade: corrigida em 02/11 com o texto por produto
    (`perguntas_produto`) e um texto padrão que não supõe relógio."""
    telefone = "+5511999977103"
    try:
        resultados = _conversar(processador, db_session, telefone, ["quanto custa a catraca de balcão?"])
        assert "relógio" not in resultados[0].resposta.lower()
    finally:
        _limpar(db_session, telefone)


@pytest.mark.xfail(
    strict=True,
    reason="Divergência A: nada limita quantas vezes uma pergunta obrigatória sem resposta é "
    "reapresentada. `_MODELO_MAX_TENTATIVAS` só conta turnos com sinal de modelo, e um turno "
    "sem sinal nenhum não conta. Quantas repetições tolerar, e o que fazer depois, é decisão "
    "de produto.",
)
def test_pergunta_de_modelo_nao_se_repete_indefinidamente(db_session, processador):
    telefone = "+5511999977104"
    mensagens = ["quanto custa a catraca de balcão?", "me passa só um valor aproximado", "é muito caro isso?"]
    try:
        resultados = _conversar(processador, db_session, telefone, mensagens)
        assert resultados[1].resposta != resultados[2].resposta
    finally:
        _limpar(db_session, telefone)


def test_cortesia_depois_da_saudacao_retoma_o_pedido_de_documento(db_session, processador):
    """Bateria de 08/10 (`mensagens_quebradas_em_rajada`, `cortesia_isolada_sem_conteudo`):
    "tudo bem?" logo depois do pedido de CNPJ/CPF era tomado como recusa do documento e
    respondia NAO_ENTENDI. Agora retoma a pergunta, e o documento continua pedido."""
    telefone = "+5511999977105"
    try:
        resultados = _conversar(processador, db_session, telefone, ["bom dia", "tudo bem?", "pois é"])

        assert resultados[1].resposta.startswith("Voltando à minha pergunta:")
        assert "CNPJ" in resultados[1].resposta
        # O pedido segue valendo: a mensagem sem documento seguinte é que conta como recusa.
        assert "não entendi" in resultados[2].resposta.lower()
    finally:
        _limpar(db_session, telefone)


def test_compatibilidade_vai_para_validacao_tecnica(db_session, processador):
    """Bateria de 08/10 (`compatibilidade_software_terceiro`): a pergunta caía na RAG
    ("não tenho certeza...") e a insistência "funciona ou não funciona?" virava reclamação.
    O template COMPATIBILIDADE_SISTEMA existia, mas nada o usava."""
    telefone = "+5511999977106"
    mensagens = ["vocês têm relógio de ponto que funciona com o Domínio?", "então funciona ou não funciona?"]
    try:
        resultados = _conversar(processador, db_session, telefone, mensagens)
        for r in resultados:
            assert "fornecedor do seu software" in r.resposta, r.resposta
    finally:
        _limpar(db_session, telefone)


def test_pergunta_de_prazo_no_meio_da_coleta_nao_e_ignorada(db_session, processador):
    """Bateria de 08/10 (`catraca_box_para_evento` T2): no Finalizando, "e entrega até o fim
    do mês?" repetia a pergunta pendente sem tocar no prazo. Agora responde sem compromisso
    e retoma a pergunta."""
    telefone = "+5511999977107"
    mensagens = ["quero orçamento de 2 relógios de ponto", "e entrega até o fim do mês?"]
    try:
        resultados = _conversar(processador, db_session, telefone, mensagens)
        resposta = resultados[1].resposta
        assert "prazo" in resposta.lower(), resposta
        assert "Voltando ao orçamento" in resposta, resposta
    finally:
        _limpar(db_session, telefone)


def test_tecnologia_dita_na_abertura_nao_e_perguntada_de_novo(db_session, processador):
    """Bateria de 08/10 (`preco_e_prazo_na_mesma_mensagem`, `leva_para_diretoria...`): a
    mensagem que abre a coleta já dizia "biométricos", e a 1ª pergunta era "cartográfico ou
    eletrônico?". `entrar` não tentava resolver o modelo."""
    telefone = "+5511999977108"
    try:
        mensagens = ["quero orçamento de 3 relógios de ponto biométricos"]
        resultados = _conversar(processador, db_session, telefone, mensagens)
        assert pergunta_modelo(db_session, "relogio_ponto") not in resultados[0].resposta, resultados[0].resposta
    finally:
        _limpar(db_session, telefone)


def test_so_o_nome_depois_da_saudacao_pede_so_o_documento(db_session, processador):
    """Bateria de 02/11 (`cumprimento_boa_tarde_espelhado`): a saudação pede nome e
    documento; "sou o Marcos" dava NAO_ENTENDI e marcava o documento como recusado."""
    telefone = "+5511999977109"
    try:
        resultados = _conversar(processador, db_session, telefone, ["boa tarde", "sou o Marcos"])
        resposta = resultados[1].resposta
        assert "não entendi" not in resposta.lower(), resposta
        assert "CNPJ" in resposta and "seu nome" not in resposta, resposta
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato.nome == "Marcos"
    finally:
        _limpar(db_session, telefone)


@pytest.mark.parametrize(
    ("texto", "tipos", "quantidades"),
    [
        ("preciso de 3 leitores faciais", ["leitor_facial"], [3]),
        ("quero 2 leitores biométricos", ["leitor_biometrico"], [2]),
        ("o modelo XPTO-9000", [], []),
    ],
)
def test_classificador_plural_de_leitor_e_codigo_de_modelo(texto, tipos, quantidades):
    """Bateria de 02/11: "leitores faciais" não abria a coleta (o casamento por palavra só
    aceita o "s" final) e o 9000 de "XPTO-9000" virava quantidade."""
    entidades = asyncio.run(classificar(texto)).entidades
    assert entidades.tipos_produto == tipos
    assert entidades.quantidades == quantidades
