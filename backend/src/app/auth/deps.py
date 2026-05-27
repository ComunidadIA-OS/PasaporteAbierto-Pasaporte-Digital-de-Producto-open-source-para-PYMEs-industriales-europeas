"""Dependencias FastAPI de autenticación y helpers de cookie de sesión.

`get_current_user` exige login (401 si no hay sesión válida); `get_optional_user`
devuelve el usuario o None sin bloquear. Ambos leen el token de la cookie
`httpOnly` y lo resuelven contra `auth_sessions`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session

from app.auth import service
from app.config import settings
from app.db.session import get_session
from app.models.auth import User

DbSession = Annotated[Session, Depends(get_session)]


def _read_token(request: Request) -> str | None:
    return request.cookies.get(settings.auth_cookie_name)


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=raw_token,
        max_age=settings.auth_session_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


def get_optional_user(request: Request, db: DbSession) -> User | None:
    return service.resolve_session(db, _read_token(request))


def get_current_user(request: Request, db: DbSession) -> User:
    user = service.resolve_session(db, _read_token(request))
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated["User | None", Depends(get_optional_user)]
