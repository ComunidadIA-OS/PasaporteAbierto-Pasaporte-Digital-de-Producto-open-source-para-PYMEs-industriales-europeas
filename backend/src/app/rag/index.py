"""Índice vectorial sobre ChromaDB embebido.

Persistencia local en `backend/data/chroma/` (mismo volumen Docker que
SQLite, ver `docker-compose.yml`). Cada `Fragment` se identifica por un
hash determinista de su (reglamento, artículo, apartado, idioma), de modo
que reindexar dos veces el mismo corpus es idempotente — criterio 2 de
F2-02.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from app.rag.embeddings import embed
from app.rag.schema import Fragment

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

_DEFAULT_PATH = Path("data/chroma")
_COLLECTION_NAME = "corpus_normativo"


def _fragment_id(fragment: Fragment) -> str:
    """ID determinista de 16 chars hex para un fragmento.

    El ID deriva de (reglamento, artículo, apartado, idioma, **texto**).
    Incluir el texto es necesario porque las coordenadas estructurales no
    son únicas: dentro de un mismo anexo la numeración de apartado se
    reinicia por cada parte (p. ej. el Annex VIII del Reg. UE 2023/1542
    tiene varias partes con apartado "1."), así que (anexo, apartado) se
    repite. Sin el texto, esos fragmentos colapsarían al mismo ID y el
    upsert perdería contenido.

    Sigue siendo idempotente para el criterio F2-02: el mismo corpus
    produce siempre los mismos IDs, de modo que reindexar dos veces
    sobrescribe en lugar de duplicar.
    """
    key = (
        f"{fragment.reglamento}|{fragment.articulo}|{fragment.apartado or ''}"
        f"|{fragment.idioma}|{fragment.texto}"
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _fragment_metadata(fragment: Fragment) -> dict[str, str]:
    """Metadata serializable para ChromaDB.

    ChromaDB acepta valores primitivos (str, int, float, bool); `None` no
    siempre se admite en `where`, por lo que `apartado` y `sector` se
    serializan como cadena vacía cuando no aplican. F2-03 decidirá la
    semántica de filtros sobre esa convención.
    """
    return {
        "reglamento": fragment.reglamento,
        "articulo": fragment.articulo,
        "apartado": fragment.apartado or "",
        "idioma": fragment.idioma,
        "fuente_url": str(fragment.fuente_url),
        "sector": fragment.sector or "",
    }


def _metadata_to_fragment(text: str, meta: dict) -> Fragment:
    """Reconstruye un `Fragment` a partir del documento + metadata de Chroma."""
    return Fragment(
        texto=text,
        reglamento=meta["reglamento"],
        articulo=meta["articulo"],
        apartado=meta["apartado"] or None,
        idioma=meta["idioma"],
        fuente_url=meta["fuente_url"],
        sector=meta["sector"] or None,
    )


def get_collection(path: Path | None = None) -> Collection:
    """Devuelve la colección ChromaDB del corpus normativo.

    `path` permite a los tests usar un directorio temporal. En producción
    se omite y se usa `backend/data/chroma/`.
    """
    import chromadb

    chroma_path = path or _DEFAULT_PATH
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        # `hnsw:search_ef` por defecto es 10, demasiado bajo: con el corpus
        # completo la búsqueda aproximada llegaba a saltarse el vecino más
        # cercano real y el top-3 variaba entre reconstrucciones del índice.
        # Subirlo a 100 da recall casi exacto sobre un corpus de este tamaño
        # (unos miles de vectores) sin coste perceptible, y hace el retrieval
        # determinista frente a reindexados.
        metadata={"hnsw:space": "cosine", "hnsw:search_ef": 100},
    )


def reset_collection(path: Path | None = None) -> None:
    """Borra la colección del corpus para reconstruirla desde cero.

    El `upsert` es idempotente cuando el corpus no cambia, pero si cambia el
    chunking o el texto de un fragmento su ID (hash de contenido) cambia y el
    upsert dejaría vectores antiguos huérfanos. Un reindexado completo debe
    empezar por vaciar la colección para no acumular residuos.
    """
    import contextlib

    import chromadb

    chroma_path = path or _DEFAULT_PATH
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    # La colección puede no existir todavía (primer reindexado): es benigno.
    with contextlib.suppress(Exception):
        client.delete_collection(_COLLECTION_NAME)


def upsert_fragments(
    fragments: Iterable[Fragment],
    path: Path | None = None,
) -> int:
    """Inserta o actualiza fragmentos en el índice. Devuelve el nº procesado.

    Idempotente: el ID se deriva determinísticamente de los metadatos, así
    que reejecutar con los mismos fragmentos sobrescribe sin duplicar.
    """
    collection = get_collection(path)
    batch = list(fragments)
    if not batch:
        return 0

    ids = [_fragment_id(f) for f in batch]
    documents = [f.texto for f in batch]
    metadatas = [_fragment_metadata(f) for f in batch]
    embeddings = embed(documents)

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return len(batch)


def query(
    text: str,
    top_k: int = 5,
    where: dict | None = None,
    path: Path | None = None,
) -> list[tuple[Fragment, float]]:
    """Recupera los `top_k` fragmentos más similares a `text`.

    Devuelve pares `(Fragment, score)` con score en [0, 1] aproximado
    (1 = idéntico, 0 = ortogonal) calculado como `1 - distancia coseno`.
    `where` se pasa tal cual a ChromaDB para filtrado por metadata.
    """
    collection = get_collection(path)
    query_embeddings = embed([text])
    result = collection.query(
        query_embeddings=query_embeddings,
        n_results=top_k,
        where=where,
    )

    documents = result["documents"][0] if result["documents"] else []
    metadatas = result["metadatas"][0] if result["metadatas"] else []
    distances = result["distances"][0] if result["distances"] else []

    return [
        (_metadata_to_fragment(doc, meta), 1.0 - dist)
        for doc, meta, dist in zip(documents, metadatas, distances, strict=True)
    ]
