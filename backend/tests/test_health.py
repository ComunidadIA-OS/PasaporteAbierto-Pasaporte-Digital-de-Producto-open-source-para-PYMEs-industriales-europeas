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
    monkeypatch.setenv("MODEL_BACKEND", "ollama:qwen2.5:14b")
    # Reimport settings to pick env up
    from importlib import reload

    from app import config

    reload(config)
    response = client.get("/api/v1/health")
    assert response.json()["backend"] == "ollama:qwen2.5:14b"
