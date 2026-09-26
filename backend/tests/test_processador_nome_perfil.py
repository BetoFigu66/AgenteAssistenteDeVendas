"""Uso do nome de perfil do WhatsApp (`ProfileName`) em `ProcessadorMensagem.processar()`.

Decisão do Beto (26/09): o nome do perfil não é gravado sem o cliente confirmar. O bot
pergunta "Olá, <nome>! Posso te chamar assim ou seu nome é outro?" no lugar do pedido de
nome, e a resposta decide (`services/conversacao/confirmacao_nome_perfil.py`).

Ponta a ponta via `processar()`, com a classificação real (regra), no mesmo padrão de
`test_processador_modo_execucao.py`: base real via `Database()`, telefone de teste único
por caso, limpo ao final. `EXECUCAO_NORMAL` para que o texto da resposta volte no
resultado (nos outros modos ele fica pendente de aprovação e o retorno é vazio).
"""

import asyncio

import pytest
from database import Database
from models import AtendimentoInfo, Contato, Empresa, ModoExecucao, ProcessamentoMensagem
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato, criar_contato_sem_empresa
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem

# CNPJ sintético válido (mesmo de `test_regras_globais.py`), sem relação com empresa real.
_CNPJ_VALIDO = "11.222.333/0001-81"
_PEDE_NOME = "o seu nome"
_PERGUNTA_CONFIRMACAO = "Posso te chamar assim ou seu nome é outro?"
_PEDE_DOCUMENTO = "o CNPJ da sua empresa ou seu CPF"


@pytest.fixture
def db_session(monkeypatch):
    # O modo vem de um dublê e não é gravado: o banco é compartilhado com o backend que
    # estiver no ar, e mudar o `parametros` ali mudaria o que ele faz com mensagem real.
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    database = Database()
    with database.get_session() as session:
        yield session
        session.rollback()


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _limpar(db_session, *telefones):
    db_session.commit()
    for telefone in telefones:
        apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _contato(db_session, telefone):
    db_session.expire_all()
    return db_session.query(Contato).filter_by(telefone=telefone).first()


def _processar(processador, db_session, telefone, texto, **kwargs):
    return asyncio.run(processador.processar(db_session, telefone, texto, **kwargs))


def _conversar(processador, db_session, telefone, *textos, nome_perfil="Ana Souza"):
    """Manda as mensagens em sequência, sempre com o mesmo `ProfileName` (a Twilio manda
    em todo webhook), e devolve as respostas."""
    return [
        _processar(processador, db_session, telefone, texto, nome_perfil=nome_perfil).resposta
        for texto in textos
    ]


def _desfecho(db_session, telefone):
    """Valor de `nome_perfil_confirmacao` no atendimento do telefone (ou None)."""
    contato = _contato(db_session, telefone)
    ids = [a.id for a in contato.atendimentos] if contato else []
    info = (
        db_session.query(AtendimentoInfo)
        .filter(AtendimentoInfo.atendimento_id.in_(ids), AtendimentoInfo.chave == "nome_perfil_confirmacao")
        .first()
    )
    return info.valor if info else None


@pytest.fixture
def empresa_teste(db_session):
    """Empresa do CNPJ sintético já na base, para o fluxo de CNPJ não consultar a ReceitaWS."""
    empresa = Empresa(cnpj=_CNPJ_VALIDO, nome="Empresa Teste Nome Perfil")
    db_session.add(empresa)
    db_session.commit()
    yield empresa
    db_session.rollback()
    db_session.query(Empresa).filter_by(cnpj=_CNPJ_VALIDO).delete()
    db_session.commit()


def test_telefone_novo_com_nome_valido_pergunta_se_pode_chamar_assim(db_session, processador):
    """A confirmação substitui o pedido de nome; o pedido de CNPJ/CPF continua na mesma
    frase. Nada é gravado antes da resposta."""
    telefone = "+5511999977201"
    try:
        resultado = _processar(processador, db_session, telefone, "oi", nome_perfil="Beto Figu")

        assert resultado.resposta.startswith("Olá, Beto Figu! 👋 Sou o assistente da Inforrel.")
        assert f"{_PERGUNTA_CONFIRMACAO} E para te atender melhor, poderia me informar {_PEDE_DOCUMENTO}?" in (
            resultado.resposta
        )
        assert _PEDE_NOME not in resultado.resposta
        assert _contato(db_session, telefone).nome is None
        assert _desfecho(db_session, telefone) == "aguardando"
    finally:
        _limpar(db_session, telefone)


