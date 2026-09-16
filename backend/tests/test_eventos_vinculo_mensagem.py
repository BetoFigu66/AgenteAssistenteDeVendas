"""`EventoAtendimento.mensagem_id`/`processamento_id` preenchidos (achado A2, auditoria 2026-08).

As duas colunas existiam e eram migradas, mas nenhum dos call sites de
`registrar_evento_atendimento` as preenchia — a trilha de auditoria não dizia qual
mensagem provocou cada evento.

O preenchimento é feito por back-fill no fim de `processar()`, e não passando os ids
adiante, por dois motivos: o `processamento_id` só nasce *depois* da decisão (é ele que
registra o resultado dela), e passar o `mensagem_id` exigiria acrescentá-lo a seis
assinaturas no caminho, onde um chamador esquecido falharia em silêncio com `None`.

O back-fill só é possível porque os eventos deixaram de ser commitados um a um (achado B1).
"""

import asyncio

import pytest
from database import Database
from models import Atendimento, Contato, EventoAtendimento, Mensagem, OrigemMensagem
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.processador import ProcessadorMensagem


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


def test_eventos_ficam_vinculados_a_mensagem_e_ao_processamento(db_session, processador):
    telefone = "5511999955001"
    try:
        _limpar(db_session, telefone)
        asyncio.run(processador.processar(db_session, telefone, "Quero orcamento de catraca"))
        db_session.commit()

        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        atendimento = db_session.query(Atendimento).filter_by(contato_id=contato.id).first()
        msg_in = (
            db_session.query(Mensagem)
            .filter_by(telefone=telefone, origem=OrigemMensagem.USER)
            .order_by(Mensagem.id.desc())
            .first()
        )

        eventos = db_session.query(EventoAtendimento).filter_by(atendimento_id=atendimento.id).all()
        # Sem isto o teste passaria vazio e não provaria nada.
        assert eventos, "a mensagem deveria ter gerado ao menos um evento de auditoria"

        for evento in eventos:
            assert evento.mensagem_id == msg_in.id, f"evento {evento.tipo} sem vínculo com a mensagem"
            assert evento.processamento_id == msg_in.processamento_id, (
                f"evento {evento.tipo} sem vínculo com o processamento"
            )
    finally:
        _limpar(db_session, telefone)


def test_limpeza_por_telefone_remove_eventos_antes_das_mensagens(db_session, processador):
    """Regressão da FK: com `mensagem_id` preenchido, apagar `mensagens` antes dos
    eventos viola `eventos_atendimento_mensagem_id_fkey`. Enquanto a coluna era sempre
    NULL, a ordem em `dev_limpeza_telefone` não importava e ninguém notava."""
    telefone = "5511999955002"
    try:
        _limpar(db_session, telefone)
        asyncio.run(processador.processar(db_session, telefone, "Quero orcamento de catraca"))
        db_session.commit()

        resultado = apagar_dados_telefone(db_session, telefone)
        db_session.commit()

        assert resultado["removidos"]["eventos_atendimento"] > 0
        assert resultado["removidos"]["mensagens"] > 0
        assert db_session.query(Contato).filter_by(telefone=telefone).first() is None
    finally:
        _limpar(db_session, telefone)
