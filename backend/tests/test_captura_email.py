"""Report #8: "meu email é ..." caía no "Desculpa, não entendi muito bem" (NAO_ENTENDI).

O e-mail já era extraído pelo classificador e gravado em `AtendimentoInfo`
(`email_contato`), mas nenhuma Regra do motor respondia a ele: não existe intenção
FORNECER_EMAIL, só a entidade. A correção é uma regra global que casa pela entidade, grava
o e-mail e agradece, como o aviso do CPF ("Anotei seu CPF."), sem ser exclusiva.

Classificação REAL (só regras, sem LLM), como em
`test_processador_divergencias_bateria_cenarios.py`: intenção fabricada esconderia
justamente o ponto do bug (o classificador devolve DESCONHECIDO para essa mensagem).
"""

import asyncio

import pytest
from database import Database
from models import AtendimentoInfo, Contato
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.processador import ProcessadorMensagem

_EMAIL = "fulano@exemplo.com"


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _conversar(db_session, telefone, mensagens):
    p = ProcessadorMensagem()
    return [asyncio.run(p.processar(db=db_session, telefone=telefone, conteudo=m)) for m in mensagens]


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _email_gravado(db_session, telefone):
    contato = db_session.query(Contato).filter_by(telefone=telefone).first()
    assert contato is not None
    info = (
        db_session.query(AtendimentoInfo)
        .filter(AtendimentoInfo.chave == "email_contato")
        .filter(AtendimentoInfo.atendimento_id.in_([a.id for a in contato.atendimentos]))
        .first()
    )
    return contato.email, info.valor if info else None


def test_email_sozinho_e_anotado_e_agradecido_em_vez_de_nao_entendi(db_session):
    """A conversa do report: pergunta de produto, depois só o e-mail."""
    telefone = "+5511999977801"
    try:
        resultados = _conversar(db_session, telefone, ["Quais produtos a Inforrel vende?", f"meu email é {_EMAIL}"])
        resposta = resultados[-1].resposta
        assert "não entendi" not in resposta.lower()
        assert "anotei seu e-mail" in resposta.lower()
        assert _email_gravado(db_session, telefone) == (_EMAIL, _EMAIL)
    finally:
        _limpar(db_session, telefone)


def test_email_junto_com_pedido_nao_e_exclusivo(db_session):
    """A mensagem seguinte do report: o aviso abre a resposta e o pedido segue."""
    telefone = "+5511999977802"
    try:
        resultados = _conversar(
            db_session,
            telefone,
            [
                "Quais produtos a Inforrel vende?",
                f"Quero comprar catracas modelo fit. Envia o orçamento para o email {_EMAIL}",
            ],
        )
        resposta = resultados[-1].resposta
        assert resposta.lower().startswith("obrigado, anotei seu e-mail.")
        assert "orçamento" in resposta
        assert _email_gravado(db_session, telefone) == (_EMAIL, _EMAIL)
    finally:
        _limpar(db_session, telefone)