def test_nome_invalido_e_ignorado_e_fluxo_fica_igual_ao_sem_nome(db_session, processador):
    tel_sem, tel_invalido = "+5511999977202", "+5511999977203"
    try:
        sem_nome = _processar(processador, db_session, tel_sem, "oi")
        com_invalido = _processar(processador, db_session, tel_invalido, "oi", nome_perfil="~~~")

        assert com_invalido.resposta == sem_nome.resposta
        assert _PEDE_NOME in com_invalido.resposta
        assert _PERGUNTA_CONFIRMACAO not in com_invalido.resposta
        assert _contato(db_session, tel_invalido).nome is None
    finally:
        _limpar(db_session, tel_sem, tel_invalido)


def test_contato_existente_sem_nome_pergunta_e_so_grava_depois_de_confirmar(db_session, processador, empresa_teste):
    """Contato com empresa e sem nome: antes caía em PERGUNTAR_NOME ("Como posso te
    chamar?"); com o perfil válido, pergunta se pode chamar pelo nome do perfil."""
    telefone = "+5511999977204"
    try:
        criar_contato(db_session, telefone, empresa=empresa_teste)

        pergunta, resposta = _conversar(processador, db_session, telefone, "oi", "sim", nome_perfil="Ana")

        assert pergunta == f"Olá, Ana! 👋 {_PERGUNTA_CONFIRMACAO}"
        assert resposta == "Combinado, Ana! 😊 Em que posso te ajudar hoje?"
        assert _contato(db_session, telefone).nome == "Ana"
    finally:
        _limpar(db_session, telefone)


def test_nome_ja_existente_nao_e_sobrescrito_nem_perguntado(db_session, processador):
    telefone = "+5511999977205"
    try:
        criar_contato_sem_empresa(db_session, telefone, nome="Roberto")

        resultado = _processar(processador, db_session, telefone, "oi", nome_perfil="Beto Figu")

        assert _PERGUNTA_CONFIRMACAO not in resultado.resposta
        assert _contato(db_session, telefone).nome == "Roberto"
    finally:
        _limpar(db_session, telefone)


def test_nome_digitado_na_mesma_mensagem_vence_o_perfil(db_session, processador):
    telefone = "+5511999977206"
    try:
        resultado = _processar(processador, db_session, telefone, "oi, meu nome é Carla", nome_perfil="Beto Figu")

        assert resultado.resposta.startswith("Olá, Carla!")
        assert _PERGUNTA_CONFIRMACAO not in resultado.resposta
        assert _contato(db_session, telefone).nome == "Carla"
    finally:
        _limpar(db_session, telefone)


@pytest.mark.parametrize(
    "resposta_cliente",
    ["sim", "Sim!", "pode", "pode sim", "isso", "ok", "claro", "👍", "👍🏽", "sim, pode"],
)
def test_confirmacao_grava_o_nome_do_perfil(db_session, processador, resposta_cliente):
    telefone = "+5511999977210"
    try:
        _, resposta = _conversar(processador, db_session, telefone, "oi", resposta_cliente)

        assert resposta == f"Combinado, Ana Souza! 😊 Para te atender melhor, poderia me informar {_PEDE_DOCUMENTO}?"
        assert _contato(db_session, telefone).nome == "Ana Souza"
        assert _desfecho(db_session, telefone) == "confirmado"
    finally:
        _limpar(db_session, telefone)


@pytest.mark.parametrize(
    "resposta_cliente, nome_esperado",
    [
        ("meu nome é Carlos", "Carlos"),
        ("pode me chamar de Cadu", "Cadu"),
        ("Carlos", "Carlos"),
        ("carlos eduardo", "Carlos Eduardo"),
        ("é Carlos", "Carlos"),
    ],
)
def test_outro_nome_grava_o_informado(db_session, processador, resposta_cliente, nome_esperado):
    telefone = "+5511999977211"
    try:
        _, resposta = _conversar(processador, db_session, telefone, "oi", resposta_cliente)

        assert resposta.startswith(f"Combinado, {nome_esperado}! 😊")
        assert _contato(db_session, telefone).nome == nome_esperado
        assert _desfecho(db_session, telefone) == "outro_nome"
    finally:
        _limpar(db_session, telefone)


def test_negacao_sem_nome_pergunta_o_nome_e_grava_a_resposta(db_session, processador):
    telefone = "+5511999977212"
    try:
        _, pergunta, resposta = _conversar(processador, db_session, telefone, "oi", "não", "Carlos")

        assert pergunta == "Como posso te chamar? 😊"
        assert resposta.startswith("Combinado, Carlos! 😊")
        assert _contato(db_session, telefone).nome == "Carlos"
    finally:
        _limpar(db_session, telefone)


