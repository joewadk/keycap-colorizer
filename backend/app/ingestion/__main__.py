import argparse
import asyncio
from pathlib import Path

from app.config import get_settings
from app.ingestion.images import ImageCache
from app.ingestion.service import ScrapingService
from app.ingestion.urls import IntakeError


async def run() -> None:
    parser = argparse.ArgumentParser(description="Inspect a product page and cache raw evidence locally.")
    parser.add_argument("url")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--provider", choices=["playwright", "firecrawl"], help="Override SCRAPER_PROVIDER for this request")
    parser.add_argument("--images", type=int, choices=range(0, 6), default=0, help="Download up to five candidate images")
    args = parser.parse_args()
    settings = get_settings()
    directory = Path(settings.data_dir)
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[3] / directory
    try:
        service = ScrapingService(directory, provider=args.provider or settings.scraper_provider, api_key=settings.firecrawl_api_key)
        result = await service.scrape(args.url, refresh=args.refresh)
        if args.images:
            cache = ImageCache(directory / "images")
            for image in result.evidence.images[:args.images]:
                await cache.download(image.url)
        print(result.model_dump_json(indent=2))
    except (IntakeError, OSError) as error:
        parser.exit(1, f"Product intake failed: {error}\n")


if __name__ == "__main__":
    asyncio.run(run())
