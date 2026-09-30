import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.ingestion.models import ScrapeResult
from app.ingestion.urls import normalize_url


def cache_key(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def recover_image_candidates(directory: Path, evidence):
    """Reparse locally retained HTML so pre-upgrade 30-image caches need no paid refresh."""
    from app.ingestion.extraction import extract_page
    path = directory / f"{cache_key(evidence.source_url)}.html"
    try:
        with path.open("rb") as stream:
            html = stream.read(20_000_001)
        if len(html) > 20_000_000:
            return
        recovered = extract_page(html.decode("utf-8"), evidence.source_url, evidence.final_url)
    except (OSError, UnicodeError, ValueError):
        return
    known = {image.url for image in evidence.images}
    for image in recovered.images:
        if image.url not in known:
            evidence.images.append(image)
            known.add(image.url)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class PageCache:
    def __init__(self, directory: Path, ttl_seconds: float = 86400):
        self.directory = directory
        self.ttl_seconds = ttl_seconds

    def get(self, url: str) -> ScrapeResult | None:
        path = self.directory / f"{cache_key(url)}.json"
        try:
            cached = ScrapeResult.model_validate_json(path.read_text(encoding="utf-8"))
            age = (datetime.now(timezone.utc) - cached.fetched_at).total_seconds()
            if cached.evidence.source_url != normalize_url(url) or age < 0 or age > self.ttl_seconds:
                return None
            recover_image_candidates(self.directory, cached.evidence)
            return cached.model_copy(update={"cached": True})
        except (OSError, ValidationError, ValueError, TypeError):
            return None

    def put(self, url: str, result: ScrapeResult, html: str) -> None:
        key = cache_key(url)
        atomic_write(self.directory / f"{key}.html", html.encode("utf-8"))
        atomic_write(self.directory / f"{key}.json", result.model_dump_json().encode("utf-8"))
