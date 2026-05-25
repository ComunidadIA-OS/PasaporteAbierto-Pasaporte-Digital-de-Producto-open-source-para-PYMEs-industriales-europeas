"""Reindexa todos los JSONL de `backend/data/corpus/` en ChromaDB.

Uso: `uv run python -m scripts.reindex`. Idempotente — reejecutar no
duplica vectores ni metadatos gracias al ID determinista del índice.
"""

import sys
import time
from pathlib import Path

# Permite ejecutar `uv run python -m scripts.reindex` desde backend/ sin instalar el paquete.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.rag.chunking import load_corpus  # noqa: E402
from app.rag.index import upsert_fragments  # noqa: E402

_CORPUS_DIR = Path(__file__).resolve().parents[1] / "data" / "corpus"


def main() -> None:
    if not _CORPUS_DIR.exists():
        print(f"Directorio del corpus no encontrado: {_CORPUS_DIR}")
        print("Ejecuta primero la ingesta (F2-01) para poblar backend/data/corpus/")
        sys.exit(1)

    start = time.perf_counter()
    count = upsert_fragments(load_corpus(_CORPUS_DIR))
    elapsed = time.perf_counter() - start
    print(f"Reindexado: {count} fragmentos en {elapsed:.2f}s")


if __name__ == "__main__":
    main()
