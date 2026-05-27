"""Tests del endpoint PUT /sessions/{id}/bom (F4-03)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from app.db.session import get_session
from app.models.extracted_fields import ExtractedField

DESCRIPTION = "Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial"


def _create_classified_session(client: TestClient, sector: str = "batteries") -> str:
    """Crea sesión + override directo al sector (sin pasar por classifier)."""
    sid = client.post("/api/v1/sessions", json={"description": DESCRIPTION}).json()["session_id"]
    client.post(
        f"/api/v1/sessions/{sid}/classify/override",
        json={
            "sector": sector,
            "plugin": sector,
            "reason": "asignación directa para test de BOM",
        },
    )
    return sid


# ─── GET /plugins/{name} ─────────────────────────────────────────────────────


def test_get_plugin_detail_returns_full_fields(client: TestClient) -> None:
    r = client.get("/api/v1/plugins/batteries")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "batteries"
    assert len(body["fields"]) >= 25  # criterio F1-03
    first = body["fields"][0]
    assert "id" in first
    assert "type" in first
    assert "required" in first
    assert "citation" in first


def test_get_plugin_detail_returns_404_for_unknown(client: TestClient) -> None:
    r = client.get("/api/v1/plugins/aircraft")
    assert r.status_code == 404


# ─── PUT /bom: happy path ────────────────────────────────────────────────────


def test_put_bom_persists_self_declared_fields(client: TestClient) -> None:
    sid = _create_classified_session(client)
    r = client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={
            "fields": {
                "battery_passport_unique_id": "ABC-12345",
                "battery_mass_kg": 25.5,
                "battery_chemistry": "li_ion",
            }
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    # Errors solo de required faltantes (no de los enviados).
    enviado_errors = [e for e in body["errors"] if "requerido" not in e["message"]]
    assert enviado_errors == []

    # Confirma persistencia con provenance correcto.
    db_factory = client.app.dependency_overrides[get_session]  # type: ignore[arg-type]
    db = next(db_factory())
    try:
        rows = db.exec(select(ExtractedField).where(ExtractedField.session_id == sid)).all()
        assert {r.field_id for r in rows} == {
            "battery_passport_unique_id",
            "battery_mass_kg",
            "battery_chemistry",
        }
        assert all(r.provenance == "self_declared" for r in rows)
        assert all(r.confidence == 1.0 for r in rows)
    finally:
        db.close()


def test_put_bom_upsert_does_not_duplicate(client: TestClient) -> None:
    """Re-PUT del mismo field_id actualiza el valor, no inserta un segundo row."""
    sid = _create_classified_session(client)
    client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"battery_mass_kg": 25.0}},
    )
    client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"battery_mass_kg": 30.5}},
    )

    db = next(client.app.dependency_overrides[get_session]())  # type: ignore[arg-type]
    try:
        rows = db.exec(
            select(ExtractedField).where(
                ExtractedField.session_id == sid,
                ExtractedField.field_id == "battery_mass_kg",
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].value == "30.5"
    finally:
        db.close()


# ─── PUT /bom: errores ───────────────────────────────────────────────────────


def test_put_bom_rejects_wrong_type(client: TestClient) -> None:
    sid = _create_classified_session(client)
    r = client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"battery_mass_kg": "not-a-number"}},
    )
    assert r.status_code == 200
    body = r.json()
    field_errors = [e for e in body["errors"] if e["field_id"] == "battery_mass_kg"]
    assert len(field_errors) == 1
    assert "number" in field_errors[0]["message"]
    # accepted=False porque hubo un tipo mal.
    assert body["accepted"] is False


def test_put_bom_rejects_enum_value_outside_allowed(client: TestClient) -> None:
    sid = _create_classified_session(client)
    r = client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"battery_chemistry": "kryptonite"}},
    )
    body = r.json()
    field_errors = [e for e in body["errors"] if e["field_id"] == "battery_chemistry"]
    assert len(field_errors) == 1
    assert "enum" in field_errors[0]["message"]


def test_put_bom_rejects_unknown_field_id(client: TestClient) -> None:
    sid = _create_classified_session(client)
    r = client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"made_up_field": "x"}},
    )
    field_errors = [e for e in r.json()["errors"] if e["field_id"] == "made_up_field"]
    assert any("no definido" in e["message"] for e in field_errors)


def test_put_bom_reports_missing_required_but_accepts(client: TestClient) -> None:
    """Save parcial: si faltan required, los reporta pero el PUT pasa (accepted=True)."""
    sid = _create_classified_session(client)
    r = client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"battery_mass_kg": 25.0}},  # solo un required de muchos
    )
    body = r.json()
    assert body["accepted"] is True  # save parcial permitido
    required_errors = [e for e in body["errors"] if "requerido" in e["message"]]
    assert len(required_errors) > 0


def test_put_bom_returns_400_without_plugin(client: TestClient) -> None:
    """Si la sesión no tiene plugin asignado, no se puede validar el BOM."""
    sid = client.post("/api/v1/sessions", json={"description": DESCRIPTION}).json()["session_id"]
    r = client.put(f"/api/v1/sessions/{sid}/bom", json={"fields": {}})
    assert r.status_code == 400
    assert r.json()["detail"] == "session_has_no_plugin"


def test_put_bom_returns_404_for_unknown_session(client: TestClient) -> None:
    r = client.put("/api/v1/sessions/nope/bom", json={"fields": {}})
    assert r.status_code == 404


def test_put_bom_reflects_values_in_session_state(client: TestClient) -> None:
    """Tras PUT, GET /sessions devuelve el BOM en `bom`."""
    sid = _create_classified_session(client)
    client.put(
        f"/api/v1/sessions/{sid}/bom",
        json={"fields": {"battery_mass_kg": 25.0, "battery_chemistry": "li_ion"}},
    )
    state = client.get(f"/api/v1/sessions/{sid}").json()
    assert state["bom"]["battery_mass_kg"] == 25.0
    assert state["bom"]["battery_chemistry"] == "li_ion"
