"""Testes de `services/conversacao/regras_globais.py` — FORNECER_CNPJ, FORNECER_CPF,
FORNECER_DATA_NASCIMENTO (continuação isolada) e FORNECER_NOME. Zero cobertura antes
desta rodada (levantamento de cobertura de 2026-08-21). ESCALAR_HUMANO/RECLAMAR/projeto
complexo já são cobertos por `test_escalonamento.py` — não duplicados aqui.

Padrão de integração real (base real via `Database()`, sem pytest-asyncio, telefone de
teste único por caso, limpo ao final) — mesma convenção de `test_escalonamento.py`. CNPJ
e CPF não fazem chamada de rede real nestes testes: `obter_ou_criar_empresa` retorna
direto do banco quando a Empresa já existe (sem consultar ReceitaWS), e a consulta de
crédito de CPF é um stub sem provedor configurado (`services/cpf/consulta_credito.py`) —
nenhum dos dois precisa de mock.
"""

import asyncio

import pytest
from database import Database
from models import Contato, Empresa, Pessoa, TipoDocumento
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.debug_log import DebugLogger
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, identificar_por_telefone
from services.processador import ProcessadorMensagem

# CNPJ/CPF sintéticos válidos (passam no dígito verificador), sem relação com pessoa/
# empresa real — mesmo papel dos exemplos já usados em `tests/test_cpf.py` (CPF) e nos
# exemplos de documentação da Receita Federal (CNPJ).
_CNPJ_VALIDO = "11.222.333/0001-81"
_CPF_VALIDO = "52998224725"


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


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _limpar_com_empresa(db_session, telefone, cnpj):
    """`apagar_dados_telefone` não remove Empresa/Pessoa de propósito (podem ser
    compartilhadas por outros contatos) — os testes que criam uma direto precisam
    apagá-la também, depois do atendimento que a referencia já ter sido removido."""
    _limpar(db_session, telefone)
    db_session.query(Empresa).filter_by(cnpj=cnpj).delete()
    db_session.commit()


def _limpar_com_pessoa(db_session, telefone, cpf_formatado):
    _limpar(db_session, telefone)
    db_session.query(Pessoa).filter_by(cpf=cpf_formatado).delete()
    db_session.commit()


def test_fornecer_cnpj_cria_atendimento_vinculado_a_empresa_existente(db_session):
    """`_executar_fornecer_cnpj` (regras_globais.py:87-96) — Empresa já cadastrada no
    banco: `obter_ou_criar_empresa` não precisa consultar a ReceitaWS."""
    telefone = "5511999988001"
    try:
        empresa = Empresa(cnpj=_CNPJ_VALIDO, nome="Empresa Teste Regras Globais")
        db_session.add(empresa)
        db_session.commit()

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        resultado_class = _resultado(Intencao.FORNECER_CNPJ, cnpjs=[_CNPJ_VALIDO])
        p = ProcessadorMensagem()
        dlog = DebugLogger(telefone=telefone, msg_id=0)

        resposta = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo=f"meu cnpj é {_CNPJ_VALIDO}",
                identificacao=identificacao,
                resultado_class=resultado_class,
                dlog=dlog,
            )
        )
        db_session.commit()

        assert resposta.template_usado == "CNPJ_CONSULTADO_OK"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
        atendimento = contato.atendimentos[0]
        assert atendimento.empresa_id == empresa.id
    finally:
        _limpar_com_empresa(db_session, telefone, _CNPJ_VALIDO)


