"""Helpers de fecha/hora del proyecto.

`utcnow()` reemplaza el `datetime.utcnow()` deprecado en Python 3.12+ por la
forma moderna con timezone explícita (`datetime.now(timezone.utc)`). Devuelve
un datetime timezone-aware en UTC, no un naive datetime.

Se usa como `default_factory` en los modelos SQLModel del proyecto.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Devuelve un datetime UTC timezone-aware.

    Equivalente moderno a `datetime.utcnow()` (que está deprecado en Python
    3.12+ y emite `DeprecationWarning` porque devuelve un naive datetime
    sin información de zona).
    """
    return datetime.now(UTC)
