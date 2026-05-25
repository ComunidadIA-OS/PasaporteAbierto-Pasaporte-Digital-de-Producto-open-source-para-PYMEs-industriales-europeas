"""Fixtures compartidos de tests RAG."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Directorio con fixtures HTML/JSON-LD reales recortados."""
    return Path(__file__).parent / "fixtures"
