"""Tests del wrapper bge-m3.

Marcados como `slow` porque la primera ejecución descarga el modelo
(~2 GB). En CI/local rápido, ejecutar con `pytest -m "not slow"` para
omitirlos; en verificación end-to-end de F2-02, ejecutar con
`pytest -m slow` o sin filtro.
"""

import pytest

from app.rag.embeddings import embed


@pytest.mark.slow
def test_embed_empty_returns_empty() -> None:
    assert embed([]) == []


@pytest.mark.slow
def test_embed_returns_normalized_vectors() -> None:
    vectors = embed(["pasaporte digital de producto"])
    assert len(vectors) == 1
    vec = vectors[0]
    norm = sum(x * x for x in vec) ** 0.5
    # bge-m3 con normalize_embeddings=True produce vectores unitarios.
    assert abs(norm - 1.0) < 1e-3


@pytest.mark.slow
def test_embed_similar_texts_score_higher_than_unrelated() -> None:
    """ES↔ES sobre el mismo tema > ES↔EN sobre tema distinto.

    Cubre la intuición del criterio 3 de F2-02 (multilingüe sobre mismo
    índice) y del criterio 1 (resultados relevantes en top-k).
    """
    texts = [
        "pasaporte digital de producto para baterías",  # ES tema A
        "battery passport regulation requirements",  # EN tema A (mismo)
        "agricultural subsidies in the common market",  # EN tema B (distinto)
    ]
    a_es, a_en, b_en = embed(texts)

    def dot(u: list[float], v: list[float]) -> float:
        return sum(x * y for x, y in zip(u, v, strict=True))

    similar_score = dot(a_es, a_en)
    unrelated_score = dot(a_es, b_en)
    assert similar_score > unrelated_score
