import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.ingestion.browser import LoadedPage, PlaywrightPageLoader
from app.ingestion.firecrawl import FirecrawlPageLoader
from app.ingestion.service import ScrapingService
from app.ingestion.urls import IntakeError, normalize_url

HTML = (Path(__file__).parent / "fixtures" / "keyboard_product.html").read_text()


@pytest.fixture(autouse=True)
def public_urls(monkeypatch):
    monkeypatch.setattr("app.ingestion.firecrawl.require_public_url", AsyncMock(side_effect=normalize_url))


def response(html=HTML, **metadata):
    return {"success": True, "data": {"rawHtml": html, "metadata": {"statusCode": 200, **metadata}}}


def loader(handler):
    return FirecrawlPageLoader(SecretStr("test-only-key"), transport=httpx.MockTransport(handler))


def test_firecrawl_contract_preserves_raw_product_evidence(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://api.firecrawl.dev/v2/scrape"
        assert request.headers["authorization"] == "Bearer test-only-key"
        body = json.loads(request.content)
        assert body["formats"] == ["rawHtml"] and not body["onlyMainContent"]
        assert body["maxAge"] == 0
        return httpx.Response(200, json=response(sourceURL="https://example.com/board"))

    service = ScrapingService(tmp_path, loader(handler), provider="firecrawl", delay_seconds=0)
    result = asyncio.run(service.scrape("https://example.com/board"))
    assert result.provider == "firecrawl"
    assert result.evidence.products[0]["name"] == "Compact 75"
    assert result.evidence.variants == ["Black", "Silver"]
    assert asyncio.run(service.scrape("https://example.com/board")).cached
    assert len(calls) == 1
    asyncio.run(service.scrape("https://example.com/board", refresh=True))
    assert len(calls) == 2
    for path in tmp_path.rglob("*.json"):
        assert "test-only-key" not in path.read_text()


@pytest.mark.parametrize("status,fragment", [(401, "authentication"), (403, "denied"), (402, "credits"), (429, "rate limit"), (500, "HTTP 500")])
def test_errors_are_actionable_and_do_not_leak_server_body(status, fragment):
    provider = loader(lambda request: httpx.Response(status, text="test-only-key"))
    with pytest.raises(IntakeError, match=fragment) as error:
        asyncio.run(provider.load("https://example.com/board"))
    assert "test-only-key" not in str(error.value)


@pytest.mark.parametrize("data", [
    {"success": False}, {"success": True},
    {"success": True, "data": {"markdown": "not raw HTML"}},
    response(html=" "), response(error="blocked"), response(statusCode=404),
])
def test_incomplete_or_failed_responses_are_not_success(data):
    with pytest.raises(IntakeError):
        asyncio.run(loader(lambda request: httpx.Response(200, json=data)).load("https://example.com/board"))


def test_timeout_is_clean():
    def handler(request):
        raise httpx.ReadTimeout("test-only-key", request=request)
    with pytest.raises(IntakeError, match="timed out") as error:
        asyncio.run(loader(handler).load("https://example.com/board"))
    assert "test-only-key" not in str(error.value)


def test_non_json_response_is_clean():
    with pytest.raises(IntakeError, match="malformed data"):
        asyncio.run(loader(lambda request: httpx.Response(200, text="<html>upstream error</html>")).load("https://example.com/board"))


def test_oversized_html_is_rejected():
    with pytest.raises(IntakeError, match="20 MB"):
        asyncio.run(loader(lambda request: httpx.Response(200, json=response(html="x" * 20_000_001))).load("https://example.com/board"))


def test_private_final_url_is_rejected():
    with pytest.raises(IntakeError, match="Private network"):
        asyncio.run(loader(lambda request: httpx.Response(200, json=response(url="http://127.0.0.1"))).load("https://example.com/board"))


def test_providers_have_separate_caches(tmp_path):
    first = AsyncMock(load=AsyncMock(return_value=LoadedPage(HTML, "https://example.com/board")))
    second = AsyncMock(load=AsyncMock(return_value=LoadedPage(HTML, "https://example.com/board")))
    asyncio.run(ScrapingService(tmp_path, first, delay_seconds=0).scrape("https://example.com/board"))
    result = asyncio.run(ScrapingService(tmp_path, second, provider="firecrawl", delay_seconds=0).scrape("https://example.com/board"))
    assert not result.cached and result.provider == "firecrawl"
    second.load.assert_awaited_once()


def test_default_is_local_and_firecrawl_requires_a_key(tmp_path):
    assert isinstance(ScrapingService(tmp_path).loader, PlaywrightPageLoader)
    with pytest.raises(IntakeError, match="FIRECRAWL_API_KEY"):
        ScrapingService(tmp_path, provider="firecrawl")


def test_settings_support_dotenv_and_mask_the_key(tmp_path):
    path = tmp_path / ".env"
    path.write_text("FIRECRAWL_API_KEY=test-only-key\nSCRAPER_PROVIDER=firecrawl\n")
    settings = Settings(_env_file=path)
    assert settings.scraper_provider == "firecrawl"
    assert settings.firecrawl_api_key.get_secret_value() == "test-only-key"
    assert "test-only-key" not in repr(settings)
