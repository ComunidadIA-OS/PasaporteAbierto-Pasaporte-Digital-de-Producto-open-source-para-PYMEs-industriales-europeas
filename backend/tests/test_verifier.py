"""Tests del módulo app.verifier (F3-03).

Cubre verify_session() en aislamiento — el endpoint vive en
test_wizard_verify.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import (  # noqa: F401  registrar metadata
    audit_log,
    documents,
    extracted_fields,
    published_dpps,
    sessions,
)
from app.models.extracted_fields import ExtractedField
from app.models.sessions import WizardSession
from app.plugins.loader import load_plugin
from app.verifier import verify_session

PLUGIN_PATH = Path(__file__).resolve().parents[2] / "plugins" / "batteries.yaml"


@pytest.fixture
def db_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'verifier.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def plugin():
    return load_plugin(PLUGIN_PATH)


def _make_session(db: Session, session_id: str = "sess-1") -> WizardSession:
    s = WizardSession(id=session_id, sector="batteries", plugin="batteries")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _add_field(
    db: Session, session_id: str, field_id: str, value: str, provenance: str = "self_declared"
) -> None:
    db.add(
        ExtractedField(
            session_id=session_id,
            field_id=field_id,
            value=value,
            provenance=provenance,
            confidence=1.0,
        )
    )
    db.commit()


def test_empty_session_blocks_publish(db_session: Session, plugin) -> None:
    s = _make_session(db_session)
    result = verify_session(db_session, s, plugin)
    assert result.can_publish is False
    assert result.completeness == 0.0
    assert len(result.missing_fields) > 0
    # Todos los faltantes son required_pending (ninguno se intentó rellenar).
    assert all(m.reason == "required_pending" for m in result.missing_fields)


def test_partial_session_reports_progress(db_session: Session, plugin) -> None:
    s = _make_session(db_session)
    _add_field(db_session, s.id, "battery_passport_unique_id", "ABC-12345")
    _add_field(db_session, s.id, "battery_mass_kg", "25.5")

    result = verify_session(db_session, s, plugin)
    assert result.can_publish is False  # aún faltan required
    assert 0 < result.completeness < 1
    assert len(result.missing_fields) > 0


def test_required_pending_provenance_counts_as_missing(db_session: Session, plugin) -> None:
    """Un row con provenance=required_pending debe contar como faltante."""
    s = _make_session(db_session)
    _add_field(
        db_session,
        s.id,
        "battery_passport_unique_id",
        "",
        provenance="required_pending",
    )
    result = verify_session(db_session, s, plugin)
    missing_ids = [m.field_id for m in result.missing_fields]
    assert "battery_passport_unique_id" in missing_ids


def test_wrong_type_marks_validation_failed(db_session: Session, plugin) -> None:
    """battery_mass_kg con valor no numérico debe reportarse validation_failed."""
    s = _make_session(db_session)
    _add_field(db_session, s.id, "battery_mass_kg", "no-soy-numero")
    result = verify_session(db_session, s, plugin)
    failed = [m for m in result.missing_fields if m.field_id == "battery_mass_kg"]
    assert len(failed) == 1
    assert failed[0].reason == "validation_failed"


def test_cross_validation_failure_emits_warning(db_session: Session, plugin) -> None:
    """voltage_min_v > voltage_max_v viola voltage_consistency."""
    s = _make_session(db_session)
    # Setear los tres campos del cross_validation con valores inconsistentes.
    _add_field(db_session, s.id, "voltage_min_v", "10")
    _add_field(db_session, s.id, "voltage_nominal_v", "20")
    _add_field(db_session, s.id, "voltage_max_v", "5")  # max < min, regla rota

    result = verify_session(db_session, s, plugin)
    rule_ids = [w.rule_id for w in result.warnings]
    assert "voltage_consistency" in rule_ids


def test_cross_validation_with_missing_fields_is_silent(db_session: Session, plugin) -> None:
    """Si los campos de una cross_validation no están todos, la regla es indeterminada
    y NO se reporta como warning (para no ahogar la UI con avisos prematuros)."""
    s = _make_session(db_session)
    _add_field(db_session, s.id, "voltage_min_v", "10")
    # No añadimos voltage_nominal_v ni voltage_max_v
    result = verify_session(db_session, s, plugin)
    rule_ids = [w.rule_id for w in result.warnings]
    assert "voltage_consistency" not in rule_ids


def test_citation_propagated_to_missing(db_session: Session, plugin) -> None:
    """Cada missing_field debe llevar la cita normativa del plugin."""
    s = _make_session(db_session)
    result = verify_session(db_session, s, plugin)
    for m in result.missing_fields[:5]:
        assert m.citation_regulation != ""
        assert m.citation_article != ""


def test_repeater_serialized_as_json_deserializes_ok(db_session: Session, plugin) -> None:
    """Un repeater guardado como JSON string debe deserializar a lista."""
    import json

    s = _make_session(db_session)
    _add_field(
        db_session,
        s.id,
        "hazardous_substances",
        json.dumps(["Pb < 0.01%", "Hg < 0.0005%"]),
    )
    result = verify_session(db_session, s, plugin)
    failed = [m for m in result.missing_fields if m.field_id == "hazardous_substances"]
    # Si deserializa OK, no aparece como validation_failed.
    assert not any(m.reason == "validation_failed" for m in failed)
