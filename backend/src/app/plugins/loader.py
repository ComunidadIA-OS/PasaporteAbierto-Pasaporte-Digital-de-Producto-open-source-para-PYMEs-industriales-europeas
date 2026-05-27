from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

DocType = Literal["datasheet", "certificate", "lca", "sds", "ce_declaration"]
FieldType = Literal["string", "number", "integer", "boolean", "enum", "repeater"]
AccessLevel = Literal["public", "legitimate_interest", "authorities_only", "individual"]
IdentifierScheme = Literal["gs1_digital_link", "iso_iec_15459"]


class PluginValidationError(Exception):
    """Se eleva cuando un YAML no cumple `_schema.yaml`."""


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: str
    article: str


class PluginField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: FieldType
    required: bool
    citation: Citation
    access_level: AccessLevel = "public"
    enum_values: list[str] | None = None
    validation: str | None = None


class RequiredDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: DocType
    mandatory: bool
    when: str | None = None


class CrossValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    rule: str
    message: str | None = None


class Plugin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    regulation: str
    version: str
    description: str = ""
    identifier_scheme: IdentifierScheme = "gs1_digital_link"
    fields: list[PluginField] = Field(default_factory=list)
    required_documents: list[RequiredDocument] = Field(default_factory=list)
    cross_validations: list[CrossValidation] = Field(default_factory=list)


def load_plugin(path: Path) -> Plugin:
    """Carga y valida un YAML de plugin. Eleva PluginValidationError si no cumple."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise PluginValidationError(f"{path.name}: YAML mal formado ({e})") from e
    if not isinstance(raw, dict):
        raise PluginValidationError(f"{path.name}: el YAML debe ser un mapping en la raíz")

    for required_section in ("name", "regulation", "version", "fields", "required_documents"):
        if required_section not in raw or raw[required_section] is None:
            raise PluginValidationError(
                f"{path.name}: falta sección obligatoria '{required_section}'"
            )

    try:
        return Plugin(**raw)
    except ValidationError as e:
        raise PluginValidationError(f"{path.name}: el plugin no cumple el esquema:\n{e}") from e


def load_all_plugins(plugins_dir: Path) -> dict[str, Plugin]:
    """Carga todos los YAMLs de `plugins_dir` excepto `_schema.yaml`."""
    plugins: dict[str, Plugin] = {}
    for yaml_file in plugins_dir.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue
        plugin = load_plugin(yaml_file)
        plugins[plugin.name] = plugin
    return plugins
