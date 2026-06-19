"""Utilitários de data/hora — armazenamento UTC explícito."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

UTC = timezone.utc


def utc_now() -> datetime:
    """Retorna datetime timezone-aware em UTC (substituto de datetime.utcnow)."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normaliza datetime naive (legado) ou aware para UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def serialize_utc_datetime(value: Optional[datetime]) -> Optional[str]:
    """Serializa datetime UTC para ISO 8601 com sufixo Z (compatível com JavaScript)."""
    if value is None:
        return None
    normalized = ensure_utc(value)
    text = normalized.isoformat()
    if text.endswith("+00:00"):
        return text[:-6] + "Z"
    return text
