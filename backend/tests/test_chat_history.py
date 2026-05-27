"""Tests del histórico del chat persistido por sesión (F3-04 criterio 3).

Verifica:
  - POST /chat persiste user + assistant en chat_messages.
  - GET /sessions/{id}/chat devuelve los mensajes en orden cronológico.
  - El chat NO escribe en el estado del wizard (sessions.progress sin tocar).
  - Sesión inexistente → 404 en ambos endpoints.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import chat as chat_module
from app.chat.agent import ChatResult


@pytest.fixture
def _stub_chat_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sustituye chat_answer por un stub determinista que no llama al LLM."""

    def _fake(message: str, session_context: dict[str, Any] | None = None, idioma: str = "es"):
        return ChatResult(
            answer=f"Respuesta a: {message} [Reglamento UE 2024/1781, Art. 7]",
            citation_regulation="Reglamento UE 2024/1781",
            citation_article="Art. 7",
            citation_url="https://eur-lex.europa.eu/eli/reg/2024/1781/oj",
            fragments=[],
        )

    monkeypatch.setattr(chat_module, "chat_answer", _fake)


def _create_session(client: TestClient) -> str:
    r = client.post(
        "/api/v1/sessions",
        json={"description": "Producto de prueba para test de histórico del chat lateral."},
    )
    assert r.status_code == 201
    return r.json()["session_id"]


def test_chat_history_persists_user_and_assistant(
    client: TestClient, _stub_chat_answer: None
) -> None:
    sid = _create_session(client)

    # Histórico vacío al inicio
    r = client.get(f"/api/v1/sessions/{sid}/chat")
    assert r.status_code == 200
    assert r.json() == {"messages": []}

    # Una llamada al chat persiste user + assistant
    r = client.post(
        "/api/v1/chat",
        json={"session_id": sid, "message": "¿Qué exige el ESPR sobre huella de carbono?"},
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/api/v1/sessions/{sid}/chat")
    assert r.status_code == 200
    messages = r.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert "huella de carbono" in messages[0]["content"]
    assert messages[0]["citation"] is None
    assert messages[1]["role"] == "assistant"
    assert messages[1]["citation"]["regulation"] == "Reglamento UE 2024/1781"
    assert messages[1]["citation"]["article"] == "Art. 7"


def test_chat_history_orders_by_created_at(client: TestClient, _stub_chat_answer: None) -> None:
    sid = _create_session(client)

    for q in ["primera pregunta", "segunda pregunta", "tercera pregunta"]:
        r = client.post("/api/v1/chat", json={"session_id": sid, "message": q})
        assert r.status_code == 200

    r = client.get(f"/api/v1/sessions/{sid}/chat")
    messages = r.json()["messages"]
    # 3 pares (user + assistant), orden cronológico estable
    assert len(messages) == 6
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    assert user_msgs == ["primera pregunta", "segunda pregunta", "tercera pregunta"]


def test_chat_does_not_write_wizard_state(client: TestClient, _stub_chat_answer: None) -> None:
    """El chat NUNCA escribe en sessions.progress ni extracted_fields (CLAUDE.md)."""
    sid = _create_session(client)

    state_before = client.get(f"/api/v1/sessions/{sid}").json()

    client.post("/api/v1/chat", json={"session_id": sid, "message": "una pregunta cualquiera"})

    state_after = client.get(f"/api/v1/sessions/{sid}").json()

    # Estos campos del estado del wizard deben quedar inalterados.
    assert state_after["current_step"] == state_before["current_step"]
    assert state_after["bom"] == state_before["bom"]
    assert state_after["sector"] == state_before["sector"]
    assert state_after["extracted_fields"] == state_before["extracted_fields"]


def test_chat_404_on_unknown_session(client: TestClient, _stub_chat_answer: None) -> None:
    # POST /chat con sesión inexistente
    r = client.post("/api/v1/chat", json={"session_id": "no-existe-123", "message": "hola"})
    assert r.status_code == 404

    # GET /sessions/{id}/chat con sesión inexistente
    r = client.get("/api/v1/sessions/no-existe-123/chat")
    assert r.status_code == 404
