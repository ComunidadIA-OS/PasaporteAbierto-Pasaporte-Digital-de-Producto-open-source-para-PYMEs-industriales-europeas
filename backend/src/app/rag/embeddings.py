"""Wrapper de embeddings sobre `sentence-transformers` con bge-m3.

Carga del modelo perezosa (lazy singleton): la primera llamada a `embed()`
descarga e instancia el modelo; las siguientes reutilizan la misma instancia.
Esto evita penalizar el arranque de FastAPI con la descarga del modelo
(~2 GB en primera ejecución) y permite a los tests que no usan embeddings
correr sin tocarlo.
"""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_MODEL_NAME = "BAAI/bge-m3"
# bge-m3 admite hasta 8192 tokens, pero la atención es O(n²): codificar un
# lote de fragmentos largos (p. ej. artículos de definiciones con decenas de
# apartados concatenados, ~5 K tokens) hace estallar la memoria (>30 GiB).
# Acotamos la secuencia a 1024 tokens —cubre con holgura un apartado legal
# normal (p99 del corpus ≈ 780 tokens)— y procesamos en lotes pequeños para
# mantener el uso de memoria acotado y la indexación reproducible en CPU.
_MAX_SEQ_LENGTH = 1024
_BATCH_SIZE = 8
_model: SentenceTransformer | None = None
_lock = Lock()


def _get_model() -> SentenceTransformer:
    """Devuelve el modelo bge-m3, descargándolo en la primera llamada."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(_MODEL_NAME)
                model.max_seq_length = _MAX_SEQ_LENGTH
                _model = model
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Calcula embeddings densos para una lista de textos.

    Devuelve vectores normalizados (longitud 1) — bge-m3 ya los entrega así
    cuando se usa `normalize_embeddings=True`, lo que permite usar producto
    escalar como similitud coseno directamente. Los textos que excedan
    `_MAX_SEQ_LENGTH` tokens se truncan; el lote se procesa en bloques de
    `_BATCH_SIZE` para acotar la memoria.
    """
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=_BATCH_SIZE,
    )
    return vectors.tolist()
