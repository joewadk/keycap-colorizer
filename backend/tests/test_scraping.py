import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.ingestion.browser import LoadedPage
from app.ingestion.cache import cache_key
from app.ingestion.service import ScrapingService
from app.ingestion.urls import IntakeError, require_public_url

HTML = (Path(__file__).parent / "fixtures" / "keyboard_product.html").read_text()


def loader():
    return AsyncMock(load=AsyncMock(return_value=LoadedPage(HTML, "https://example.com/board")))


def test_cache_avoids_repeat_loads_and_retains_html(tmp_path):
    mocked = loader()
    service = ScrapingService(tmp_path, mocked, delay_seconds=0)
    first = asyncio.run(service.scrape("https://EXAMPLE.com/board#gallery"))
    second = asyncio.run(service.scrape("https://example.com/board"))
    assert not first.cached and second.cached
    assert first.evidence == second.evidence
    assert mocked.load.await_count == 1
    assert list((tmp_path / "cache" / "pages").glob("*.html"))


def test_refresh_and_expiry_reload(tmp_path):
    mocked = loader()
    service = ScrapingService(tmp_path, mocked, delay_seconds=0)
    asyncio.run(service.scrape("https://example.com/board"))
    asyncio.run(service.scrape("https://example.com/board", refresh=True))
    service.cache.ttl_seconds = -1
    asyncio.run(service.scrape("https://example.com/board"))
    assert mocked.load.await_count == 3


def test_corrupt_cache_is_recovered(tmp_path):
    mocked = loader()
    service = ScrapingService(tmp_path, mocked, delay_seconds=0)
    service.cache.directory.mkdir(parents=True)
    (service.cache.directory / f"{cache_key('https://example.com/board')}.json").write_text("broken")
    assert not asyncio.run(service.scrape("https://example.com/board")).cached


def test_concurrent_same_product_loads_once(tmp_path):
    mocked = loader()
    service = ScrapingService(tmp_path, mocked, delay_seconds=0)

    async def run():
        return await asyncio.gather(*(service.scrape("https://example.com/board") for _ in range(3)))

    results = asyncio.run(run())
    assert sum(result.cached for result in results) == 2
    assert mocked.load.await_count == 1


def test_failures_do_not_create_success_cache(tmp_path):
    mocked = loader()
    mocked.load.side_effect = IntakeError("Page blocked")
    with pytest.raises(IntakeError, match="blocked"):
        asyncio.run(ScrapingService(tmp_path, mocked, delay_seconds=0).scrape("https://example.com/board"))
    assert not list(tmp_path.rglob("*.json"))


def test_dns_private_hosts_are_rejected():
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 0))]):
        with pytest.raises(IntakeError, match="public addresses"):
            asyncio.run(require_public_url("https://example.com/board"))
