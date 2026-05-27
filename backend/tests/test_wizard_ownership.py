"""Aislamiento de sesiones entre usuarios (ADR-0004, propiedad blanda).

Un usuario no puede ver, continuar ni chatear sobre la sesión de otro aunque
conozca su `session_id` opaco. Antes del login, el ID bastaba para acceder.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import authenticate

DESCRIPTION = "Batería industrial Li-ion 5 kWh para almacenamiento residencial fijo."


@pytest.fixture
def two_users(anon_client: TestClient) -> tuple[TestClient, TestClient]:
    """Dos clients autenticados como usuarios distintos sobre la MISMA BD.

    `anon_client` deja activo el override de `get_session`; un segundo
    `TestClient(app)` comparte ese override (mismo engine) pero con su propio
    tarro de cookies, así representa a otro usuario.
    """
    user_a = anon_client
    authenticate(user_a, email="a@example.com")
    user_b = TestClient(app)
    authenticate(user_b, email="b@example.com")
    return user_a, user_b


def _create(client: TestClient) -> str:
    r = client.post("/api/v1/sessions", json={"description": DESCRIPTION})
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


def test_other_user_cannot_read_session(two_users) -> None:
    user_a, user_b = two_users
    sid = _create(user_a)

    assert user_a.get(f"/api/v1/sessions/{sid}").status_code == 200
    # B conoce el id pero no es suyo → 404 (no confirma ni que exista).
    assert user_b.get(f"/api/v1/sessions/{sid}").status_code == 404


def test_other_user_cannot_mutate_session(two_users) -> None:
    user_a, user_b = two_users
    sid = _create(user_a)
    assert user_b.patch(f"/api/v1/sessions/{sid}", json={"step": 3}).status_code == 404


def test_other_user_cannot_chat_or_read_history(two_users) -> None:
    user_a, user_b = two_users
    sid = _create(user_a)
    assert (
        user_b.post("/api/v1/chat", json={"session_id": sid, "message": "hola"}).status_code == 404
    )
    assert user_b.get(f"/api/v1/sessions/{sid}/chat").status_code == 404


def test_list_sessions_is_scoped_to_owner(two_users) -> None:
    user_a, user_b = two_users
    sid_a = _create(user_a)
    sid_b = _create(user_b)

    ids_a = {s["session_id"] for s in user_a.get("/api/v1/sessions").json()["sessions"]}
    ids_b = {s["session_id"] for s in user_b.get("/api/v1/sessions").json()["sessions"]}

    assert sid_a in ids_a and sid_b not in ids_a
    assert sid_b in ids_b and sid_a not in ids_b


def test_list_sessions_summary_flags(two_users) -> None:
    user_a, _ = two_users
    sid = _create(user_a)
    sessions = user_a.get("/api/v1/sessions").json()["sessions"]
    summary = next(s for s in sessions if s["session_id"] == sid)
    assert summary["description"] == DESCRIPTION
    assert summary["current_step"] == 1
    assert summary["has_chat"] is False
    assert summary["published"] is False
