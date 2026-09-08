import asyncio

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from app.ingestion.browser import LoadedPage
from app.ingestion.urls import IntakeError, require_public_url


class FirecrawlMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_url: str | None = Field(default=None, alias="sourceURL")
    url: str | None = None
    status_code: int | None = Field(default=None, alias="statusCode")
    error: str | None = None


class FirecrawlDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    raw_html: str = Field(alias="rawHtml", min_length=1)
    metadata: FirecrawlMetadata = Field(default_factory=FirecrawlMetadata)


class FirecrawlResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    success: bool
    data: FirecrawlDocument | None = None


class FirecrawlPageLoader:
    def __init__(self, api_key: SecretStr, *, transport: httpx.AsyncBaseTransport | None = None):
        if not api_key.get_secret_value().strip():
            raise IntakeError("Firecrawl is disabled. Set FIRECRAWL_API_KEY in the project .env, or use --provider playwright.")
        self.api_key = api_key
        self.transport = transport

    async def load(self, url: str) -> LoadedPage:
        url = await require_public_url(url)
        try:
            async with asyncio.timeout(65):
                async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False, transport=self.transport) as client:
                    async with client.stream(
                        "POST", "https://api.firecrawl.dev/v2/scrape",
                        headers={"Authorization": f"Bearer {self.api_key.get_secret_value()}"},
                        json={
                            "url": url, "formats": ["rawHtml"], "onlyMainContent": False,
                            "timeout": 45000, "waitFor": 1200,
                            # Our local TTL/refresh controls freshness, not Firecrawl's cache.
                            "maxAge": 0,
                        },
                    ) as response:
                        if response.status_code != 200:
                            messages = {
                                401: "Firecrawl authentication failed. Check FIRECRAWL_API_KEY.",
                                403: "Firecrawl denied access to this request.",
                                402: "Firecrawl credits are unavailable. Check your Firecrawl account.",
                                429: "Firecrawl rate limit reached. Try again later.",
                            }
                            raise IntakeError(messages.get(response.status_code, f"Firecrawl returned HTTP {response.status_code}."))
                        payload = bytearray()
                        async for chunk in response.aiter_bytes():
                            payload.extend(chunk)
                            if len(payload) > 30_000_000:
                                raise IntakeError("Firecrawl response exceeds the 30 MB limit.")
                try:
                    result = FirecrawlResponse.model_validate_json(bytes(payload))
                except ValidationError:
                    # Provider payloads may echo credentials or page content: don't expose them.
                    raise IntakeError("Firecrawl returned malformed data or no raw HTML.") from None
                if not result.success or result.data is None:
                    raise IntakeError("Firecrawl could not scrape this product page.")
                document = result.data
                if document.metadata.error or (document.metadata.status_code is not None and document.metadata.status_code >= 400):
                    raise IntakeError("Firecrawl reported an error loading the product page.")
                if not document.raw_html.strip():
                    raise IntakeError("Firecrawl returned empty HTML.")
                if len(document.raw_html.encode("utf-8")) > 20_000_000:
                    raise IntakeError("Product page exceeds the 5 MB extraction limit.")
                final_url = await require_public_url(document.metadata.url or document.metadata.source_url or url)
                return LoadedPage(document.raw_html, final_url)
        except (httpx.HTTPError, TimeoutError):
            raise IntakeError("Firecrawl request failed or timed out. Try again or use --provider playwright.") from None
