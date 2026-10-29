"""Testes de `services/conversacao/regras_globais.py` — FORNECER_CNPJ, FORNECER_CPF e
FORNECER_NOME. (A continuação pela data de nascimento saiu em 11/10/2026: a data não é
mais pedida.) Zero cobertura antes
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
from services.conversacao import pilha
from services.debug_log import DebugLogger
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao
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
    telefone = "+5511999988001"
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

        # A captura não é exclusiva: só com o documento, a resposta completa com a pergunta
        # de como ajudar.
        assert resposta.template_usado == "CNPJ_CONSULTADO_OK+COMO_POSSO_AJUDAR"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato is not None
        atendimento = contato.atendimentos[0]
        assert atendimento.empresa_id == empresa.id
    finally:
        _limpar_com_empresa(db_session, telefone, _CNPJ_VALIDO)


def test_fornecer_cpf_conclui_sem_pedir_data_de_nascimento(db_session):
    """`_executar_fornecer_cpf`: o CPF sozinho completa o cadastro PF (a data de nascimento
    não é mais pedida nem gravada, decisão de 11/10/2026)."""
    telefone = "+5511999988002"
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

        assert resposta.template_usado == "CPF_CONSULTADO_OK+COMO_POSSO_AJUDAR"
        assert resposta.texto == "Anotei seu CPF.\n\nEm que posso ajudar hoje?"
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = contato.atendimentos[0]
        assert atendimento.tipo_documento == TipoDocumento.CPF
        assert atendimento.pessoa.cpf == "529.982.247-25"  # persistido formatado
        assert atendimento.pessoa.data_nascimento is None
        assert pilha.abertas(atendimento) == []
    finally:
        _limpar_com_pessoa(db_session, telefone, "529.982.247-25")


def test_data_de_nascimento_na_mensagem_nao_e_gravada(db_session):
    """Se o cliente manda a data por conta própria, ela não vai para a `Pessoa` (REQ-005:
    dado que o sistema não usa)."""
    telefone = "+5511999988003"
    try:
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
        resultado_class = _resultado(
            Intencao.FORNECER_CPF, cpfs=[_CPF_VALIDO], datas_nascimento=["1990-01-01"]
        )
        asyncio.run(
            ProcessadorMensagem()._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo=f"meu cpf é {_CPF_VALIDO}, nasci em 01/01/1990",
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        )
        db_session.commit()

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        assert contato.atendimentos[0].pessoa.data_nascimento is None
    finally:
        _limpar_com_pessoa(db_session, telefone, "529.982.247-25")


def test_fornecer_nome_grava_no_contato_existente_sem_nome(db_session):
    """`_executar_fornecer_nome` (regras_globais.py:152-162) — só grava quando o
    Contato já existe e ainda não tem nome (efeito colateral silencioso, sem gerar
    fragmento de resposta)."""
    telefone = "+5511999988005"
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
