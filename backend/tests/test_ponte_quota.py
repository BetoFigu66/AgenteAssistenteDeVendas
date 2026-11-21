"""Trava de quota da ponte reports → goals (`scripts/ponte_reports_goals.py`).

O ritmo proporcional: com reinício no sábado 10:00 e expediente 8h-18h, a semana tem 70
horas úteis e cada hora útil decorrida soma 1/70 ao uso que a ponte aceita.
"""

from datetime import datetime, timedelta, timezone

import pytest

from scripts import ponte_reports_goals as ponte

BRT = timezone(timedelta(hours=-3))
REINICIO = datetime(2026, 11, 28, 10, 0, tzinfo=BRT)  # sábado
INICIO = REINICIO - timedelta(days=7)


def test_semana_tem_70_horas_uteis():
    assert ponte.horas_uteis(INICIO, REINICIO) == 70


@pytest.mark.parametrize(
    "agora,horas",
    [
        (datetime(2026, 11, 21, 10, 0, tzinfo=BRT), 0),  # no reinício
        (datetime(2026, 11, 21, 12, 30, tzinfo=BRT), 2.5),
        (datetime(2026, 11, 21, 23, 0, tzinfo=BRT), 8),  # noite de sábado: parou em 18h
        (datetime(2026, 11, 22, 7, 59, tzinfo=BRT), 8),  # madrugada de domingo não soma
        (datetime(2026, 11, 22, 18, 0, tzinfo=BRT), 18),  # domingo inteiro
        (datetime(2026, 11, 27, 18, 0, tzinfo=BRT), 68),  # sexta à noite
        (REINICIO, 70),
    ],
)
def test_uso_esperado_soma_1_70_por_hora_util(agora, horas):
    assert ponte.uso_esperado(agora, REINICIO) == pytest.approx(horas / 70)


def test_quota_permite_compara_com_nivel(monkeypatch):
    agora = datetime(2026, 11, 22, 18, 0, tzinfo=BRT)  # 18/70 ≈ 25,7%

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr(ponte, "datetime", Relogio)
    monkeypatch.setattr(ponte, "ler_quota", lambda repo: (25.0, REINICIO))
    assert ponte.quota_permite(None, 1.0) is True
    assert ponte.quota_permite(None, 0.9) is False  # limite 23,1%


def test_quota_ilegivel_nao_despacha(monkeypatch):
    def falha(repo):
        raise RuntimeError("sem token")

    monkeypatch.setattr(ponte, "ler_quota", falha)
    assert ponte.quota_permite(None, 1.0) is False
