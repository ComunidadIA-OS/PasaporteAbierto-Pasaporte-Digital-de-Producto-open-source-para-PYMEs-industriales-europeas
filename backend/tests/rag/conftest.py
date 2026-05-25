"""Fixtures compartidos del módulo RAG."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Directorio con fixtures HTML/JSON-LD reales recortados."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_fragments_path() -> Path:
    """Ruta al JSONL de fragmentos de muestra (10 fragmentos ES+EN)."""
    return Path(__file__).parent / "fixtures" / "sample_fragments.jsonl"
