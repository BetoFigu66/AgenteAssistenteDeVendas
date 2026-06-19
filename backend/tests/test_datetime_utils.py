from datetime import datetime, timezone

from utils.datetime_utils import ensure_utc, serialize_utc_datetime, utc_now


def test_utc_now_is_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_serialize_naive_as_utc_with_z_suffix():
    naive = datetime(2026, 6, 15, 19, 34, 44, 641735)
    assert serialize_utc_datetime(naive) == "2026-06-15T19:34:44.641735Z"


def test_serialize_aware_utc():
    aware = datetime(2026, 6, 15, 16, 34, 44, tzinfo=timezone.utc)
    assert serialize_utc_datetime(aware) == "2026-06-15T16:34:44Z"


def test_ensure_utc_from_naive():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert ensure_utc(naive).tzinfo == timezone.utc
