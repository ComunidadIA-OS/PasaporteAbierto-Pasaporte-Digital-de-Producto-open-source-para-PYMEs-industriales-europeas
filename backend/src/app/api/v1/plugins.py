"""Endpoint para listar plugins sectoriales disponibles.

Consumido por F4-02 (select del override manual) y F4-03 (BOM dinámico).
Lee directamente desde `plugins/*.yaml` — añadir un sector ESPR es
añadir un YAML, no modificar este endpoint.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.v1.schemas import PluginsListResponse, PluginSummary
from app.plugins.loader import Plugin, load_all_plugins

# `backend/src/app/api/v1/plugins.py` → parents[5] = repo root
PLUGINS_DIR: Path = Path(__file__).resolve().parents[5] / "plugins"

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=PluginsListResponse)
def list_plugins() -> PluginsListResponse:
    plugins = load_all_plugins(PLUGINS_DIR)
    return PluginsListResponse(
        plugins=[
            PluginSummary(
                name=p.name,
                regulation=p.regulation,
                description=p.description,
            )
            for p in plugins.values()
        ]
    )


@router.get("/{name}", response_model=Plugin)
def get_plugin_detail(name: str) -> Plugin:
    """Devuelve la definición completa del plugin (campos, docs requeridos,
    cross-validations) para generar el formulario dinámico de F4-03.
    """
    plugins = load_all_plugins(PLUGINS_DIR)
    plugin = plugins.get(name)
    if plugin is None:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    return plugin
