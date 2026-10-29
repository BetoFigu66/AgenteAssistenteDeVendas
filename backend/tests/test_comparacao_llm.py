"""O que o sistema faria sem o LLM e o que fez com ele (`services/llm/comparacao.py`,
tabela `comparacoes_llm`), e o mascaramento da aba Sistema (`services/diagnostico_sistema.py`).

Pedido do Beto (12/10/2026), depois de descobrir que a Groq bloqueou a organização e o
sistema seguia calado só com regras.
"""

import asyncio
from types import SimpleNamespace

import pytest
from config import Settings
from database import Database
from models import ComparacaoLLM, ModoExecucao
from services import diagnostico_sistema
from services.classificador import Intencao, classificar
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.llm import LLMProvider, LLMResponse
from services.llm import comparacao as comparacao_llm
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem
from services.respostas.gerador import GeradorRespostas


class LLMFalso(LLMProvider):
    def __init__(self, conteudo="Resposta do LLM.", json=None, falha=None):
        self._conteudo, self._json, self._falha = conteudo, json, falha

    async def completar(self, prompt_sistema, prompt_usuario, temperatura=None, max_tokens=None):
        if self._falha:
            raise self._falha
        return LLMResponse(conteudo=self._conteudo, modelo="falso-1", tokens_input=10, tokens_output=5)

    async def completar_json(self, prompt_sistema, prompt_usuario, temperatura=None):
        if self._falha:
            raise self._falha
        return self._json or {}

    @property
    def nome(self):
        return "falso"


def _coletar(coro):
    async def rodar():
        token = comparacao_llm.iniciar()
        try:
            resultado = await coro
            return resultado, comparacao_llm.coletados()
        finally:
            comparacao_llm.encerrar(token)

    return asyncio.run(rodar())


# Sem regra que bata: a confiança fica abaixo do limite e o LLM é consultado.
_TEXTO_SEM_REGRA = "zzqx wuvb plorf"


def test_llm_com_erro_na_classificacao_volta_para_as_regras():
    llm = LLMFalso(falha=RuntimeError("organization_restricted"))
    resultado, usos = _coletar(classificar(_TEXTO_SEM_REGRA, llm=llm))

    assert resultado.origem == "regra"
    (uso,) = usos
    assert uso.etapa == comparacao_llm.CLASSIFICACAO
    assert uso.situacao == comparacao_llm.ERRO
    assert "organization_restricted" in uso.erro
    assert uso.com_llm is None


def test_classificacao_pelo_llm_registra_os_dois_lados():
    llm = LLMFalso(json={"intencao": "pedir_catalogo", "confianca": 0.9, "entidades": {}})
    resultado, usos = _coletar(classificar(_TEXTO_SEM_REGRA, llm=llm))

    assert resultado.origem == "llm"
    assert resultado.intencao_principal == Intencao.PEDIR_CATALOGO
    (uso,) = usos
    assert uso.situacao == comparacao_llm.OK
    assert uso.dados["intencoes_llm"] == ["pedir_catalogo"]
    assert "pedir_catalogo" in uso.com_llm


def test_sem_llm_o_ponto_fica_registrado_como_indisponivel():
    _, usos = _coletar(classificar(_TEXTO_SEM_REGRA, llm=None))

    (uso,) = usos
    assert uso.situacao == comparacao_llm.INDISPONIVEL


def test_regra_confiante_nao_registra_nada():
    _, usos = _coletar(classificar("quero falar com um atendente", llm=LLMFalso()))

    assert usos == []


_TRECHO = SimpleNamespace(titulo="Bastão de ronda", conteudo="O bastão registra as rondas.", score=0.9, metadados={})


@pytest.mark.parametrize(
    ("llm", "situacao"),
    [
        (LLMFalso(conteudo="O bastão registra cada ponto da ronda."), comparacao_llm.OK),
        (LLMFalso(falha=RuntimeError("fora do ar")), comparacao_llm.ERRO),
        (LLMFalso(conteudo="   "), comparacao_llm.VAZIO),
        (None, comparacao_llm.INDISPONIVEL),
    ],
)
def test_resposta_da_base_registra_o_template_que_iria_sem_llm(llm, situacao):
    gerador = GeradorRespostas(llm=llm)
    resposta, usos = _coletar(gerador.gerar_com_rag("como funciona o bastão?", [_TRECHO]))

    (uso,) = usos
    assert uso.etapa == comparacao_llm.RESPOSTA_RAG
    assert uso.situacao == situacao
    assert uso.sem_llm and uso.sem_llm != "O bastão registra cada ponto da ronda."
    assert uso.texto_usado == resposta.texto


def test_registrar_fora_de_coleta_nao_faz_nada():
    comparacao_llm.registrar(comparacao_llm.UsoLLM(etapa="x", situacao="ok", sem_llm="a"))
    assert comparacao_llm.coletados() == []


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    with Database().get_session() as session:
        yield session
        session.rollback()


def test_processar_grava_a_comparacao_ligada_a_pergunta_e_a_resposta(db_session):
    telefone = "+5500900000321"
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()
    try:
        processador = ProcessadorMensagem(llm=LLMFalso(falha=RuntimeError("organization_restricted")))
        resultado = asyncio.run(processador.processar(db_session, telefone, _TEXTO_SEM_REGRA))
        db_session.commit()

        registros = (
            db_session.query(ComparacaoLLM)
            .filter(ComparacaoLLM.processamento_id == resultado.processamento_id)
            .all()
        )
        classificacao = [r for r in registros if r.etapa == comparacao_llm.CLASSIFICACAO]
        assert len(classificacao) == 1
        assert classificacao[0].situacao == comparacao_llm.ERRO
        assert classificacao[0].resposta_mensagem_id == resultado.mensagens_saida_ids[0]
        assert classificacao[0].mensagem_id != classificacao[0].resposta_mensagem_id
    finally:
        db_session.commit()
        apagar_dados_telefone(db_session, telefone)
        db_session.commit()


# ----------------------------------------------------------------------
# Aba Sistema: mascaramento
# ----------------------------------------------------------------------


def test_configuracoes_nao_expoem_dados_sensiveis():
    cfg = Settings(
        _env_file=None,
        LLM_API_KEY="gsk_segredo123",
        TWILIO_ACCOUNT_SID="AC_segredo",
        TWILIO_WHATSAPP_NUMBER="whatsapp:+5511999998888",
        AUTH_USUARIO_PADRAO="fulano",
        DATABASE_URL="postgresql://usuario:senha123@host:5432/banco",
    )
    itens = {c["nome"]: c for c in diagnostico_sistema.configuracoes(cfg)}
    texto = str(itens)

    for segredo in ("gsk_segredo123", "AC_segredo", "fulano", "senha123", "usuario:", "99999"):
        assert segredo not in texto
    assert itens["LLM_API_KEY"]["valor"] == "definido"
    assert itens["TWILIO_AUTH_TOKEN"]["valor"] == "não definido"
    assert itens["TWILIO_WHATSAPP_NUMBER"]["valor"] == "***8888"
    assert itens["DATABASE_URL"]["valor"] == "postgresql://***@host:5432/banco"
    assert itens["LLM_PROVIDER"]["valor"] == "groq"
    assert itens["LLM_API_KEY"]["origem"] == "configurado"
    assert itens["SESSION_SECRET_KEY"]["aviso"]
