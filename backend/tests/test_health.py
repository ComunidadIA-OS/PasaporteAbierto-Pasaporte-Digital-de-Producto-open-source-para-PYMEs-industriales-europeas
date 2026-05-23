from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_version_model_and_backend():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
    assert "model" in payload
    assert "backend" in payload


def test_health_reflects_env_backend(monkeypatch):
    """Cambiar settings.model_backend en runtime debe propagarse al endpoint."""
    from app.config import settings

    monkeypatch.setattr(settings, "model_backend", "anthropic:claude-opus-4")
    response = client.get("/api/v1/health")
    payload = response.json()
    assert payload["backend"] == "anthropic:claude-opus-4"
    assert payload["model"] == "claude-opus-4"
