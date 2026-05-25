"""Tests del endpoint GET /sessions/{id}/verify (F3-03)."""

from __future__ import annotations

from fastapi.testclient import TestClient

DESCRIPTION = "Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial"


def _create_classified(client: TestClient) -> str:
    sid = client.post("/api/v1/sessions", json={"description": DESCRIPTION}).json()["session_id"]
    client.post(
        f"/api/v1/sessions/{sid}/classify/override",
        json={"sector": "batteries", "plugin": "batteries", "reason": "test setup"},
    )
    return sid


def test_verify_empty_session_blocks_publish(client: TestClient) -> None:
    sid = _create_classified(client)
    r = client.get(f"/api/v1/sessions/{sid}/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["can_publish"] is False
    assert body["completeness"] == 0.0
    assert len(body["missing_fields"]) > 0
    # Cada missing trae cita.
    first = body["missing_fields"][0]
    assert first["citation"]["regulation"]
    assert first["citation"]["article"]


def test_verify_returns_404_for_unknown_session(client: TestClient) -> None:
    r = client.get("/api/v1/sessions/nope/verify")
    assert r.status_code == 404


def test_verify_returns_400_without_plugin(client: TestClient) -> None:
    sid = client.post("/api/v1/sessions", json={"description": DESCRIPTION}).json()["session_id"]
    r = client.get(f"/api/v1/sessions/{sid}/verify")
    assert r.status_code == 400


def test_verify_reflects_partial_bom(client: TestClient) -> None:
    sid = _create_classified(client)
    client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={
            "fields": {
                "battery_passport_unique_id": "ABC-12345",
                "battery_mass_kg": 25.5,
                "battery_chemistry": "li_ion",
            }
        },
    )
    body = client.get(f"/api/v1/sessions/{sid}/verify").json()
    assert body["can_publish"] is False  # aún faltan muchos required
    assert 0 < body["completeness"] < 1


def test_verify_is_no_longer_stub(client: TestClient) -> None:
    sid = _create_classified(client)
    r = client.get(f"/api/v1/sessions/{sid}/verify")
    assert r.headers.get("X-Stub") is None
