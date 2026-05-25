"""Cache HTTP en disco para descargas del corpus.

Política: GET texto, cache en disco bajo `cache_dir/<cache_key>`, validar
tamaño mínimo (descarta cache corrupta truncada). Reintentos con backoff
exponencial en errores de red.
"""

import time
from pathlib import Path

import httpx

DEFAULT_HEADERS = {
    "User-Agent": "PasaporteAbierto-corpus-ingest/0.1 (+https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas)",
    "Accept-Language": "es;q=1.0, en;q=0.9",
}


class CachedHttpClient:
    """Cliente httpx con cache en disco y reintentos."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
        min_size: int = 1024,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout_seconds,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        )
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.min_size = min_size

    def get_text(self, url: str, *, cache_key: str, force_refresh: bool = False) -> str:
        cache_path = self.cache_dir / cache_key
        if not force_refresh and cache_path.exists():
            data = cache_path.read_text(encoding="utf-8")
            if len(data) >= self.min_size:
                return data
            # cache corrupta o truncada: descartar
            cache_path.unlink()

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(url)
                response.raise_for_status()
                body = response.text
                cache_path.write_text(body, encoding="utf-8")
                return body
            except (httpx.HTTPError, httpx.ConnectError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_base_seconds * (2**attempt))
        assert last_error is not None
        raise last_error

    def close(self) -> None:
        self._client.close()
