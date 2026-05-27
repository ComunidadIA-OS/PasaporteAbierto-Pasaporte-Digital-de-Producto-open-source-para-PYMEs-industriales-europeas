"""Carga de fragmentos normativos desde JSONL.

No hace re-chunking: F2-01 ya entrega un `Fragment` por artículo/apartado,
y ese es el chunk natural por construcción (cada fragmento es citable de
forma directa: "Reglamento X, Art. Y.Z"). Este módulo solo lee, valida
con Pydantic y emite `Fragment`.
"""

from collections.abc import Iterator
from pathlib import Path

from app.rag.schema import Fragment


def load_fragments(path: Path) -> Iterator[Fragment]:
    """Itera los `Fragment` de un fichero JSONL.

    Cada línea no vacía debe ser un objeto JSON válido para `Fragment`.
    Lanza `pydantic.ValidationError` si una línea no cumple el contrato.
    """
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield Fragment.model_validate_json(line)


def load_corpus(directory: Path) -> Iterator[Fragment]:
    """Itera los `Fragment` de todos los `*.jsonl` de un directorio.

    Útil para el CLI de reindexado, que apunta a `backend/data/corpus/`
    donde F2-01 deposita los reglamentos parseados.
    """
    for jsonl_file in sorted(directory.glob("*.jsonl")):
        yield from load_fragments(jsonl_file)
