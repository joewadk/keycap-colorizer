import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from pydantic import SecretStr

from app.ingestion.browser import LoadedPage, PlaywrightPageLoader
from app.ingestion.cache import PageCache
from app.ingestion.extraction import extract_page
from app.ingestion.firecrawl import FirecrawlPageLoader
from app.ingestion.models import ScrapeResult
from app.ingestion.urls import normalize_url


class PageLoader(Protocol):
    async def load(self, url: str) -> LoadedPage: ...


class ScrapingService:
    def __init__(self, data_dir: Path, loader: PageLoader | None = None, *, ttl_seconds=86400, delay_seconds=1.0,
                 provider: Literal["playwright", "firecrawl"] = "playwright", api_key: SecretStr | None = None):
        if provider not in {"playwright", "firecrawl"}:
            raise ValueError("Unknown scraping provider.")
        self.provider = provider
        self.loader = loader or (FirecrawlPageLoader(api_key or SecretStr("")) if provider == "firecrawl" else PlaywrightPageLoader())
        directory = data_dir / "cache" / "pages"
        if provider == "firecrawl":
            directory /= "firecrawl"
        self.cache = PageCache(directory, ttl_seconds)
        self.delay_seconds = delay_seconds
        self.lock = asyncio.Lock()

    async def scrape(self, url: str, *, refresh: bool = False) -> ScrapeResult:
        url = normalize_url(url)
        # One page at a time avoids duplicate loads and simultaneous vendor requests.
        async with self.lock:
            if not refresh:
                cached = self.cache.get(url)
                if cached and cached.provider == self.provider:
                    return cached
            await asyncio.sleep(self.delay_seconds)
            page = await self.loader.load(url)
            result = ScrapeResult(
                provider=self.provider,
                evidence=extract_page(page.html, url, page.final_url), cached=False,
                fetched_at=datetime.now(timezone.utc),
            )
            self.cache.put(url, result, page.html)
            return result
