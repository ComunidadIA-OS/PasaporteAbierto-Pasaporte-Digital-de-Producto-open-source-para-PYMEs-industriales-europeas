"""Verificador del DPP (F3-03) — paso 6 determinista.

Componente puro (sin LLM, sin RAG) que valida el estado de una sesión
contra el schema del plugin asignado:

  1. Cada campo `required` del plugin tiene un valor en `extracted_fields`
     y su tipo es deserializable.
  2. Las `cross_validations` del YAML se evalúan contra el BOM.

Política de severidad:
  - Falta o tipo inválido en required → `missing_fields` → bloquea publicación.
  - `cross_validation` fallida → `warnings` → NO bloquea publicación (el
    plugin puede marcarlas como críticas haciéndolas required en su campo).

Las reglas de `cross_validations` se evalúan con `eval()` en un namespace
restringido: `__builtins__` vacío y solo las claves del BOM como variables.
El YAML del plugin es código de configuración del repo, no input externo,
así que la superficie de ataque está acotada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Session, select

from app.models.extracted_fields import ExtractedField
from app.models.sessions import WizardSession
from app.plugins.loader import Plugin, PluginField


@dataclass(frozen=True)
class MissingFieldInfo:
    field_id: str
    citation_regulation: str
    citation_article: str
    reason: str  # "required_pending" | "validation_failed"


@dataclass(frozen=True)
class WarningInfo:
    rule_id: str | None
    field_id: str | None
    message: str


@dataclass(frozen=True)
class VerifyResult:
    completeness: float
    can_publish: bool
    missing_fields: list[MissingFieldInfo] = field(default_factory=list)
    warnings: list[WarningInfo] = field(default_factory=list)


def _deserialize_value(value: str, field_def: PluginField) -> Any:
    """Convierte el valor string almacenado a su tipo Python real.

    Devuelve `None` si el valor no encaja en el tipo declarado — el caller
    interpreta None como `reason="validation_failed"`.
    """
    if value == "":
        return None
    if field_def.type == "boolean":
        return value.lower() in ("true", "1", "yes")
    if field_def.type == "integer":
        try:
            return int(value)
        except ValueError:
            return None
    if field_def.type == "number":
        try:
            return float(value)
        except ValueError:
            return None
    if field_def.type == "repeater":
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None
    # string, enum → string tal cual
    return value


def _eval_rule(rule: str, bom: dict[str, Any]) -> bool | None:
    """Evalúa una expresión del YAML contra el BOM.

    Devuelve:
      - True si la regla se cumple
      - False si la regla se viola
      - None si no se puede evaluar (campos faltantes, error de sintaxis)
        → tratamos como "indeterminado", no se reporta como warning.

    Seguridad: `__builtins__` vacío + namespace = BOM bloquean cualquier
    acceso al runtime Python. Los plugins son código de configuración del
    repo (no input externo), así que evaluar expresiones controladas es
    seguro.
    """
    try:
        return bool(eval(rule, {"__builtins__": {}}, bom))
    except (NameError, KeyError, TypeError, SyntaxError):
        return None


def verify_session(db: Session, session: WizardSession, plugin: Plugin) -> VerifyResult:
    """Valida la sesión contra el schema del plugin. Función pura sobre la BD."""
    rows = db.exec(
        select(ExtractedField).where(ExtractedField.session_id == session.id)
    ).all()
    by_id: dict[str, ExtractedField] = {r.field_id: r for r in rows}

    missing: list[MissingFieldInfo] = []
    bom_values: dict[str, Any] = {}

    total_required = 0
    present_required = 0

    for f_def in plugin.fields:
        row = by_id.get(f_def.id)
        deserialized: Any = None
        if row is not None and row.provenance != "required_pending":
            deserialized = _deserialize_value(row.value, f_def)
            if deserialized is not None:
                bom_values[f_def.id] = deserialized

        if not f_def.required:
            continue

        total_required += 1
        if row is None or row.provenance == "required_pending":
            missing.append(
                MissingFieldInfo(
                    field_id=f_def.id,
                    citation_regulation=f_def.citation.regulation,
                    citation_article=f_def.citation.article,
                    reason="required_pending",
                )
            )
        elif deserialized is None:
            missing.append(
                MissingFieldInfo(
                    field_id=f_def.id,
                    citation_regulation=f_def.citation.regulation,
                    citation_article=f_def.citation.article,
                    reason="validation_failed",
                )
            )
        else:
            present_required += 1

    warnings: list[WarningInfo] = []
    for cv in plugin.cross_validations:
        result = _eval_rule(cv.rule, bom_values)
        if result is False:
            warnings.append(
                WarningInfo(
                    rule_id=cv.id,
                    field_id=None,
                    message=cv.message or f"regla {cv.id} no cumplida",
                )
            )

    completeness = (present_required / total_required) if total_required else 1.0
    return VerifyResult(
        completeness=completeness,
        missing_fields=missing,
        warnings=warnings,
        can_publish=len(missing) == 0,
    )


__all__ = ["MissingFieldInfo", "VerifyResult", "WarningInfo", "verify_session"]
