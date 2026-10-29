"""Testes do serviço de atendimentos (REQ-016 T-A4)."""

from services import atendimentos as svc


def test_titulo_novo_atendimento_sem_identificacao():
    assert svc._titulo_novo_atendimento() == "Atendimento (sem empresa)"
