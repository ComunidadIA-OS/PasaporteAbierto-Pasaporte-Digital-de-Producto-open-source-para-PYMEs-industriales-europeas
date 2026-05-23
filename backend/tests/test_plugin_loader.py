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
