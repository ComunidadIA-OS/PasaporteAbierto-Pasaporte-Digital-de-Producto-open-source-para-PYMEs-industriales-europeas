"""Fixtures compartidos del módulo RAG."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_fragments_path() -> Path:
    """Ruta al JSONL de fragmentos de muestra (10 fragmentos ES+EN)."""
    return Path(__file__).parent / "fixtures" / "sample_fragments.jsonl"
