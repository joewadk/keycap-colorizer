import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as BrowserError

from app.ingestion.browser import PlaywrightPageLoader
from app.ingestion.urls import IntakeError, normalize_url


def setup_browser(monkeypatch, status=200):
    page = SimpleNamespace(
        goto=AsyncMock(return_value=SimpleNamespace(ok=status < 400, status=status, headers={"content-type": "text/html"})),
        wait_for_timeout=AsyncMock(), content=AsyncMock(return_value="<title>Dynamic product</title>"),
        url="https://example.com/final-product",
    )
    context = SimpleNamespace(route=AsyncMock(), new_page=AsyncMock(return_value=page))
    browser = SimpleNamespace(new_context=AsyncMock(return_value=context), close=AsyncMock())
    chromium = SimpleNamespace(launch=AsyncMock(return_value=browser))
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=SimpleNamespace(chromium=chromium))
    manager.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("app.ingestion.browser.async_playwright", lambda: manager)
    monkeypatch.setattr("app.ingestion.browser.require_public_url", AsyncMock(side_effect=normalize_url))
    return page, context, browser, chromium


def test_browser_returns_rendered_html_and_closes(monkeypatch):
    page, context, browser, _ = setup_browser(monkeypatch)
    result = asyncio.run(PlaywrightPageLoader().load("https://example.com/item"))
    assert result.html == "<title>Dynamic product</title>"
    assert result.final_url == page.url
    browser.close.assert_awaited_once()
    context.route.assert_awaited_once()


def test_http_failure_closes_browser(monkeypatch):
    _, _, browser, _ = setup_browser(monkeypatch, status=403)
    with pytest.raises(IntakeError, match="403"):
        asyncio.run(PlaywrightPageLoader().load("https://example.com/item"))
    browser.close.assert_awaited_once()


def test_missing_chromium_has_actionable_error(monkeypatch):
    _, _, _, chromium = setup_browser(monkeypatch)
    chromium.launch.side_effect = BrowserError("Executable doesn't exist")
    with pytest.raises(IntakeError, match="playwright install chromium"):
        asyncio.run(PlaywrightPageLoader().load("https://example.com/item"))


def test_navigation_requests_to_local_addresses_are_blocked(monkeypatch):
    _, context, _, _ = setup_browser(monkeypatch)
    asyncio.run(PlaywrightPageLoader().load("https://example.com/item"))
    guard = context.route.call_args.args[1]
    route = SimpleNamespace(request=SimpleNamespace(resource_type="document", url="http://127.0.0.1/"), abort=AsyncMock(), continue_=AsyncMock())
    asyncio.run(guard(route))
    route.abort.assert_awaited_once()
    route.continue_.assert_not_awaited()
