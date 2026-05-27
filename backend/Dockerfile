FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Crea el directorio de datos antes de exponer el puerto. El volume
# `backend_data:/app/data` de docker-compose lo monta encima en runtime,
# pero `docker run` aislado (sin volume) necesita que exista para que
# SQLite pueda abrir la DB sin "unable to open database file".
RUN mkdir -p /app/data

EXPOSE 8000

# start-period generoso: la primera vez aplica migraciones e inicializa
# el cliente de Chroma antes de que uvicorn empiece a responder.
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
