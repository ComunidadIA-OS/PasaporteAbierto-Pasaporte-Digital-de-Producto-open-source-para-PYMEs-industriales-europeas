"""Fixtures compartidas para los tests de FastAPI.

Las pruebas que tocan la BD usan `client` (TestClient con dependencia
`get_session` reemplazada por un engine SQLite efímero por test).

Reutilizable por Persona A y Persona B — añadir nuevas fixtures aquí
es seguro, modificar las existentes requiere PR conjunto.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app

# Importa modelos para registrar metadata en SQLModel.
from app.models import (  # noqa: F401
    audit_log,
    chat_messages,
    documents,
    extracted_fields,
    published_dpps,
    sessions,
)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """TestClient con BD SQLite aislada por test."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def _override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
