from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _discover_plugins_dir() -> Path:
    """Busca el directorio `plugins/` ascendiendo desde este módulo.

    El layout cambia entre host (`backend/src/app/config.py` con `plugins/`
    a 5 niveles arriba en la raíz del repo) y contenedor (`/app/src/app/config.py`
    con `plugins/` montado en `/app/plugins`). Resolver ascendentemente quita
    el `parents[N]` hardcodeado que rompía en el contenedor.
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        candidate = parent / "plugins"
        if candidate.is_dir() and (candidate / "_schema.yaml").exists():
            return candidate
    # Fallback razonable para el contenedor (Dockerfile WORKDIR=/app).
    return Path("/app/plugins")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_backend: str = "ollama:qwen2.5:14b"
    database_url: str = "sqlite:///./pasaporteabierto.db"
    langfuse_host: str = "http://localhost:3001"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    plugins_dir: Path = _discover_plugins_dir()
    # Modo demo: activa endpoints /api/v1/demo/* (sample data + seed-documents).
    # El frontend espeja este flag en NEXT_PUBLIC_DEMO_MODE para mostrar/ocultar
    # los botones "Cargar ejemplo" sin recompilar.
    demo_mode: bool = False


settings = Settings()
