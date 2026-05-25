"""Recolector de PDFs (F3-02).

Pipeline híbrido: pdfplumber para texto estructurado, LLM para campos en
lenguaje natural. No abre diálogo con el usuario.
"""

from app.collector.agent import extract_fields

__all__ = ["extract_fields"]
