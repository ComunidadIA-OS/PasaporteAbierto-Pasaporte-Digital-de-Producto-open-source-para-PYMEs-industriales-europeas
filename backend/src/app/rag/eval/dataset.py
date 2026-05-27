"""Carga y validación del dataset de queries de calidad RAG."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from app.rag.schema import Language


class ExpectedCitation(BaseModel):
    reglamento: str
    articulo: str
    apartado: str | None = None


class DatasetEntry(BaseModel):
    id: str
    query: str
    expected_citation: ExpectedCitation
    idioma: Language
    tags: list[str] = []


_DEFAULT_PATH = Path(__file__).resolve().parents[4] / "tests" / "rag" / "queries.yaml"


def load_queries(path: Path | None = None) -> list[DatasetEntry]:
    yaml_path = path or _DEFAULT_PATH
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return [DatasetEntry.model_validate(entry) for entry in raw]


def render_expected_citation(citation: ExpectedCitation) -> str:
    """Renderiza la cita esperada en el mismo formato que `format_citation()`."""
    base = f"Reglamento {citation.reglamento}, Art. {citation.articulo}"
    return f"{base}.{citation.apartado}" if citation.apartado else base
