"""Testes do ParametroService (REQ-016 T-A8)."""

from unittest.mock import MagicMock

import pytest

from services.parametro_service import ParametroService, validar_valor_parametro


def test_set_int_rejeita_valor_menor_que_minimo():
    svc = ParametroService(MagicMock())
    with pytest.raises(ValueError, match=">= 1"):
        svc.set_int("janela_continuacao_atendimento_horas", 0)


def test_validar_valor_parametro_janela_minimo():
    assert validar_valor_parametro("janela_continuacao_atendimento_horas", "24") == "24"
    with pytest.raises(ValueError, match=">= 1"):
        validar_valor_parametro("janela_continuacao_atendimento_horas", "0")


def test_validar_valor_parametro_float_0_1():
    assert validar_valor_parametro("qa_fulltext_responde_min", "0.30") == "0.30"
    with pytest.raises(ValueError, match="0.0 e 1.0"):
        validar_valor_parametro("qa_fulltext_responde_min", "1.5")
