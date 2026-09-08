from pathlib import Path

import httpx

from app.ingestion.cache import atomic_write, cache_key
from app.ingestion.urls import IntakeError, normalize_url, require_public_url

IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}


class ImageCache:
    """Download selected image candidates on demand, bounded and locally cached."""

    def __init__(self, directory: Path):
        self.directory = directory

    async def download(self, url: str) -> Path:
        url = normalize_url(url)
        key = cache_key(url)
        for extension in IMAGE_TYPES.values():
            path = self.directory / f"{key}{extension}"
            if path.is_file():
                return path
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
                current = url
                for _ in range(5):
                    current = await require_public_url(current)
                    async with client.stream("GET", current) as response:
                        if response.is_redirect:
                            if not response.headers.get("location"):
                                raise IntakeError("Image redirect has no destination.")
                            current = str(response.url.join(response.headers["location"]))
                            continue
                        response.raise_for_status()
                        extension = IMAGE_TYPES.get(response.headers.get("content-type", "").split(";")[0].strip())
                        if not extension:
                            raise IntakeError("Image URL did not return a supported raster image.")
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > 8_000_000:
                                raise IntakeError("Product image exceeds the 8 MB limit.")
                        if not data:
                            raise IntakeError("Product image was empty.")
                        path = self.directory / f"{key}{extension}"
                        atomic_write(path, bytes(data))
                        return path
                raise IntakeError("Too many image redirects.")
        except httpx.HTTPError as error:
            raise IntakeError("Could not download the product image.") from error
