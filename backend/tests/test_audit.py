"""Tests del audit log con hash chain (F4-02 + futuras operaciones)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.audit import append_entry, verify_chain
from app.models import audit_log  # noqa: F401  (registrar metadata)


@pytest.fixture
def db_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def test_first_entry_has_null_prev_hash(db_session: Session) -> None:
    e = append_entry(db_session, operation="classify_override", payload={"sector": "batteries"})
    db_session.commit()

    assert e.prev_hash is None
    assert len(e.content_hash) == 64  # sha256 hex


def test_second_entry_links_to_first(db_session: Session) -> None:
    e1 = append_entry(db_session, operation="classify_override", payload={"sector": "batteries"})
    e2 = append_entry(db_session, operation="verify", payload={"completeness": 0.9})
    db_session.commit()

    assert e2.prev_hash == e1.content_hash
    assert e2.id > e1.id


def test_chain_remains_valid_across_many_entries(db_session: Session) -> None:
    for i in range(5):
        append_entry(db_session, operation="verify", payload={"i": i})
    db_session.commit()

    status = verify_chain(db_session)
    assert status.valid is True
    assert status.entries_checked == 5


def test_hash_is_deterministic_for_same_input() -> None:
    """Dos payloads con las mismas claves en distinto orden producen mismo hash."""
    p1 = {"sector": "batteries", "reason": "manual fix"}
    p2 = {"reason": "manual fix", "sector": "batteries"}
    assert _canonical(p1) == _canonical(p2)
    h1 = hashlib.sha256(b"op" + _canonical(p1)).hexdigest()
    h2 = hashlib.sha256(b"op" + _canonical(p2)).hexdigest()
    assert h1 == h2


def test_tampering_with_payload_breaks_verification(db_session: Session) -> None:
    """Si alguien edita el payload en BD, verify_chain detecta el mismatch."""
    e1 = append_entry(db_session, operation="classify_override", payload={"sector": "batteries"})
    append_entry(db_session, operation="verify", payload={"completeness": 0.9})
    db_session.commit()

    # Tampering: cambiar el payload de la primera entrada sin recalcular hash.
    e1.payload = {"sector": "textile"}
    db_session.add(e1)
    db_session.commit()

    status = verify_chain(db_session)
    assert status.valid is False
    assert status.first_invalid_id == e1.id
    assert status.reason is not None


def test_tampering_with_prev_hash_breaks_verification(db_session: Session) -> None:
    """Romper el enlace `prev_hash` también se detecta."""
    append_entry(db_session, operation="classify_override", payload={"sector": "batteries"})
    e2 = append_entry(db_session, operation="verify", payload={"completeness": 0.9})
    db_session.commit()

    e2.prev_hash = "deadbeef" * 8
    db_session.add(e2)
    db_session.commit()

    status = verify_chain(db_session)
    assert status.valid is False
    assert status.first_invalid_id == e2.id


def test_empty_log_is_trivially_valid(db_session: Session) -> None:
    status = verify_chain(db_session)
    assert status.valid is True
    assert status.entries_checked == 0
