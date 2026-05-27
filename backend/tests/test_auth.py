"""Tests de autenticación (ADR-0004): hashing, registro/login/logout y cookie.

Usan `anon_client` (sin autenticar) para ejercer el flujo de login desde cero.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.auth import service
from app.config import settings

EMAIL = "fabricante@example.com"
PASSWORD = "contraseña-segura-123"


# ─── hashing de contraseñas ──────────────────────────────────────────────────


def test_hash_password_roundtrips_and_is_salted() -> None:
    h1 = service.hash_password(PASSWORD)
    h2 = service.hash_password(PASSWORD)
    assert h1.startswith("scrypt$")
    assert h1 != h2  # salt aleatorio por hash
    assert PASSWORD not in h1  # nunca la contraseña en claro
    assert service.verify_password(PASSWORD, h1)
    assert service.verify_password(PASSWORD, h2)


def test_verify_password_rejects_wrong_and_malformed() -> None:
    h = service.hash_password(PASSWORD)
    assert not service.verify_password("otra-cosa", h)
    assert not service.verify_password(PASSWORD, "no-es-un-hash")
    assert not service.verify_password(PASSWORD, "bcrypt$x$y")


# ─── registro / login ───────────────────────────────────────────────────────


def test_register_sets_httponly_cookie_and_returns_user(anon_client: TestClient) -> None:
    r = anon_client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == EMAIL
    assert "password" not in body and "password_hash" not in body
    set_cookie = r.headers.get("set-cookie", "")
    assert settings.auth_cookie_name in set_cookie
    assert "httponly" in set_cookie.lower()


def test_register_normalizes_email_and_blocks_duplicates(anon_client: TestClient) -> None:
    assert anon_client.post(
        "/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD}
    ).status_code == 201
    # Mismo email con otra capitalización/espacios → conflicto (normalizado).
    r = anon_client.post(
        "/api/v1/auth/register", json={"email": f"  {EMAIL.upper()} ", "password": PASSWORD}
    )
    assert r.status_code == 409


def test_register_rejects_invalid_email_and_short_password(anon_client: TestClient) -> None:
    assert anon_client.post(
        "/api/v1/auth/register", json={"email": "sin-arroba", "password": PASSWORD}
    ).status_code == 422
    assert anon_client.post(
        "/api/v1/auth/register", json={"email": EMAIL, "password": "corta"}
    ).status_code == 422


def test_register_disabled_returns_403(anon_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "allow_registration", False)
    r = anon_client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 403


def test_login_valid_and_invalid(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    anon_client.post("/api/v1/auth/logout")

    ok = anon_client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert ok.status_code == 200

    bad = anon_client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "mal"})
    assert bad.status_code == 401
    # Email inexistente devuelve el MISMO 401 genérico (no oráculo de existencia).
    nope = anon_client.post(
        "/api/v1/auth/login", json={"email": "noexiste@example.com", "password": PASSWORD}
    )
    assert nope.status_code == 401


# ─── /me, sesión y logout ────────────────────────────────────────────────────


def test_me_requires_authentication(anon_client: TestClient) -> None:
    assert anon_client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_user_when_authenticated(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    r = anon_client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


def test_logout_revokes_session(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert anon_client.get("/api/v1/auth/me").status_code == 200

    assert anon_client.post("/api/v1/auth/logout").status_code == 204
    # Tras logout la cookie ya no resuelve a un usuario.
    assert anon_client.get("/api/v1/auth/me").status_code == 401


def test_tampered_cookie_is_rejected(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    anon_client.cookies.set(settings.auth_cookie_name, "token-inventado")
    assert anon_client.get("/api/v1/auth/me").status_code == 401


# ─── el wizard exige login ───────────────────────────────────────────────────


def test_create_session_requires_login(anon_client: TestClient) -> None:
    r = anon_client.post("/api/v1/sessions", json={"description": "x" * 30})
    assert r.status_code == 401


def test_list_sessions_requires_login(anon_client: TestClient) -> None:
    assert anon_client.get("/api/v1/sessions").status_code == 401
