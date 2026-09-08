import asyncio
from dataclasses import dataclass

from playwright.async_api import Error as BrowserError, async_playwright

from app.ingestion.urls import IntakeError, require_public_url


@dataclass(frozen=True)
class LoadedPage:
    html: str
    final_url: str


class PlaywrightPageLoader:
    async def load(self, url: str) -> LoadedPage:
        await require_public_url(url)
        try:
            # Include browser startup, navigation, rendering, and shutdown in a deadline.
            async with asyncio.timeout(45):
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=True)
                    try:
                        context = await browser.new_context(
                            service_workers="block", accept_downloads=False,
                            user_agent="KeycapColorizer/0.1 (local product preview)",
                        )

                        async def guard(route):
                            if route.request.resource_type in {"media", "font"}:
                                await route.abort()
                                return
                            try:
                                await require_public_url(route.request.url)
                            except IntakeError:
                                await route.abort()
                            else:
                                await route.continue_()

                        await context.route("**/*", guard)
                        page = await context.new_page()
                        response = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                        if response is None or not response.ok:
                            raise IntakeError(f"Product page returned HTTP {response.status if response else 'no response'}.")
                        content_type = response.headers.get("content-type", "").lower()
                        if "html" not in content_type:
                            raise IntakeError("Product URL did not return an HTML page.")
                        # A bounded rendering window also works on pages with perpetual analytics requests.
                        await page.wait_for_timeout(1200)
                        final_url = await require_public_url(page.url)
                        html = await page.content()
                        if len(html.encode("utf-8")) > 20_000_000:
                            raise IntakeError("Product page exceeds the 20 MB extraction limit.")
                        return LoadedPage(html, final_url)
                    finally:
                        await browser.close()
        except (TimeoutError, BrowserError) as error:
            message = str(error)
            if "Executable doesn't exist" in message:
                raise IntakeError("Chromium is not installed. Run: python -m playwright install chromium") from error
            raise IntakeError("Could not load product page. It may be unavailable, blocked, or timed out.") from error
