"""Endpoints de autenticación (ADR-0004).

  - POST /api/v1/auth/register   alta de cuenta (si `allow_registration`)
  - POST /api/v1/auth/login      inicio de sesión
  - POST /api/v1/auth/logout     cierre de sesión (revoca la sesión server-side)
  - GET  /api/v1/auth/me         identidad del usuario autenticado

El login/registro fija una cookie `httpOnly` con el token de sesión. El cliente
nunca ve el token desde JS (no `localStorage`): el estado de login vive en la
cookie + la tabla `auth_sessions`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session

from app.api.v1.schemas import LoginRequest, RegisterRequest, UserResponse
from app.auth import service
from app.auth.deps import (
    CurrentUser,
    clear_session_cookie,
    get_current_user,
    set_session_cookie,
)
from app.config import settings
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_session)]


def _to_user_response(user) -> UserResponse:  # type: ignore[no-untyped-def]
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


def _start_session(db: Session, response: Response, user) -> None:  # type: ignore[no-untyped-def]
    token = service.create_auth_session(db, user, settings.auth_session_ttl_days)
    set_session_cookie(response, token)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, response: Response, db: DbSession) -> UserResponse:
    """Crea una cuenta e inicia sesión. 403 si el alta está cerrada, 409 si el
    email ya existe (mensaje genérico, sin confirmar más detalle)."""
    if not settings.allow_registration:
        raise HTTPException(status_code=403, detail="registration_disabled")
    if "@" not in body.email or "." not in body.email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="invalid_email")
    try:
        user = service.create_user(db, body.email, body.password)
    except ValueError:
        raise HTTPException(status_code=409, detail="email_taken") from None
    _start_session(db, response, user)
    return _to_user_response(user)


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, response: Response, db: DbSession) -> UserResponse:
    """Inicia sesión. 401 genérico ante credenciales inválidas (no distingue
    email inexistente de contraseña errónea)."""
    user = service.authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    _start_session(db, response, user)
    return _to_user_response(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DbSession) -> Response:
    """Revoca la sesión server-side y borra la cookie. Idempotente."""
    service.revoke_session(db, request.cookies.get(settings.auth_cookie_name))
    clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    """Identidad del usuario autenticado. 401 si no hay sesión válida."""
    return _to_user_response(user)


# Re-export para que el router del wizard reutilice la misma dependencia.
__all__ = ["router", "get_current_user"]
