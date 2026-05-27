"""Endpoint público de verificación del audit log (F5-04 CA #2).

`GET /api/v1/audit/verify` recorre la cadena completa y devuelve si está
íntegra o, en caso contrario, el `id` de la primera fila donde se rompe.

La lógica de verificación vive en `app.audit.verify_chain`; este módulo
sólo adapta el resultado al contrato del ticket:

    { "ok": bool, "broken_at": int | None, "total_rows": int, "reason": str | None }

`broken_at` es `null` cuando la cadena está sana.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.audit import verify_chain
from app.db.session import get_session

router = APIRouter(prefix="/audit", tags=["audit"])

DbSession = Annotated[Session, Depends(get_session)]


class AuditVerifyResponse(BaseModel):
    ok: bool
    total_rows: int
    broken_at: int | None = None
    reason: str | None = None


@router.get("/verify", response_model=AuditVerifyResponse)
def verify_audit_chain(db: DbSession) -> AuditVerifyResponse:
    status = verify_chain(db)
    return AuditVerifyResponse(
        ok=status.valid,
        total_rows=status.entries_checked,
        broken_at=status.first_invalid_id,
        reason=status.reason,
    )
