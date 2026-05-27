"""Tests de subida y listado de documentos (F4-04)."""

import hashlib
import io

from fastapi.testclient import TestClient

from app.plugins.conditions import evaluate_when

# ---------------------------------------------------------------------------
# evaluate_when (conditions.py)
# ---------------------------------------------------------------------------


class TestEvaluateWhen:
    def test_none_condition_returns_true(self) -> None:
        assert evaluate_when(None, {}) is True

    def test_empty_condition_returns_true(self) -> None:
        assert evaluate_when("", {}) is True

    def test_in_operator_match(self) -> None:
        bom = {"battery_category": "industrial"}
        assert evaluate_when("battery_category in [industrial, ev]", bom) is True

    def test_in_operator_no_match(self) -> None:
        bom = {"battery_category": "portable"}
        assert evaluate_when("battery_category in [industrial, ev]", bom) is False

    def test_arithmetic_comparison(self) -> None:
        bom = {"rated_capacity_ah": 100, "voltage_nominal_v": 48}
        assert evaluate_when("rated_capacity_ah * voltage_nominal_v / 1000 > 2", bom) is True

    def test_arithmetic_comparison_false(self) -> None:
        bom = {"rated_capacity_ah": 1, "voltage_nominal_v": 3.7}
        assert evaluate_when("rated_capacity_ah * voltage_nominal_v / 1000 > 2", bom) is False

    def test_missing_field_returns_true(self) -> None:
        """Si el campo no está en el BOM, precaución: requerir el documento."""
        assert evaluate_when("unknown_field > 5", {}) is True

    def test_chained_comparison(self) -> None:
        bom = {"voltage_min_v": 3.0, "voltage_nominal_v": 3.7, "voltage_max_v": 4.2}
        assert evaluate_when("voltage_min_v <= voltage_nominal_v <= voltage_max_v", bom) is True


# ---------------------------------------------------------------------------
# Upload & dedup (requieren BD vía fixture `client`)
# ---------------------------------------------------------------------------


def _create_batteries_session(client: TestClient) -> str:
    """Crea una sesión y la fuerza a plugin=batteries para tests."""
    resp = client.post(
        "/api/v1/sessions",
        json={"description": "Batería industrial para prueba de documentos"},
    )
    assert resp.status_code == 201
    sid = resp.json()["session_id"]

    # Forzar clasificación manualmente vía PATCH
    # (classify real requiere LLM configurado)
    from app.db.session import get_session
    from app.main import app
    from app.models.sessions import WizardSession

    override_fn = app.dependency_overrides[get_session]
    session_gen = override_fn()
    db = next(session_gen)
    row = db.get(WizardSession, sid)
    assert row is not None
    row.sector = "batteries"
    row.plugin = "batteries"
    db.add(row)
    db.commit()

    return sid


def test_list_documents_returns_plugin_derived_list(client: TestClient) -> None:
    """La lista de documentos requeridos se deriva del plugin, no hardcodeada."""
    sid = _create_batteries_session(client)
    resp = client.get(f"/api/v1/sessions/{sid}/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert "required" in data
    assert "uploaded" in data
    doc_types = [r["doc_type"] for r in data["required"]]
    assert "datasheet" in doc_types
    assert "ce_declaration" in doc_types


def test_upload_document_and_dedup(client: TestClient) -> None:
    """Subir el mismo PDF dos veces no lo duplica (dedup por SHA-256)."""
    sid = _create_batteries_session(client)
    pdf_content = b"%PDF-1.4 fake content for testing"
    expected_hash = hashlib.sha256(pdf_content).hexdigest()

    resp1 = client.post(
        f"/api/v1/sessions/{sid}/documents?doc_type=datasheet",
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["deduplicated"] is False
    assert data1["document"]["sha256"] == expected_hash

    resp2 = client.post(
        f"/api/v1/sessions/{sid}/documents?doc_type=datasheet",
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["deduplicated"] is True
    assert data2["document"]["id"] == data1["document"]["id"]


def test_upload_too_large_file(client: TestClient) -> None:
    """Fichero > 10 MB rechazado con 413."""
    sid = _create_batteries_session(client)
    big_content = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        f"/api/v1/sessions/{sid}/documents?doc_type=datasheet",
        files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
    )
    assert resp.status_code == 413