def test_fornecer_cpf_sem_data_nascimento_pergunta_e_marca_pendente(db_session):
    """`_executar_fornecer_cpf` (regras_globais.py:99-111) sem data de nascimento na
    mesma mensagem: pergunta a data e guarda o CPF em `AtendimentoInfo` (cpf_pendente)
    pra completar depois."""
    telefone = "5511999988002"
    try:
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        resultado_class = _resultado(Intencao.FORNECER_CPF, cpfs=[_CPF_VALIDO])
        p = ProcessadorMensagem()
        dlog = DebugLogger(telefone=telefone, msg_id=0)

        resposta = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo=f"meu cpf é {_CPF_VALIDO}",
                identificacao=identificacao,
                resultado_class=resultado_class,
                dlog=dlog,
            )
        )
        db_session.commit()

        assert resposta.template_usado == "PERGUNTAR_DATA_NASCIMENTO"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.tipo_documento == TipoDocumento.CPF
        assert atendimento.pessoa_id is None
        assert p._info_atendimento(db_session, atendimento.id, "cpf_pendente") == _CPF_VALIDO
    finally:
        _limpar(db_session, telefone)


def test_fornecer_cpf_com_data_nascimento_na_mesma_mensagem_conclui(db_session):
    """`_executar_fornecer_cpf` com `datas_nascimento` já presente na mesma mensagem:
    cria a Pessoa e conclui sem precisar de uma segunda mensagem."""
    telefone = "5511999988003"
    try:
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        resultado_class = _resultado(
            Intencao.FORNECER_CPF, cpfs=[_CPF_VALIDO], datas_nascimento=["1990-01-01"]
        )
        p = ProcessadorMensagem()

        resposta = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo=f"meu cpf é {_CPF_VALIDO}, nasci em 01/01/1990",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()

        assert resposta.template_usado == "CPF_CONSULTADO_OK"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.pessoa_id is not None
        assert atendimento.pessoa.cpf == "529.982.247-25"  # persistido formatado
    finally:
        _limpar_com_pessoa(db_session, telefone, "529.982.247-25")


def test_fornecer_data_nascimento_isolada_completa_cpf_pendente(db_session):
    """`_builder_fornecer_data_nascimento` (regras_globais.py:114-149) — continuação do
    fluxo PF: 1ª mensagem dá o CPF sem data (fica pendente); 2ª mensagem só com a data,
    sem repetir o CPF, completa o cadastro."""
    telefone = "5511999988004"
    try:
        p = ProcessadorMensagem()

        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo=f"meu cpf é {_CPF_VALIDO}",
                identificacao=ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[]),
                resultado_class=_resultado(Intencao.FORNECER_CPF, cpfs=[_CPF_VALIDO]),
            )
        )
        db_session.commit()

        identificacao2 = identificar_por_telefone(db_session, telefone)
        dlog = DebugLogger(telefone=telefone, msg_id=1)
        resposta2 = asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="nasci em 01/01/1990",
                identificacao=identificacao2,
                resultado_class=_resultado(
                    Intencao.FORNECER_DATA_NASCIMENTO, datas_nascimento=["1990-01-01"]
                ),
                dlog=dlog,
            )
        )
        db_session.commit()

        assert resposta2.template_usado == "CPF_CONSULTADO_OK"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.pessoa_id is not None
        assert p._info_atendimento(db_session, atendimento.id, "cpf_pendente") is None
    finally:
        _limpar_com_pessoa(db_session, telefone, "529.982.247-25")


def test_fornecer_nome_grava_no_contato_existente_sem_nome(db_session):
    """`_executar_fornecer_nome` (regras_globais.py:152-162) — só grava quando o
    Contato já existe e ainda não tem nome (efeito colateral silencioso, sem gerar
    fragmento de resposta)."""
    telefone = "5511999988005"
    try:
        contato = Contato(telefone=telefone, nome=None)
        db_session.add(contato)
        db_session.commit()
        db_session.refresh(contato)

        identificacao = ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
        )
        resultado_class = _resultado(Intencao.FORNECER_NOME, nomes=["Fulano de Tal"])
        p = ProcessadorMensagem()

        asyncio.run(
            p._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="meu nome é Fulano de Tal",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()
        db_session.refresh(contato)

        assert contato.nome == "Fulano de Tal"
    finally:
        _limpar(db_session, telefone)
