from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlsplit

from app.colors.sampling import SamplingError, sample_image
from app.ingestion.extraction import extract_page
from app.ingestion.images import ImageCache
from app.ingestion.models import PageEvidence
from app.ingestion.service import ScrapingService
from app.ingestion.urls import IntakeError, normalize_url
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet
from app.services.compatibility import check_compatibility
from app.storage.repository import Repository
from app.workflows.models import IntakeRequest, ReviewRequired, WorkflowResult, WorkflowStep
from app.workflows.normalization import classify, explicit_colors, keyboard_from_evidence, keycaps_from_evidence


FIXTURE_KEYBOARD_URL = "https://fixtures.keycap.test/products/ansi-75"
FIXTURE_KEYCAP_URL = "https://fixtures.keycap.test/products/botanical-keycaps"
Progress = Callable[[WorkflowStep, str], Awaitable[None]]


class IngestionWorkflow:
    def __init__(self, repository: Repository, scraper: ScrapingService, data_dir: Path,
                 image_cache: ImageCache | None = None):
        self.repository = repository
        self.scraper = scraper
        self.data_dir = data_dir
        self.image_cache = image_cache or ImageCache(data_dir / "images")

    async def _evidence(self, url: str, *, refresh: bool) -> PageEvidence:
        normalized = normalize_url(url)
        fixtures = {
            FIXTURE_KEYBOARD_URL: "keyboard_product.html",
            FIXTURE_KEYCAP_URL: "keycap_product.html",
        }
        if normalized in fixtures:
            path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / fixtures[normalized]
            return extract_page(path.read_text(encoding="utf-8"), normalized)
        return (await self.scraper.scrape(normalized, refresh=refresh)).evidence

    async def _read_product(self, url: str, kind: str, *, refresh: bool, progress: Progress) -> PageEvidence:
        reader = "Firecrawl" if self.scraper.provider == "firecrawl" else "Playwright"
        host = urlsplit(url).hostname
        await progress(WorkflowStep.FETCHING_PAGE, f"Reading the {kind} product page on {host} with {reader}.")
        try:
            return await self._evidence(url, refresh=refresh)
        except IntakeError as error:
            raise IntakeError(f"{reader} could not read the {kind} page on {host}. {error}") from error

    async def _samples(self, evidence: PageEvidence) -> list:
        for candidate in evidence.images[:3]:
            try:
                path = await self.image_cache.download(candidate.url)
                return sample_image(path).colors
            except (OSError, SamplingError, ValueError):
                continue
        return []

    async def run(self, request: IntakeRequest, progress: Progress) -> WorkflowResult:
        keyboard_url = normalize_url(request.keyboard_url)
        keycap_url = normalize_url(request.keycap_url)
        if keyboard_url == keycap_url:
            raise IntakeError("Use two different product pages: a keyboard in the first field and a keycap set in the second.")
        warnings: list[str] = []
        cached: list[str] = []

        await progress(WorkflowStep.CHECKING_CACHE, "Checking normalized products saved on this computer.")
        keyboard = None if request.refresh else self.repository.find_product(keyboard_url, "keyboard")
        keycaps = None if request.refresh else self.repository.find_product(keycap_url, "keycaps")
        if keyboard:
            cached.append("keyboard")
        if keycaps:
            cached.append("keycaps")

        if keyboard is None:
            evidence = await self._read_product(keyboard_url, "keyboard", refresh=request.refresh, progress=progress)
            await progress(WorkflowStep.EXTRACTING_METADATA, "Extracted keyboard metadata and specifications.")
            await progress(WorkflowStep.CLASSIFYING_PRODUCT, "Checking that the first page describes a keyboard.")
            if classify(evidence) != "keyboard":
                raise ReviewRequired("The keyboard URL could not be confidently classified as a keyboard.", evidence.warnings, evidence)
            await progress(WorkflowStep.ANALYZING_LAYOUT, "Matching the keyboard to a canonical ANSI layout.")
            try:
                keyboard, notes = keyboard_from_evidence(evidence)
            except ReviewRequired as error:
                raise ReviewRequired(str(error), evidence.warnings + error.warnings, evidence) from error
            warnings.extend(evidence.warnings + notes)
            await progress(WorkflowStep.SAVING, "Saving the normalized keyboard locally.")
            keyboard = self.repository.save_product(keyboard, evidence)

        if keycaps is None:
            evidence = await self._read_product(keycap_url, "keycap", refresh=request.refresh, progress=progress)
            await progress(WorkflowStep.EXTRACTING_METADATA, "Extracted keycap metadata, variants, and images.")
            await progress(WorkflowStep.CLASSIFYING_PRODUCT, "Checking that the second page describes keycaps.")
            if classify(evidence) != "keycaps":
                raise ReviewRequired("The keycap URL could not be confidently classified as a keycap set.", evidence.warnings, evidence)
            await progress(WorkflowStep.EXTRACTING_COLORS, "Looking for explicit color codes, then usable image samples.")
            sampled = [] if explicit_colors(evidence) else await self._samples(evidence)
            try:
                keycaps, notes = keycaps_from_evidence(evidence, sampled)
            except ReviewRequired as error:
                raise ReviewRequired(str(error), evidence.warnings + error.warnings, evidence) from error
            warnings.extend(evidence.warnings + notes)
            await progress(WorkflowStep.SAVING, "Saving the normalized keycap set locally.")
            keycaps = self.repository.save_product(keycaps, evidence)

        if not isinstance(keyboard, KeyboardDefinition) or not isinstance(keycaps, KeycapSet):
            raise ReviewRequired("Cached products have unexpected types; manual review is required.")
        await progress(WorkflowStep.VALIDATING, "Validating normalized products and checking keycap fit evidence.")
        compatibility = check_compatibility(keyboard, keycaps)
        return WorkflowResult(keyboard=keyboard, keycap_set=keycaps, compatibility=compatibility,
                              warnings=list(dict.fromkeys(warnings)), cached_products=cached)
