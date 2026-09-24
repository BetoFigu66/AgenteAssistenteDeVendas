"""Atomicidade entre mudança de estado e evento de auditoria (achado B1, auditoria 2026-08).

O `CLAUDE.md` define a trilha de `EventoAtendimento` como fonte de verdade para "por que o
bot respondeu X". Se a mudança de estado e o evento que a explica caem em transações
diferentes, uma falha no meio deixa o atendimento com estado novo e sem rastro. No pior
caso (`concluir`), `modo_operacao=HUMANO` fica gravado sozinho: suprime toda resposta
automática futura e ninguém descobre por quê.

A suíte inteira passa tanto com um commit quanto com dois — só um teste que force a falha
entre eles pega a diferença. É o que este arquivo faz, via `rollback()`.
"""

import pytest
from database import Database
from models import Atendimento, EventoAtendimento, FaseAtendimento, ModoOperacao, StatusAtendimento
from services.atendimentos import proximo_numero_atendimento_cliente
from services.conversacao.acoes import ContextoAcao
from services.conversacao.estados.finalizando import FINALIZANDO
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato_sem_empresa
from services.processador import ProcessadorMensagem


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _atendimento_em_esclarecendo(db_session, telefone) -> Atendimento:
    contato = criar_contato_sem_empresa(db_session, telefone, nome=None)
    numero = proximo_numero_atendimento_cliente(db_session, contato.id)
    atendimento = Atendimento(
        contato_id=contato.id,
        status=StatusAtendimento.ATIVO,
        fase=FaseAtendimento.ESCLARECENDO,
        modo_operacao=ModoOperacao.AGENTE,
        numero_atendimento_cliente=numero,
    )
    db_session.add(atendimento)
    db_session.commit()
    return atendimento


def _ctx(db_session, telefone, atendimento) -> ContextoAcao:
    return ContextoAcao(
        db=db_session,
        telefone=telefone,
        conteudo="",
        identificacao=object(),
        resultado_class=object(),
        processador=ProcessadorMensagem(),
        atendimento=atendimento,
    )


def _eventos_de(db_session, atendimento_id) -> list[EventoAtendimento]:
    return db_session.query(EventoAtendimento).filter_by(atendimento_id=atendimento_id).all()


def test_transicao_e_evento_desfazem_juntos(db_session):
    """Falha depois da transição não pode deixar a fase nova gravada."""
    telefone = "+5511999966001"
    try:
        atendimento = _atendimento_em_esclarecendo(db_session, telefone)
        atendimento_id = atendimento.id
        assert _eventos_de(db_session, atendimento_id) == []

        FINALIZANDO.transicionar_para(
            _ctx(db_session, telefone, atendimento),
            FaseAtendimento.FINALIZANDO,
            motivo="teste de atomicidade",
        )

        # Simula a falha adiante no processamento da mensagem.
        db_session.rollback()

        assert atendimento.fase == FaseAtendimento.ESCLARECENDO
        assert _eventos_de(db_session, atendimento_id) == []
    finally:
        _limpar(db_session, telefone)


def test_transicao_e_evento_persistem_juntos(db_session):
    """O outro lado: no caminho feliz, os dois têm que estar lá."""
    telefone = "+5511999966002"
    try:
        atendimento = _atendimento_em_esclarecendo(db_session, telefone)

        FINALIZANDO.transicionar_para(
            _ctx(db_session, telefone, atendimento),
            FaseAtendimento.FINALIZANDO,
            motivo="teste de atomicidade",
        )
        db_session.commit()

        assert atendimento.fase == FaseAtendimento.FINALIZANDO
        eventos = _eventos_de(db_session, atendimento.id)
        assert len(eventos) == 1
        assert eventos[0].estado_anterior == "esclarecendo"
        assert eventos[0].estado_novo == "finalizando"
    finally:
        _limpar(db_session, telefone)
