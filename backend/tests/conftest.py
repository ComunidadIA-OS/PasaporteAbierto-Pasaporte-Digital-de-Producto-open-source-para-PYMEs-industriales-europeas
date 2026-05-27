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
    auth,
    chat_messages,
    documents,
    extracted_fields,
    published_dpps,
    sessions,
)

# Credenciales del usuario por defecto que autentica el fixture `client`. Desde
# que el login es obligatorio (ADR-0004), casi todos los endpoints del wizard y
# del chat exigen sesión iniciada; autenticar aquí mantiene verdes los tests
# que ya existían sin tener que tocar cada uno.
DEFAULT_TEST_EMAIL = "tester@example.com"
DEFAULT_TEST_PASSWORD = "test-password-123"


def authenticate(client: TestClient, email: str = DEFAULT_TEST_EMAIL) -> None:
    """Registra (o inicia sesión si ya existe) y deja la cookie en el client."""
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": DEFAULT_TEST_PASSWORD},
    )
    if r.status_code == 409:  # email ya registrado en esta BD efímera
        r = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": DEFAULT_TEST_PASSWORD},
        )
    assert r.status_code in (200, 201), r.text


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """TestClient con BD SQLite aislada por test y un usuario ya autenticado."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def _override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        test_client = TestClient(app)
        authenticate(test_client)
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anon_client(tmp_path: Path) -> Iterator[TestClient]:
    """Como `client` pero SIN autenticar — para tests de auth/propiedad."""
    db_path = tmp_path / "anon.db"
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
