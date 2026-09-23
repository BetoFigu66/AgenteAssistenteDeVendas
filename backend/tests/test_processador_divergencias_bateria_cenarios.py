"""Regressões das duas divergências vistas na 1ª bateria de 16 cenários do
`testador_conversas` (set/2026).

Estratégia: classificação REAL (só regras, sem LLM — `ProcessadorMensagem()` sem
provider) em vez de `ResultadoClassificacao` fabricado. Injetar intenção já pronta foi
exatamente o que escondeu o bug corrigido em `175ab15`, e no cenário
`preco_direto_sem_identificacao` a intenção fabricada esconderia o ponto central: o tipo
de produto é extraído CERTO ("catraca") e mesmo assim a pergunta que sai fala de relógio
de ponto.

Divergência A (`preco_direto_sem_identificacao`): documentada, não corrigida — a correção
mexe no texto que vai para o cliente em 10 tipos de produto e no limite de repetição de
uma pergunta obrigatória, as duas coisas decisão de produto. Os testes ficam como
`xfail(strict=True)`, então viram falha no dia em que alguém corrigir e esquecer de
remover o marcador.

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
    telefone = "5511999977101"
    try:
        _conversar(processador, db_session, telefone, ["bom dia", "tudo bem?"])

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
    telefone = "5511999977102"
    mensagens = ["bom dia", "tudo bem?", "é o seguinte", "preciso de um controle de acesso", "pra uma academia"]
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


@pytest.mark.xfail(
    strict=True,
    reason="Divergência A: MensagemId.PEDIR_MODELO tem texto fixo de relógio de ponto, mas "
    "CAMPO_MODELO vale para 10 tipos de produto. Corrigir exige texto por tipo de produto "
    "(decisão de produto).",
)
def test_pergunta_de_modelo_para_catraca_nao_fala_de_relogio(db_session, processador):
    telefone = "5511999977103"
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
    telefone = "5511999977104"
    mensagens = ["quanto custa a catraca de balcão?", "me passa só um valor aproximado", "é muito caro isso?"]
    try:
        resultados = _conversar(processador, db_session, telefone, mensagens)
        assert resultados[1].resposta != resultados[2].resposta
    finally:
        _limpar(db_session, telefone)
