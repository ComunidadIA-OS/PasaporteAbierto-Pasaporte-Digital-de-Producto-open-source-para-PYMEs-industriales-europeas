"""Test de contrato que cualquier plugin futuro debe pasar.

Auto-descubre todos los ``plugins/*.yaml`` (excluyendo ``_schema.yaml``) y
verifica las 13 invariantes documentadas en ``docs/plugins.md``. La salida del
test muestra qué plugin falla qué assertion mediante ``pytest.mark.parametrize``.

Invariantes verificadas:
    1.  El YAML carga sin errores vía ``load_plugin``.
    2.  Contiene los bloques obligatorios (name, regulation, version, fields,
        required_documents). Redundante con el loader, documentado aquí para
        que el contrato sea explícito en el test.
    3.  ``version`` es semver válido (``major.minor.patch``).
    4.  Cada campo tiene ``citation`` con ``regulation`` y ``article`` no vacíos.
    5.  Cada campo ``enum`` declara ``enum_values`` no vacío.
    6.  Cada campo ``repeater`` no declara ``enum_values``.
    7.  ``access_level`` es uno de los 4 valores del enum (Pydantic Literal).
    8.  ``identifier_scheme`` es ``gs1_digital_link`` o ``iso_iec_15459``.
    9.  ``required_documents`` solo usa tipos del enum ``DocType``.
    10. Si ``required_documents[i].when`` está definido, parsea como expresión
        Python válida (``ast.parse(..., mode="eval")``).
    11. Cada ``cross_validations[i].rule`` parsea como expresión Python válida.
    12. No hay campos duplicados dentro del plugin (``id`` único).
    13. Si el plugin se llama ``batteries``, su ``identifier_scheme`` debe ser
        ``iso_iec_15459`` (Art. 77.3 del Reglamento UE 2023/1542).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import get_args

import pytest

from app.plugins.loader import (
    AccessLevel,
    DocType,
    IdentifierScheme,
    Plugin,
    load_plugin,
)

PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
VALID_ACCESS_LEVELS = set(get_args(AccessLevel))
VALID_IDENTIFIER_SCHEMES = set(get_args(IdentifierScheme))
VALID_DOC_TYPES = set(get_args(DocType))


def _discover_plugin_files() -> list[Path]:
    """Encuentra todos los YAMLs de plugin reales en ``plugins/``."""
    return sorted(
        p for p in PLUGINS_DIR.glob("*.yaml") if not p.name.startswith("_")
    )


PLUGIN_FILES = _discover_plugin_files()


@pytest.fixture(scope="module")
def plugin(request: pytest.FixtureRequest) -> Plugin:
    """Carga el plugin desde el path indirecto, fallando claro si no carga (check #1)."""
    path: Path = request.param
    return load_plugin(path)


@pytest.mark.parametrize("plugin", PLUGIN_FILES, indirect=True, ids=lambda p: p.stem)
class TestPluginContract:
    """Cada test de la clase es una de las 13 invariantes del contrato."""

    def test_01_loads_without_errors(self, plugin: Plugin) -> None:
        """Check 1: ``load_plugin`` ya ejecutó en el fixture; basta verificar el tipo."""
        assert isinstance(plugin, Plugin)

    def test_02_has_required_top_level_blocks(self, plugin: Plugin) -> None:
        """Check 2: bloques obligatorios presentes y no vacíos donde aplique."""
        assert plugin.name, "name vacío"
        assert plugin.regulation, "regulation vacía"
        assert plugin.version, "version vacía"
        assert plugin.fields, "fields vacío: un plugin sin campos no modela nada"
        assert plugin.required_documents, "required_documents vacío"

    def test_03_version_is_valid_semver(self, plugin: Plugin) -> None:
        """Check 3: version es ``major.minor.patch`` (sin pre-release ni metadata por ahora)."""
        assert SEMVER_RE.match(plugin.version), (
            f"version='{plugin.version}' no es semver válido (formato esperado: major.minor.patch)"
        )

    def test_04_every_field_has_non_empty_citation(self, plugin: Plugin) -> None:
        """Check 4: la cita normativa es la promesa central del proyecto. Sin cita, no hay campo."""
        for f in plugin.fields:
            assert f.citation.regulation.strip(), (
                f"campo '{f.id}' tiene citation.regulation vacía"
            )
            assert f.citation.article.strip(), (
                f"campo '{f.id}' tiene citation.article vacía"
            )

    def test_05_enum_fields_declare_enum_values(self, plugin: Plugin) -> None:
        """Check 5: un campo enum sin enum_values no puede renderizarse en el wizard."""
        for f in plugin.fields:
            if f.type == "enum":
                assert f.enum_values, (
                    f"campo '{f.id}' es enum pero no declara enum_values"
                )

    def test_06_repeater_fields_have_no_enum_values(self, plugin: Plugin) -> None:
        """Check 6: enum_values no aplica a repeaters (que repiten subestructuras, no opciones)."""
        for f in plugin.fields:
            if f.type == "repeater":
                assert f.enum_values is None, (
                    f"campo '{f.id}' es repeater y declara enum_values; no aplica"
                )

    def test_07_access_level_is_in_enum(self, plugin: Plugin) -> None:
        """Check 7: redundante con Pydantic Literal, explícito para documentar el contrato."""
        for f in plugin.fields:
            assert f.access_level in VALID_ACCESS_LEVELS, (
                f"campo '{f.id}' tiene access_level='{f.access_level}' "
                f"fuera del enum {sorted(VALID_ACCESS_LEVELS)}"
            )

    def test_08_identifier_scheme_is_valid(self, plugin: Plugin) -> None:
        """Check 8: identifier_scheme dentro del enum reconocido (ADR 0001)."""
        assert plugin.identifier_scheme in VALID_IDENTIFIER_SCHEMES, (
            f"identifier_scheme='{plugin.identifier_scheme}' fuera del enum "
            f"{sorted(VALID_IDENTIFIER_SCHEMES)}"
        )

    def test_09_required_documents_use_valid_doc_types(self, plugin: Plugin) -> None:
        """Check 9: el tipo de documento debe pertenecer al enum DocType del loader."""
        for doc in plugin.required_documents:
            assert doc.type in VALID_DOC_TYPES, (
                f"required_documents[*].type='{doc.type}' fuera del enum "
                f"{sorted(VALID_DOC_TYPES)}"
            )

    def test_10_when_clauses_parse_as_python_expressions(self, plugin: Plugin) -> None:
        """Check 10: el ``when`` de un documento debe ser una expresión Python parseable.

        No se evalúa la expresión (eso es responsabilidad del evaluador del
        Verificador en F3/F6); solo se valida la sintaxis con ``ast.parse``.
        """
        for doc in plugin.required_documents:
            if doc.when is None:
                continue
            try:
                ast.parse(doc.when, mode="eval")
            except SyntaxError as exc:
                pytest.fail(
                    f"required_documents[type={doc.type}].when='{doc.when}' "
                    f"no parsea como expresión Python: {exc}"
                )

    def test_11_cross_validation_rules_parse_as_python_expressions(
        self, plugin: Plugin
    ) -> None:
        """Check 11: cada ``rule`` de cross_validations debe ser una expresión Python parseable."""
        for cv in plugin.cross_validations:
            try:
                ast.parse(cv.rule, mode="eval")
            except SyntaxError as exc:
                pytest.fail(
                    f"cross_validations[id={cv.id}].rule='{cv.rule}' "
                    f"no parsea como expresión Python: {exc}"
                )

    def test_12_field_ids_are_unique(self, plugin: Plugin) -> None:
        """Check 12: dos campos con el mismo id romperían la persistencia en extracted_fields."""
        ids = [f.id for f in plugin.fields]
        duplicates = [fid for fid in set(ids) if ids.count(fid) > 1]
        assert not duplicates, f"ids duplicados en fields: {duplicates}"

    def test_13_batteries_plugin_uses_iso_iec_15459(self, plugin: Plugin) -> None:
        """Check 13: el plugin de baterías DEBE declarar iso_iec_15459 por Art. 77.3 del Reg. UE 2023/1542.

        Este check solo se aplica al plugin con ``name == 'batteries'``; los demás
        plugins quedan libres de elegir el esquema apropiado para su sector.
        """
        if plugin.name != "batteries":
            pytest.skip(f"check específico de baterías; '{plugin.name}' no aplica")
        assert plugin.identifier_scheme == "iso_iec_15459", (
            "El plugin de baterías debe declarar identifier_scheme='iso_iec_15459' "
            "(Art. 77.3 del Reglamento UE 2023/1542)"
        )


def test_at_least_two_plugins_discovered() -> None:
    """Sanidad: FUNCIONAL §10 #5 exige ≥2 plugins funcionales. Verifica el descubrimiento."""
    assert len(PLUGIN_FILES) >= 2, (
        f"Se esperaban ≥2 plugins en plugins/, encontrados: "
        f"{[p.name for p in PLUGIN_FILES]}"
    )
