"""Escritura atómica de JSONL de Fragments.

Una línea = un Fragment serializado con `model_dump_json()`. Escritura
atómica con `os.replace`: si la operación falla a medias, el fichero
previo (si existía) queda intacto.
"""

import os
from collections.abc import Iterable
from pathlib import Path

from app.rag.schema import Fragment


def write_jsonl(path: Path, fragments: Iterable[Fragment]) -> int:
    """Escribe `fragments` como JSONL en `path` de forma atómica.

    Devuelve el número de fragments escritos. El destino se crea si no
    existe; los directorios padre también.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8") as fh:
        for fragment in fragments:
            fh.write(fragment.model_dump_json())
            fh.write("\n")
            count += 1
    os.replace(tmp, path)
    return count
