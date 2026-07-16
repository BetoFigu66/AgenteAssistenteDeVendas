"""Testes do ciclo de vida de atendimentos (REQ-016 Fase 1 — encerrar/reabrir/motivos)."""

import pytest
from database import Database
from models import Atendimento, MotivoEncerramento, StatusAtendimento
from services import atendimentos as svc
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato_sem_empresa


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _novo_atendimento(db_session, telefone) -> Atendimento:
    contato = criar_contato_sem_empresa(db_session, telefone, nome=None)
    return svc.obter_ou_criar_atendimento(db_session, contato)


def test_encerrar_atendimento_seta_motivo_e_auditoria(db_session):
    telefone = "5511999983001"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        svc.encerrar_atendimento(
            db_session, atendimento, motivo=MotivoEncerramento.MANUAL_VENDEDOR, ator="vendedor:Rita"
        )
        assert atendimento.status == StatusAtendimento.ENCERRADO
        assert atendimento.motivo_encerramento == "manual_vendedor"
        assert atendimento.encerrado_por == "vendedor:Rita"
        assert atendimento.encerrado_em is not None
    finally:
        _limpar(db_session, telefone)


def test_encerrar_atendimento_ja_encerrado_levanta_erro(db_session):
    telefone = "5511999983002"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        svc.encerrar_atendimento(db_session, atendimento, motivo=MotivoEncerramento.MANUAL_VENDEDOR, ator="vendedor")
        with pytest.raises(ValueError):
            svc.encerrar_atendimento(db_session, atendimento, motivo=MotivoEncerramento.ABANDONO, ator="sistema")
    finally:
        _limpar(db_session, telefone)


def test_reabrir_atendimento_limpa_motivo_e_seta_auditoria(db_session):
    telefone = "5511999983003"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        svc.encerrar_atendimento(
            db_session, atendimento, motivo=MotivoEncerramento.CONCLUIDO_PELO_CLIENTE, ator="cliente"
        )
        svc.reabrir_atendimento(db_session, atendimento, ator="cliente", justificativa="voltou a falar")
        assert atendimento.status == StatusAtendimento.ATIVO
        assert atendimento.motivo_encerramento is None
        assert atendimento.reaberto_por == "cliente"
        assert atendimento.reabertura_justificativa == "voltou a falar"
        assert atendimento.reaberto_em is not None
    finally:
        _limpar(db_session, telefone)


def test_reabrir_atendimento_concluido_conversao_bloqueado(db_session):
    telefone = "5511999983004"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        svc.encerrar_atendimento(db_session, atendimento, motivo=MotivoEncerramento.CONCLUIDO_CONVERSAO, ator="sistema")
        with pytest.raises(ValueError):
            svc.reabrir_atendimento(db_session, atendimento, ator="vendedor")
        assert atendimento.status == StatusAtendimento.ENCERRADO
    finally:
        _limpar(db_session, telefone)


def test_atendimento_mais_recente_retorna_independente_do_status(db_session):
    telefone = "5511999983005"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        svc.encerrar_atendimento(db_session, atendimento, motivo=MotivoEncerramento.ABANDONO, ator="sistema")
        contato = atendimento.contato
        assert svc.atendimento_ativo(db_session, contato) is None
        mais_recente = svc.atendimento_mais_recente(db_session, contato)
        assert mais_recente is not None
        assert mais_recente.id == atendimento.id
    finally:
        _limpar(db_session, telefone)


def test_encerrar_por_conversao(db_session):
    telefone = "5511999983006"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        svc.encerrar_por_conversao(db_session, atendimento.id)
        assert atendimento.status == StatusAtendimento.ENCERRADO
        assert atendimento.motivo_encerramento == MotivoEncerramento.CONCLUIDO_CONVERSAO.value
    finally:
        _limpar(db_session, telefone)
