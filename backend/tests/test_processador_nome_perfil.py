"""Uso do nome de perfil do WhatsApp (`ProfileName`) em `ProcessadorMensagem.processar()`.

Ponta a ponta via `processar()`, com a classificação real (regra), no mesmo padrão de
`test_processador_modo_execucao.py`: base real via `Database()`, telefone de teste único
por caso, limpo ao final. `EXECUCAO_NORMAL` para que o texto da resposta volte no
resultado (nos outros modos ele fica pendente de aprovação e o retorno é vazio).
"""

import asyncio

import pytest
from database import Database
from models import Contato, Empresa, ModoExecucao, ProcessamentoMensagem
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato, criar_contato_sem_empresa
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem

# CNPJ sintético válido (mesmo de `test_regras_globais.py`), sem relação com empresa real.
_CNPJ_VALIDO = "11.222.333/0001-81"
_PEDE_NOME = "o seu nome"


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


def test_telefone_novo_com_nome_valido_nao_pergunta_o_nome(db_session, processador):
    telefone = "+5511999977201"
    try:
        resultado = _processar(processador, db_session, telefone, "oi", nome_perfil="Beto Figu")

        assert "Olá, Beto Figu!" in resultado.resposta
        assert _PEDE_NOME not in resultado.resposta
        assert _contato(db_session, telefone).nome == "Beto Figu"
    finally:
        _limpar(db_session, telefone)


def test_nome_invalido_e_ignorado_e_fluxo_fica_igual_ao_sem_nome(db_session, processador):
    tel_sem, tel_invalido = "+5511999977202", "+5511999977203"
    try:
        sem_nome = _processar(processador, db_session, tel_sem, "oi")
        com_invalido = _processar(processador, db_session, tel_invalido, "oi", nome_perfil="~~~")

        assert com_invalido.resposta == sem_nome.resposta
        assert _PEDE_NOME in com_invalido.resposta
        assert _contato(db_session, tel_invalido).nome is None
    finally:
        _limpar(db_session, tel_sem, tel_invalido)


def test_contato_existente_sem_nome_e_preenchido_e_saudacao_usa_o_nome(db_session, processador):
    """Contato com empresa e sem nome: antes caía em PERGUNTAR_NOME ("Como posso te
    chamar?"); com o perfil válido, cumprimenta pelo nome."""
    telefone = "+5511999977204"
    try:
        empresa = Empresa(cnpj=_CNPJ_VALIDO, nome="Empresa Teste Nome Perfil")
        db_session.add(empresa)
        db_session.commit()
        criar_contato(db_session, telefone, empresa=empresa)

        resultado = _processar(processador, db_session, telefone, "oi", nome_perfil="Ana")

        assert resultado.resposta.startswith("Olá, Ana!")
        assert "Como posso te chamar" not in resultado.resposta
        assert _contato(db_session, telefone).nome == "Ana"
    finally:
        _limpar(db_session, telefone)
        db_session.query(Empresa).filter_by(cnpj=_CNPJ_VALIDO).delete()
        db_session.commit()


def test_nome_ja_existente_nao_e_sobrescrito(db_session, processador):
    telefone = "+5511999977205"
    try:
        criar_contato_sem_empresa(db_session, telefone, nome="Roberto")

        _processar(processador, db_session, telefone, "oi", nome_perfil="Beto Figu")

        assert _contato(db_session, telefone).nome == "Roberto"
    finally:
        _limpar(db_session, telefone)


def test_nome_digitado_na_mesma_mensagem_vence_o_perfil(db_session, processador):
    telefone = "+5511999977206"
    try:
        _processar(processador, db_session, telefone, "oi, meu nome é Carla", nome_perfil="Beto Figu")

        assert _contato(db_session, telefone).nome == "Carla"
    finally:
        _limpar(db_session, telefone)


def test_nome_digitado_depois_substitui_o_que_veio_do_perfil(db_session, processador):
    telefone = "+5511999977207"
    try:
        _processar(processador, db_session, telefone, "oi", nome_perfil="Beto Figu")
        assert _contato(db_session, telefone).nome == "Beto Figu"

        _processar(processador, db_session, telefone, "meu nome é Roberto", nome_perfil="Beto Figu")

        assert _contato(db_session, telefone).nome == "Roberto"
    finally:
        _limpar(db_session, telefone)


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
