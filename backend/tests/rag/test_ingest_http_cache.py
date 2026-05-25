"""Tests del cache HTTP del ingestor."""

from pathlib import Path

import httpx
import pytest

from app.rag.ingest.http_cache import CachedHttpClient


def test_cache_hits_on_second_call(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text="<html>hola</html>")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport, min_size=10)

    body1 = client.get_text("https://example.com/foo.html", cache_key="foo")
    body2 = client.get_text("https://example.com/foo.html", cache_key="foo")

    assert body1 == body2 == "<html>hola</html>"
    assert calls["n"] == 1, "segunda llamada debe ir a cache"
    assert (tmp_path / "foo").exists()


def test_force_refresh_bypasses_cache(tmp_path: Path) -> None:
    bodies = iter(["<html>v1</html>", "<html>v2</html>"])
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text=next(bodies))

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport, min_size=10)

    first = client.get_text("https://example.com/foo.html", cache_key="foo")
    second = client.get_text("https://example.com/foo.html", cache_key="foo", force_refresh=True)

    assert first == "<html>v1</html>"
    assert second == "<html>v2</html>"
    assert calls["n"] == 2


def test_retries_then_succeeds(tmp_path: Path) -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectError("flaky")
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport)
    body = client.get_text("https://example.com/foo.html", cache_key="foo")
    assert body == "ok"
    assert attempts["n"] == 3


def test_raises_after_max_retries(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("always down")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport)
    with pytest.raises(httpx.ConnectError):
        client.get_text("https://example.com/foo.html", cache_key="foo")


def test_corrupted_cache_is_redownloaded(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text="<html>" + "x" * 5000 + "</html>")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport, min_size=100)

    (tmp_path / "foo").write_text("tiny")  # cache "corrupta": < min_size
    body = client.get_text("https://example.com/foo.html", cache_key="foo")

    assert calls["n"] == 1, "cache truncada debe descartarse y re-descargar"
    assert len(body) > 100
