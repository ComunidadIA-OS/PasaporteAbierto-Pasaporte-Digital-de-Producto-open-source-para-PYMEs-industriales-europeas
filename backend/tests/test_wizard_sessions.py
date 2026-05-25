"""Tests de los endpoints reales del wizard (POST/GET/PATCH /sessions).

Cubre F4-01 — los stubs viven en `wizard.py` y se cubrirán cuando dejen
de ser stubs (F3-01, F3-03, etc.).
"""

from fastapi.testclient import TestClient

DESCRIPTION = "Batería industrial recargable de Li-ion 5 kWh para almacenamiento residencial"


def _create_session(client: TestClient) -> str:
    r = client.post("/api/v1/sessions", json={"description": DESCRIPTION})
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


def test_create_session_persists_and_starts_at_step_1(client: TestClient) -> None:
    sid = _create_session(client)
    r = client.get(f"/api/v1/sessions/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == sid
    assert body["current_step"] == 1
    assert body["description"] == DESCRIPTION


def test_get_session_returns_404_for_unknown_id(client: TestClient) -> None:
    r = client.get("/api/v1/sessions/does-not-exist")
    assert r.status_code == 404
    assert r.json()["detail"] == "session_not_found"


def test_patch_progress_updates_step(client: TestClient) -> None:
    sid = _create_session(client)
    r = client.patch(f"/api/v1/sessions/{sid}", json={"step": 3})
    assert r.status_code == 200
    assert r.json()["current_step"] == 3

    # Releer confirma persistencia
    r2 = client.get(f"/api/v1/sessions/{sid}")
    assert r2.json()["current_step"] == 3


def test_patch_progress_shallow_merges_bom(client: TestClient) -> None:
    """Enviar `bom` con una clave no debe borrar las demás."""
    sid = _create_session(client)
    client.patch(f"/api/v1/sessions/{sid}", json={"bom": {"capacity_nominal": 5000}})
    client.patch(f"/api/v1/sessions/{sid}", json={"bom": {"cycle_life": 1000}})

    r = client.get(f"/api/v1/sessions/{sid}")
    bom = r.json()["bom"]
    assert bom == {"capacity_nominal": 5000, "cycle_life": 1000}


def test_patch_progress_rejects_step_out_of_range(client: TestClient) -> None:
    sid = _create_session(client)
    r = client.patch(f"/api/v1/sessions/{sid}", json={"step": 8})
    assert r.status_code == 422

    r = client.patch(f"/api/v1/sessions/{sid}", json={"step": 0})
    assert r.status_code == 422


def test_patch_progress_returns_404_for_unknown_id(client: TestClient) -> None:
    r = client.patch("/api/v1/sessions/does-not-exist", json={"step": 2})
    assert r.status_code == 404


def test_patch_empty_body_is_idempotent_noop(client: TestClient) -> None:
    """PATCH sin campos no debe romper ni alterar nada."""
    sid = _create_session(client)
    before = client.get(f"/api/v1/sessions/{sid}").json()

    r = client.patch(f"/api/v1/sessions/{sid}", json={})
    assert r.status_code == 200

    after = client.get(f"/api/v1/sessions/{sid}").json()
    assert after["current_step"] == before["current_step"]
    assert after["bom"] == before["bom"]
    assert after["description"] == before["description"]


def test_create_session_rejects_too_short_description(client: TestClient) -> None:
    """El schema exige min_length=20 para forzar texto significativo."""
    r = client.post("/api/v1/sessions", json={"description": "corto"})
    assert r.status_code == 422
