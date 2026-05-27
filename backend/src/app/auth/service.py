"""Lógica de autenticación: hashing de contraseñas y sesiones server-side.

Decisiones (ADR-0004):
  - **scrypt de la stdlib** (`hashlib.scrypt`) para el hash de contraseña: KDF
    memory-hard, sin dependencias nuevas (descartado argon2/bcrypt para no
    añadir wheels con build C al lock de `uv`). El digest embebe sus parámetros
    (`scrypt$n$r$p$salt$hash`) para poder subir el coste en el futuro sin
    invalidar los hashes existentes.
  - **Sesión server-side, no JWT**: el token vive en una fila de `auth_sessions`
    y se puede revocar (logout, expiración). La cookie lleva el token en claro;
    en BD solo se guarda su SHA-256, así una fuga de BD no entrega sesiones
    reutilizables.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, timedelta

from sqlmodel import Session, select

from app.models.auth import AuthSession, User
from app.time_utils import utcnow

# Parámetros scrypt. n=2^14 → ~16 MB por hash: caro para fuerza bruta, barato
# para un login interactivo. Subirlos solo afecta a hashes nuevos.
_SCRYPT_N = 1 << 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SALT_BYTES = 16


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.encode("ascii"))


def hash_password(password: str) -> str:
    """Devuelve `scrypt$n$r$p$salt_b64$hash_b64` (salt aleatorio por contraseña)."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Comprueba `password` contra un digest generado por `hash_password`.

    Reconstruye el hash con los parámetros embebidos y compara en tiempo
    constante. Cualquier digest malformado devuelve False sin lanzar.
    """
    try:
        scheme, n_s, r_s, p_s, salt_s, hash_s = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = _unb64(hash_s)
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt_s),
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.exec(select(User).where(User.email == normalize_email(email))).first()


def create_user(db: Session, email: str, password: str) -> User:
    """Crea un usuario. Lanza `ValueError` si el email ya existe.

    El caller (router) traduce el ValueError a un 409 con mensaje genérico
    para no convertir el registro en un oráculo de emails existentes.
    """
    norm = normalize_email(email)
    if get_user_by_email(db, norm) is not None:
        raise ValueError("email_taken")
    user = User(id=str(uuid.uuid4()), email=norm, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Devuelve el usuario si las credenciales son válidas, si no None.

    Verifica el hash incluso cuando el usuario no existe (con un digest
    descartable) para no filtrar por tiempo qué emails están registrados.
    """
    user = get_user_by_email(db, email)
    if user is None:
        # Trabajo equivalente para mitigar timing oracle de existencia de email.
        verify_password(password, hash_password("dummy"))
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_auth_session(db: Session, user: User, ttl_days: int) -> str:
    """Crea una sesión y devuelve el token en claro (solo se entrega aquí)."""
    raw_token = secrets.token_urlsafe(32)
    row = AuthSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=_token_hash(raw_token),
        expires_at=utcnow() + timedelta(days=ttl_days),
    )
    db.add(row)
    db.commit()
    return raw_token


def resolve_session(db: Session, raw_token: str | None) -> User | None:
    """Resuelve el token de la cookie a un usuario, o None si inválido/expirado.

    Refresca `last_seen_at` en cada acceso válido (telemetría ligera, no
    extiende la expiración). Las sesiones expiradas se eliminan al detectarlas.
    """
    if not raw_token:
        return None
    row = db.exec(
        select(AuthSession).where(AuthSession.token_hash == _token_hash(raw_token))
    ).first()
    if row is None:
        return None
    # SQLite devuelve datetimes naive (sin tz); `utcnow()` es aware. Normalizamos
    # el valor leído a UTC antes de comparar para no mezclar naive y aware.
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= utcnow():
        db.delete(row)
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None:
        return None
    row.last_seen_at = utcnow()
    db.add(row)
    db.commit()
    return user


def revoke_session(db: Session, raw_token: str | None) -> None:
    """Elimina la sesión asociada al token (logout). Idempotente."""
    if not raw_token:
        return
    row = db.exec(
        select(AuthSession).where(AuthSession.token_hash == _token_hash(raw_token))
    ).first()
    if row is not None:
        db.delete(row)
        db.commit()
