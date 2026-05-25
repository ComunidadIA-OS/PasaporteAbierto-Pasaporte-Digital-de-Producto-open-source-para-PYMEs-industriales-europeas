"""Tests del endpoint POST /sessions/{id}/classify (F3-01).

Mockea `run_classifier` para aislar el endpoint de la lógica IA. La
calidad del clasificador está cubierta en `test_classifier_agent.py`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.classifier import ClassificationResult

DESCRIPTION = "Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial"


def _create_session(client: TestClient) -> str:
    r = client.post("/api/v1/sessions", json={"description": DESCRIPTION})
    return r.json()["session_id"]


def _patch_classifier(monkeypatch: pytest.MonkeyPatch, result: ClassificationResult) -> None:
    monkeypatch.setattr("app.api.v1.wizard.run_classifier", lambda _desc: result)


def test_classify_persists_and_returns_full_response(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_classifier(
        monkeypatch,
        ClassificationResult(
            sector="batteries",
            plugin="batteries",
            confidence=0.92,
            citation_regulation="Reglamento UE 2023/1542",
            citation_article="Art. 77",
            citation_url="https://eur-lex.europa.eu/eli/reg/2023/1542",
            requires_review=False,
        ),
    )

    sid = _create_session(client)
    r = client.post(f"/api/v1/sessions/{sid}/classify")
    assert r.status_code == 200

    body = r.json()
    assert body["sector"] == "batteries"
    assert body["plugin"] == "batteries"
    assert body["confidence"] == pytest.approx(0.92)
    assert body["requires_review"] is False
    assert body["citation"]["regulation"] == "Reglamento UE 2023/1542"
    assert body["citation"]["article"] == "Art. 77"

    # Persistencia: GET devuelve el sector clasificado.
    state = client.get(f"/api/v1/sessions/{sid}").json()
    assert state["sector"] == "batteries"
    assert state["plugin"] == "batteries"
    assert state["classification_confidence"] == pytest.approx(0.92)


def test_classify_returns_no_citation_for_unknown_sector(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_classifier(
        monkeypatch,
        ClassificationResult(
            sector="unknown",
            plugin="unknown",
            confidence=0.0,
            citation_regulation="N/A",
            citation_article="sector no soportado",
            citation_url=None,
            requires_review=True,
        ),
    )

    sid = _create_session(client)
    r = client.post(f"/api/v1/sessions/{sid}/classify")
    assert r.status_code == 200
    body = r.json()
    assert body["sector"] == "unknown"
    assert body["citation"] is None
    assert body["requires_review"] is True


def test_classify_returns_404_for_unknown_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.api.v1.wizard.run_classifier",
        lambda _desc: pytest.fail("run_classifier no debería llamarse"),
    )

    r = client.post("/api/v1/sessions/does-not-exist/classify")
    assert r.status_code == 404


def test_classify_no_longer_marks_x_stub_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regresión: tras F3-01 el endpoint deja de ser stub."""
    _patch_classifier(
        monkeypatch,
        ClassificationResult(
            sector="batteries",
            plugin="batteries",
            confidence=0.9,
            citation_regulation="Reglamento UE 2023/1542",
            citation_article="Art. 77",
            citation_url=None,
            requires_review=False,
        ),
    )

    sid = _create_session(client)
    r = client.post(f"/api/v1/sessions/{sid}/classify")
    assert r.headers.get("X-Stub") is None
