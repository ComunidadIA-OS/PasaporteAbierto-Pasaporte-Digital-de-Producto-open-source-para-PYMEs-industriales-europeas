"""Ingesta del corpus normativo (F2-01).

Uso desde backend/::

    uv run python -m scripts.ingest_corpus
    uv run python -m scripts.ingest_corpus -- --only iso-15459

Equivalente a ``PYTHONPATH=src uv run python -m app.rag.ingest`` (``make ingest``).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.rag.ingest.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
