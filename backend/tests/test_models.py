import subprocess
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

EXPECTED_TABLES = {
    "sessions",
    "documents",
    "extracted_fields",
    "audit_log",
    "published_dpps",
}


@pytest.fixture
def engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    # Importa modelos para registrar metadata
    from app.models import (  # noqa: F401
        audit_log,
        documents,
        extracted_fields,
        published_dpps,
        sessions,
    )

    SQLModel.metadata.create_all(engine)
    return engine


def test_all_five_tables_exist(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables), f"Faltan tablas: {EXPECTED_TABLES - tables}"


def test_audit_log_has_prev_hash_and_index(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("audit_log")}
    assert "prev_hash" in columns
    assert "content_hash" in columns
    indexes = inspector.get_indexes("audit_log")
    assert any(idx["column_names"] == ["id"] or "id" in idx["column_names"] for idx in indexes) or \
        "id" in {c["name"] for c in inspector.get_columns("audit_log") if c.get("primary_key")}


def test_extracted_fields_provenance_canonical(engine):
    """Los tres estados deben caber: verified, self_declared, required_pending."""
    from app.models.extracted_fields import ExtractedField

    with Session(engine) as s:
        for provenance in ("verified", "self_declared", "required_pending"):
            ef = ExtractedField(
                session_id="sess-1",
                field_id="capacity_kwh",
                value="100",
                provenance=provenance,
                confidence=0.9,
            )
            s.add(ef)
        s.commit()
        results = s.exec(text("SELECT provenance FROM extracted_fields")).all()  # type: ignore[arg-type]
        assert {r[0] for r in results} == {"verified", "self_declared", "required_pending"}


def test_alembic_upgrade_downgrade_reversible(tmp_path: Path):
    """La migración 0001 debe ser totalmente reversible."""
    db_path = tmp_path / "rev.db"
    env = {"DATABASE_URL": f"sqlite:///{db_path}"}
    backend_dir = Path(__file__).resolve().parents[1]
    base = ["uv", "run", "alembic", "-c", "alembic.ini"]

    subprocess.run([*base, "upgrade", "head"], cwd=backend_dir, env={**__import__("os").environ, **env}, check=True)
    subprocess.run([*base, "downgrade", "base"], cwd=backend_dir, env={**__import__("os").environ, **env}, check=True)
    # Tras downgrade no debe quedar ninguna de las 5 tablas
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert not EXPECTED_TABLES.intersection(tables), "El downgrade no limpió todas las tablas"
