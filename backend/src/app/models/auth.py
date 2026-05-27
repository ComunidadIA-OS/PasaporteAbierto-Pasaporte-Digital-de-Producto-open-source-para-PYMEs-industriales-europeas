from datetime import datetime

from sqlmodel import Field, SQLModel

from app.time_utils import utcnow


class User(SQLModel, table=True):
    """Cuenta de la instancia (un fabricante PYME, varios operarios).

    El login es la pieza que liga las sesiones del wizard y el chat a una
    persona, de modo que al volver a entrar se recuperan las conversaciones y
    los DPP empezados (criterio del ticket de login). No es multi-tenant: no
    hay aislamiento por organización, solo por usuario dentro de la misma
    instancia auto-hospedada — ver ADR-0004.

    `password_hash` guarda el digest scrypt con sus parámetros embebidos
    (ver `app.auth.service`); nunca la contraseña en claro.
    """

    __tablename__ = "users"

    id: str = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class AuthSession(SQLModel, table=True):
    """Sesión de login server-side. Canal de autenticación, no del wizard.

    La cookie del navegador transporta el token en claro (`httpOnly`+`Secure`);
    en BD solo se guarda su SHA-256 (`token_hash`), de forma que una fuga de la
    BD no expone sesiones vivas reutilizables. El estado de login vive aquí, no
    en `localStorage` del cliente (requisito de seguridad del ticket).
    """

    __tablename__ = "auth_sessions"

    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(index=True)
    last_seen_at: datetime = Field(default_factory=utcnow)
