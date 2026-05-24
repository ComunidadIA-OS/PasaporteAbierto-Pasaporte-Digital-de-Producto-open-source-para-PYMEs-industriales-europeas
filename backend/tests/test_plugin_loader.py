from pathlib import Path

import pytest

from app.plugins.loader import Plugin, PluginValidationError, load_plugin

FIXTURES = Path(__file__).parent / "fixtures"


def test_loader_accepts_valid_plugin():
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    assert isinstance(plugin, Plugin)
    assert plugin.name == "demo-sector"
    assert plugin.regulation == "EU 2024/1781"
    assert len(plugin.fields) == 2
    assert plugin.fields[0].id == "model_name"
    assert plugin.fields[0].citation.article == "Art. 7(1)"


def test_loader_rejects_missing_required_section():
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_missing_field.yaml")
    assert "fields" in str(exc.value).lower()


def test_loader_rejects_field_without_citation():
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_missing_citation.yaml")
    assert "citation" in str(exc.value).lower()


def test_loader_lists_required_fields():
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    required_ids = [f.id for f in plugin.fields if f.required]
    assert required_ids == ["model_name"]


def test_loader_rejects_broken_yaml():
    """YAML sintácticamente roto debe ser cazado por PluginValidationError, no por yaml.YAMLError."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_broken_yaml.yaml")
    assert "yaml mal formado" in str(exc.value).lower()


def test_loader_rejects_top_level_list():
    """El YAML debe ser un mapping en la raíz, no una lista."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_top_level_list.yaml")
    assert "mapping" in str(exc.value).lower()


def test_loader_rejects_unknown_top_level_key():
    """Una clave extra como 'typoed_section' debe ser rechazada (extra='forbid')."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_unknown_key.yaml")
    msg = str(exc.value).lower()
    assert (
        "typoed_section" in msg
        or "extra" in msg
        or "forbidden" in msg
        or "no cumple el esquema" in msg
    )


def test_loader_accepts_access_level_legitimate_interest():
    """Un fixture con access_level != 'public' debe cargar y exponerlo correctamente."""
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    al = [f.access_level for f in plugin.fields]
    assert "legitimate_interest" in al, f"Esperaba algún campo con legitimate_interest, vi {al}"


def test_loader_defaults_access_level_to_public():
    """Un campo sin access_level explícito debe heredar 'public' (backward compat)."""
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    model_name = next(f for f in plugin.fields if f.id == "model_name")
    assert model_name.access_level == "public"


def test_loader_rejects_invalid_access_level():
    """Valor fuera del enum debe ser rechazado por Pydantic Literal."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_invalid_access_level.yaml")
    msg = str(exc.value).lower()
    assert "access_level" in msg or "literal" in msg or "no cumple el esquema" in msg


def test_loader_accepts_iso_iec_15459_identifier_scheme():
    """identifier_scheme=iso_iec_15459 (obligatorio para baterías por Art. 77.3) es aceptado."""
    p = Plugin(
        name="x",
        regulation="y",
        version="0.0.0",
        identifier_scheme="iso_iec_15459",
        fields=[],
        required_documents=[],
    )
    assert p.identifier_scheme == "iso_iec_15459"


def test_loader_defaults_identifier_scheme_to_gs1_digital_link():
    """Un plugin sin identifier_scheme explícito hereda 'gs1_digital_link' (backward compat)."""
    p = Plugin(name="x", regulation="y", version="0.0.0", fields=[], required_documents=[])
    assert p.identifier_scheme == "gs1_digital_link"


def test_loader_rejects_unknown_identifier_scheme():
    """identifier_scheme fuera del enum debe ser rechazado."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_invalid_identifier_scheme.yaml")
    msg = str(exc.value).lower()
    assert "identifier_scheme" in msg or "literal" in msg or "no cumple el esquema" in msg
