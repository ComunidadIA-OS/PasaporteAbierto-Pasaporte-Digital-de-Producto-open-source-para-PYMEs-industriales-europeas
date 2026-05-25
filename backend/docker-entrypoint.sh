#!/bin/sh
# Entrypoint del backend en Docker.
#
# Hace lo que históricamente había que disparar a mano:
#   1. Migraciones Alembic (crea tablas si la SQLite acaba de nacer).
#   2. Hidratación del corpus RAG (descarga EUR-Lex + embeddings + indexa
#      en ChromaDB) en BACKGROUND si la colección está vacía. La primera
#      vez tarda 5-15 min; el servidor HTTP no espera.
#   3. Levanta uvicorn.
#
# La detección del "primera ejecución" se hace consultando el `count()` de
# la colección Chroma. Es barato (read-only) y no depende de la presencia
# de ficheros concretos.

set -e

echo "[entrypoint] Aplicando migraciones Alembic..."
uv run alembic upgrade head

# Detecta si la colección RAG está vacía. Falla → asumimos vacía para no
# romper el arranque por un error transitorio del cliente Chroma.
EMPTY=$(uv run python -c "
try:
    from app.rag.index import get_collection
    print('0' if get_collection().count() > 0 else '1')
except Exception:
    print('1')
" 2>/dev/null || echo "1")

if [ "$EMPTY" = "1" ]; then
    echo "[entrypoint] ChromaDB vacío — hidratando corpus en segundo plano (5-15 min)."
    (
        cd /app
        echo "[hydrate] Iniciando ingesta del corpus (EUR-Lex + CIRPASS + GS1 + ISO)..."
        uv run python -m app.rag.ingest 2>&1 | sed 's/^/[ingest] /' \
            || echo "[hydrate] ⚠ ingesta terminó con avisos (revisa logs)."

        echo "[hydrate] Indexando en ChromaDB (embeddings bge-m3)..."
        uv run python - <<'PY' 2>&1 | sed 's/^/[reindex] /'
from pathlib import Path
from app.rag.chunking import load_corpus
from app.rag.index import upsert_fragments

corpus_dir = Path("/app/data/corpus")
if not corpus_dir.exists():
    print("No hay corpus en disco, nada que indexar.")
else:
    n = upsert_fragments(load_corpus(corpus_dir))
    print(f"{n} fragments indexados.")
PY

        echo "[hydrate] ✓ Corpus listo. El chat ya puede citar normativa."
    ) &
else
    echo "[entrypoint] ChromaDB ya hidratado, saltando ingesta."
fi

echo "[entrypoint] Iniciando uvicorn..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
