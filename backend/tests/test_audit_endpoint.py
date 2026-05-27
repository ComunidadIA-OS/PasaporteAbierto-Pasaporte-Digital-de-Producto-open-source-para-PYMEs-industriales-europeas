"""Tests del endpoint GET /api/v1/audit/verify (F5-04 CA #2).

Las pruebas unitarias de `verify_chain` viven en `test_audit.py`. Aquí
verificamos el contrato HTTP y el caso de manipulación manual desde SQL
exigido por el criterio de aceptación 2 del ticket F5-04.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.audit import append_entry
from app.db.session import get_session
from app.main import app
from app.models import (  # noqa: F401  (registrar metadata)
    audit_log,
    chat_messages,
    documents,
    extracted_fields,
    published_dpps,
    sessions,
)


@pytest.fixture
def engine_and_client(tmp_path: Path) -> Iterator[tuple[object, TestClient]]:
    """TestClient + engine compartido para poder insertar/manipular desde fuera."""
    db_path = tmp_path / "audit.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def _override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield engine, TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_empty_chain_is_ok(engine_and_client: tuple[object, TestClient]) -> None:
    _, client = engine_and_client
    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"ok": True, "total_rows": 0, "broken_at": None, "reason": None}


def test_five_entries_chain_is_ok(engine_and_client: tuple[object, TestClient]) -> None:
    """5 filas insertadas vía wrapper → ok=true, total_rows=5."""
    engine, client = engine_and_client
    with Session(engine) as session:
        for i in range(5):
            append_entry(session, operation="verify", payload={"i": i})
        session.commit()

    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["total_rows"] == 5
    assert body["broken_at"] is None


def test_tampering_row_three_breaks_chain(
    engine_and_client: tuple[object, TestClient],
) -> None:
    """CA #2: manipular fila 3 por SQL directo ⇒ ok=false, broken_at=<id fila 3>.

    El contrato del endpoint usa `broken_at = id` de la fila donde se rompe
    la cadena, no el ordinal. En este test la tercera fila tiene `id=3`,
    así que ambos coinciden.
    """
    engine, client = engine_and_client
    with Session(engine) as session:
        ids = []
        for i in range(5):
            entry = append_entry(session, operation="verify", payload={"i": i})
            session.flush()
            ids.append(entry.id)
        session.commit()

    third_id = ids[2]

    # Manipulación SQL directa: cambiamos el payload sin recalcular content_hash.
    tampered_payload = json.dumps({"i": 999})
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE audit_log SET payload = :p WHERE id = :id"),
            {"p": tampered_payload, "id": third_id},
        )

    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["broken_at"] == third_id
    assert body["reason"] is not None
