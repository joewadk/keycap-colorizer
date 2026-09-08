import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.ingestion.images import ImageCache
from app.ingestion.urls import IntakeError, normalize_url


def transport(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr("app.ingestion.images.require_public_url", AsyncMock(side_effect=normalize_url))
    monkeypatch.setattr("app.ingestion.images.httpx.AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


def test_downloaded_image_is_cached_without_a_second_request(tmp_path, monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"fixture image bytes")

    transport(monkeypatch, handler)
    cache = ImageCache(tmp_path)
    path = asyncio.run(cache.download("https://example.com/caps.png"))
    assert path.read_bytes() == b"fixture image bytes"
    assert asyncio.run(cache.download("https://example.com/caps.png")) == path
    assert len(requests) == 1


@pytest.mark.parametrize("content_type,body,reason", [
    ("text/html", b"error page", "supported raster"),
    ("image/png", b"", "empty"),
    ("image/png", b"x" * 8_000_001, "8 MB"),
], ids=["wrong-type", "empty", "oversized"])
def test_invalid_images_are_not_cached(tmp_path, monkeypatch, content_type, body, reason):
    transport(monkeypatch, lambda request: httpx.Response(200, headers={"content-type": content_type}, content=body))
    with pytest.raises(IntakeError, match=reason):
        asyncio.run(ImageCache(tmp_path).download("https://example.com/image"))
    assert not list(tmp_path.iterdir())


def test_image_redirect_to_local_network_is_rejected(tmp_path, monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/private"}))
    with pytest.raises(IntakeError, match="Private network"):
        asyncio.run(ImageCache(tmp_path).download("https://example.com/image"))


def test_image_http_error_is_clean(tmp_path, monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(404))
    with pytest.raises(IntakeError, match="Could not download"):
        asyncio.run(ImageCache(tmp_path).download("https://example.com/image"))
