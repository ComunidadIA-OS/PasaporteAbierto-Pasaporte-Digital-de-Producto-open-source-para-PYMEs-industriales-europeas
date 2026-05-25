"""Audit log con hash chain (CLAUDE.md §invariantes).

Cada operación significativa del wizard (`classify_override`, `verify`,
`publish`, `sign`) añade una entrada a `audit_log` con:

    content_hash = sha256(prev_hash || operation || canonical_json(payload))

`prev_hash` es el `content_hash` de la entrada inmediatamente anterior
(null sólo en la primera). Re-serializamos el payload con `sort_keys=True`
y separadores compactos para que la verificación posterior produzca los
mismos bytes.

API pública:

    append_entry(db, *, operation, payload) -> AuditLogEntry
    verify_chain(db) -> ChainStatus

El endpoint `GET /audit/verify` (F6) usa `verify_chain`. F4-02, F3-03 y
F4-06 usan `append_entry` para registrar override / verify / publish.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, desc, select

from app.models.audit_log import AuditLogEntry

# Lock global del módulo para serializar SELECT-último + INSERT del audit log.
# La invariante de hash chain exige que `prev_hash` de la entrada N apunte al
# `content_hash` de N-1; si dos requests concurrentes leen el mismo "último"
# antes de que ninguno haga flush, las dos persisten con el mismo `prev_hash`
# y `verify_chain` reporta una cadena corrupta sobre datos generados por el
# propio sistema. SQLite serializa transacciones pero no las dos operaciones
# entre sí desde la perspectiva del caller. Single-process es suficiente:
# alcance del hackathon (CLAUDE.md "una instancia = un fabricante PYME").
_AUDIT_LOCK = threading.Lock()


def _canonical(payload: dict[str, Any]) -> bytes:
    """Serialización determinista del payload para que el hash sea reproducible.

    sort_keys=True y separadores compactos garantizan que dos diccionarios
    con el mismo contenido produzcan los mismos bytes. `default=str` cubre
    tipos como datetime/UUID que aparezcan en payloads.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def _compute_hash(prev_hash: str | None, operation: str, payload: dict[str, Any]) -> str:
    h = hashlib.sha256()
    if prev_hash is not None:
        h.update(prev_hash.encode())
    h.update(operation.encode())
    h.update(_canonical(payload))
    return h.hexdigest()


def append_entry(
    db: Session,
    *,
    operation: str,
    payload: dict[str, Any],
) -> AuditLogEntry:
    """Añade una entrada al audit log encadenada con la anterior.

    No hace commit — el caller decide cuándo confirmar. Sí hace `flush()`
    para asignar el `id` autoincrement antes de devolver.

    El lock global `_AUDIT_LOCK` serializa SELECT-último + INSERT entre los
    distintos workers del proceso para preservar la cadena (ver comentario
    arriba). El flush ocurre dentro del lock para que el siguiente caller
    vea esta entrada en su SELECT.
    """
    with _AUDIT_LOCK:
        last = db.exec(select(AuditLogEntry).order_by(desc(AuditLogEntry.id)).limit(1)).first()
        prev_hash = last.content_hash if last else None
        content_hash = _compute_hash(prev_hash, operation, payload)

        entry = AuditLogEntry(
            prev_hash=prev_hash,
            content_hash=content_hash,
            operation=operation,
            payload=payload,
        )
        db.add(entry)
        db.flush()
        return entry


@dataclass(frozen=True)
class ChainStatus:
    valid: bool
    entries_checked: int
    first_invalid_id: int | None = None
    reason: str | None = None


def verify_chain(db: Session) -> ChainStatus:
    """Recorre el audit_log en orden de id y verifica la cadena."""
    entries = db.exec(select(AuditLogEntry).order_by(AuditLogEntry.id)).all()
    prev_hash: str | None = None

    for i, entry in enumerate(entries, start=1):
        if entry.prev_hash != prev_hash:
            return ChainStatus(
                valid=False,
                entries_checked=i,
                first_invalid_id=entry.id,
                reason="prev_hash no coincide con la anterior",
            )
        expected = _compute_hash(prev_hash, entry.operation, entry.payload or {})
        if expected != entry.content_hash:
            return ChainStatus(
                valid=False,
                entries_checked=i,
                first_invalid_id=entry.id,
                reason="content_hash recalculado no coincide (payload alterado)",
            )
        prev_hash = entry.content_hash

    return ChainStatus(valid=True, entries_checked=len(entries))


__all__ = ["ChainStatus", "append_entry", "verify_chain"]
