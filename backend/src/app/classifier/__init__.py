"""Agente Clasificador (F3-01) — paso 2 del wizard.

Pipeline lineal sin frameworks de agentes:

    descripción → search_corpus → prompt → complete → parse JSON →
        validar contra plugins → ClassificationResult

Punto único de entrada: `classify(description)`.
"""

from app.classifier.agent import ClassificationResult, classify

__all__ = ["ClassificationResult", "classify"]