def test_cliente_ignora_a_pergunta_e_manda_o_cnpj(db_session, processador, empresa_teste):
    """Não trava: o CNPJ segue o fluxo normal, e o nome do perfil não é gravado."""
    telefone = "+5511999977213"
    try:
        _, resposta = _conversar(processador, db_session, telefone, "oi", _CNPJ_VALIDO)

        assert "Confirmei os dados da empresa *Empresa Teste Nome Perfil*" in resposta
        assert "Combinado" not in resposta
        contato = _contato(db_session, telefone)
        assert contato.nome is None
        assert contato.empresa_id == empresa_teste.id
        assert _desfecho(db_session, telefone) == "ignorado"
    finally:
        _limpar(db_session, telefone)


def test_cliente_ignora_a_pergunta_e_ela_nao_volta(db_session, processador):
    """Recomendação registrada: não insistir. Quem ignorou não recebe a pergunta de novo
    neste atendimento."""
    telefone = "+5511999977214"
    try:
        _, *seguintes = _conversar(
            processador, db_session, telefone, "oi", "quero orçamento de relógio de ponto", "oi"
        )

        assert all(_PERGUNTA_CONFIRMACAO not in texto for texto in seguintes)
        assert _contato(db_session, telefone).nome is None
        assert _desfecho(db_session, telefone) == "ignorado"
    finally:
        _limpar(db_session, telefone)


def test_confirmacao_e_cnpj_na_mesma_mensagem_tratam_as_duas_coisas(db_session, processador, empresa_teste):
    telefone = "+5511999977215"
    try:
        _, resposta = _conversar(processador, db_session, telefone, "oi", f"sim, {_CNPJ_VALIDO}")

        assert "Confirmei os dados da empresa *Empresa Teste Nome Perfil*" in resposta
        contato = _contato(db_session, telefone)
        assert contato.nome == "Ana Souza"  # e não "Sim", que o classificador extrai junto do CNPJ
        assert contato.empresa_id == empresa_teste.id
        assert _desfecho(db_session, telefone) == "confirmado"
    finally:
        _limpar(db_session, telefone)


def test_orcamento_no_primeiro_contato_pergunta_o_nome_e_retoma_a_pergunta_do_orcamento(db_session, processador):
    """No modo orçamento a saudação nunca pediu CNPJ/CPF; só ganha a confirmação do nome.
    Depois do "sim", a pergunta pendente do orçamento volta."""
    telefone = "+5511999977216"
    try:
        abertura, resposta = _conversar(
            processador, db_session, telefone, "quero orçamento de relógio de ponto", "pode sim"
        )

        primeira_parte, *resto = abertura.split("\n\n")
        assert primeira_parte == f"Olá, Ana Souza! 👋 Sou o assistente da Inforrel.\n{_PERGUNTA_CONFIRMACAO}"
        assert _PEDE_DOCUMENTO not in abertura
        pergunta_orcamento = resto[-1]
        assert resposta == f"Combinado, Ana Souza! 😊\n\n{pergunta_orcamento}"
        assert _contato(db_session, telefone).nome == "Ana Souza"
    finally:
        _limpar(db_session, telefone)


def test_confirmacao_junto_da_resposta_do_orcamento_nao_engole_a_resposta(db_session, processador):
    """ "sim, biometria" confirma o nome e a parte "biometria" segue para o Finalizando,
    que responde como responderia a "biometria" sozinha."""
    tel_com, tel_sem = "+5511999977217", "+5511999977218"
    try:
        _, com_nome = _conversar(
            processador, db_session, tel_com, "quero orçamento de relógio de ponto", "sim, biometria"
        )
        _, sem_nome = _conversar(
            processador, db_session, tel_sem, "quero orçamento de relógio de ponto", "biometria", nome_perfil=None
        )

        assert com_nome == sem_nome
        assert _contato(db_session, tel_com).nome == "Ana Souza"
    finally:
        _limpar(db_session, tel_com, tel_sem)


def test_processamento_registra_nome_perfil_so_quando_recebido(db_session, processador):
    tel_com, tel_sem = "+5511999977208", "+5511999977209"
    try:
        com = _processar(processador, db_session, tel_com, "oi", nome_perfil="~~~")
        sem = _processar(processador, db_session, tel_sem, "oi")

        ent_com = db_session.get(ProcessamentoMensagem, com.processamento_id).entidades
        ent_sem = db_session.get(ProcessamentoMensagem, sem.processamento_id).entidades
        assert ent_com["nome_perfil_whatsapp"] == "~~~"
        assert ent_com["nome_perfil_aproveitavel"] is False
        assert "nome_perfil_whatsapp" not in ent_sem
    finally:
        _limpar(db_session, tel_com, tel_sem)
