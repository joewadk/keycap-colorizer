"""Independent product reviews: explicit image/crop selection before applying colors."""
import asyncio
import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response
from pydantic import Field

from app.api.ingestion import SettingsDep, _root_path
from app.api.storage import Repo
from app.colors.sampling import Crop, SamplingError, _decode, sample_image
from app.colors.quick_fit import quick_fit
from app.ingestion.cache import atomic_write, recover_image_candidates
from app.ingestion.images import ImageCache
from app.ingestion.models import PageEvidence, ProductImage
from app.ingestion.service import ScrapingService
from app.ingestion.urls import IntakeError, normalize_url
from app.layouts import LayoutTemplate, build_keyboard_from_template
from app.models.base import DomainModel
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet
from app.storage.repository import NotFound
from app.workflows.models import ReviewRequired
from app.workflows.normalization import classify, explicit_colors, keyboard_from_evidence, keycaps_from_evidence
from app.workflows.service import FIXTURE_KEYBOARD_URL, FIXTURE_KEYCAP_URL, IngestionWorkflow

router = APIRouter(prefix="/ingestion", tags=["photo review"])
REVIEW_VERSION = "photo-review-2"


class Prepare(DomainModel):
    kind: Literal["keyboard", "keycaps"]
    url: str = ""
    provider: Literal["playwright", "firecrawl"] = "playwright"
    manual: bool = False


class Sample(DomainModel):
    image_index: int = Field(ge=0)
    crop: Crop


class QuickFit(Sample):
    layout: Literal["ANSI_65", "ANSI_75", "ANSI_TKL"]
    strategy: Literal["scheme", "positions"] = "scheme"


class KeySample(DomainModel):
    sample_id: str
    color_id: str


class Confirm(DomainModel):
    name: str = Field(min_length=1, max_length=200)
    variant: str = Field(default="", max_length=200)
    layout: Literal["ANSI_65", "ANSI_75", "ANSI_TKL"] | None = None
    sample_id: str | None = None
    color_ids: list[str] = Field(default_factory=list, max_length=12)
    use_explicit_colors: bool = False
    key_samples: dict[str, KeySample] = Field(default_factory=dict, max_length=128)


def sessions(request: Request):
    return request.app.state.photo_reviews


def session(request: Request, review_id: str):
    item = sessions(request).get(review_id)
    if item is None:
        raise NotFound("Photo review expired or the backend restarted. Read the product again or upload a photo.")
    return item


def payload(review_id, item):
    evidence = item["evidence"]
    board = item["keyboard"]
    layout = {"65": "ANSI_65", "75": "ANSI_75", "TKL": "ANSI_TKL"}.get(board.layout_type) if board else None
    return {"id": review_id, "kind": item["kind"], "title": evidence.title,
            "sourceUrl": evidence.source_url, "images": [image.model_dump() for image in evidence.images],
            "variants": evidence.variants, "layout": layout,
            "colors": [color.model_dump() for color in explicit_colors(evidence)],
            "warnings": item["warnings"], "cached": item["cached"]}


@router.get("/version")
def version():
    return {"version": REVIEW_VERSION}


@router.post("/reviews")
async def prepare(body: Prepare, request: Request, repository: Repo, settings: SettingsDep):
    review_id = str(uuid4())
    root = Path(__file__).resolve().parents[3]
    data_dir = _root_path(settings.data_dir, root)
    url = normalize_url(body.url) if body.url else f"https://local.keycap.test/manual/{review_id}"
    cached = False
    if body.manual:
        evidence = PageEvidence(source_url=url, final_url=url, title="My keyboard" if body.kind == "keyboard" else "My keycaps")
    else:
        if not body.url:
            raise IntakeError("Enter a product URL or choose Upload a photo.")
        stored = repository.find_product(url, body.kind)
        evidence = repository.get_evidence(stored.id) if stored else None
        cached = evidence is not None
        if evidence is None:
            try:
                provider = "playwright" if url in {FIXTURE_KEYBOARD_URL, FIXTURE_KEYCAP_URL} else body.provider
                scraper = ScrapingService(data_dir, provider=provider, api_key=settings.firecrawl_api_key)
                workflow = IngestionWorkflow(repository, scraper, data_dir)
                evidence = await workflow._evidence(url, refresh=False)
            except IntakeError as error:
                raise IntakeError(f"{body.provider.title()} could not read the {body.kind} page. {error} You can upload a product photo instead.") from error
    notes = list(evidence.warnings)
    if cached:
        for directory in (data_dir / "cache" / "pages", data_dir / "cache" / "pages" / "firecrawl"):
            await asyncio.to_thread(recover_image_candidates, directory, evidence)
    board = None
    if not body.manual and classify(evidence) != body.kind:
        notes.append("Product type is uncertain. Check the title and photo before confirming this product.")
    if body.kind == "keyboard":
        try:
            board, _ = keyboard_from_evidence(evidence)
        except ReviewRequired:
            notes.append("Choose the matching supported layout. Other sizes and ISO layouts are not supported yet.")
        notes.append("Geometry is a generic ANSI template. Select a case-only crop to sample the housing color.")
    else:
        notes.append("Select a crop covering keycap surfaces; exclude the case and photo background.")
    item = {"kind": body.kind, "evidence": evidence, "keyboard": board, "warnings": notes,
            "cached": cached, "data_dir": data_dir, "files": {}, "samples": {}}
    if url in {FIXTURE_KEYBOARD_URL, FIXTURE_KEYCAP_URL}:
        # Synthetic demo photo deliberately includes distinct housing, keys, and background.
        # It exercises the same crop/download/sample review path without vendor calls.
        from PIL import Image, ImageDraw
        image = Image.new("RGB", (400, 200), "#FFFFFF")
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 379, 179), fill="#245577")
        draw.rectangle((60, 60, 199, 139), fill="#D8DBD1")
        draw.rectangle((200, 60, 339, 139), fill="#C5795E")
        output = BytesIO()
        image.save(output, format="PNG")
        path = data_dir / "images" / "review-demo.png"
        atomic_write(path, output.getvalue())
        evidence.images = [ProductImage(url="https://local.keycap.test/photos/review-demo.png", alt="Demo: blue housing, bone and clay keycaps, white background")]
        item["files"][0] = path
    pool = sessions(request)
    if len(pool) >= 100:
        pool.pop(next(iter(pool)))
    pool[review_id] = item
    return payload(review_id, item)


async def image_path(item, index):
    if not 0 <= index < len(item["evidence"].images):
        raise NotFound("Product image not found.")
    if index not in item["files"]:
        url = item["evidence"].images[index].url
        parts = urlsplit(url)
        filename = Path(parts.path).name
        if parts.hostname == "local.keycap.test" and (re.fullmatch(r"upload-[0-9a-f-]{36}\.image", filename) or filename == "review-demo.png"):
            path = item["data_dir"] / "images" / filename
            if not path.is_file():
                raise NotFound("Local photo is missing. Upload it again.")
            item["files"][index] = path
        else:
            item["files"][index] = await ImageCache(item["data_dir"] / "images").download(url)
    return item["files"][index]


@router.get("/reviews/{review_id}/images/{index}")
async def photo(review_id: str, index: int, request: Request):
    item = session(request, review_id)
    path = await image_path(item, index)
    try:
        image = await asyncio.to_thread(_decode, path, Crop())
    except SamplingError as error:
        raise IntakeError(str(error)) from error
    output = BytesIO()
    image.save(output, format="PNG")
    return Response(output.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/reviews/{review_id}/upload")
async def upload(review_id: str, request: Request):
    item = session(request, review_id)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8_000_000:
            raise IntakeError("Photo exceeds the 8 MB limit.")
    path = item["data_dir"] / "images" / f"upload-{uuid4()}.image"
    # Validate in memory before storing untrusted bytes.
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(BytesIO(data), formats=["PNG", "JPEG", "WEBP", "GIF"]) as image:
            if image.width * image.height > 16_000_000 or max(image.size) > 8192 or getattr(image, "is_animated", False):
                raise IntakeError("Choose a still photo up to 16 megapixels and 8192 pixels per side.")
            image.verify()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise IntakeError("Invalid photo. Choose PNG, JPEG, WebP, or still GIF.") from error
    atomic_write(path, bytes(data))
    index = len(item["evidence"].images)
    item["files"][index] = path
    item["evidence"].images.append(ProductImage(url=f"https://local.keycap.test/photos/{path.name}", alt="Uploaded product photo"))
    return {"review": payload(review_id, item), "imageIndex": index}


@router.post("/reviews/{review_id}/sample")
async def sample(review_id: str, body: Sample, request: Request):
    item = session(request, review_id)
    path = await image_path(item, body.image_index)
    try:
        palette = await asyncio.to_thread(sample_image, path, crop=body.crop)
    except SamplingError as error:
        raise IntakeError(str(error)) from error
    sample_id = str(uuid4())
    # Bound retained samples; old client proposals must be resampled if evicted.
    if len(item["samples"]) >= 256:
        item["samples"].pop(next(iter(item["samples"])))
    item["samples"][sample_id] = (palette, body)
    return {"id": sample_id, **palette.model_dump(), "imageIndex": body.image_index, "crop": body.crop.model_dump()}


@router.post("/reviews/{review_id}/quick-fit")
async def fit(review_id: str, body: QuickFit, request: Request):
    item = session(request, review_id)
    if item["kind"] != "keycaps":
        raise IntakeError("Quick fit is for keycaps. Crop the housing separately for case color.")
    path = await image_path(item, body.image_index)
    board = build_keyboard_from_template(LayoutTemplate(body.layout), keyboard_id="fit",
        manufacturer="Generic", model="Quick fit", source_url=item["evidence"].source_url)
    try:
        palette, assignments = await asyncio.to_thread(quick_fit, path, board, body.crop, body.strategy)
    except SamplingError as error:
        raise IntakeError(str(error)) from error
    sample_id = str(uuid4())
    if len(item["samples"]) >= 256:
        item["samples"].pop(next(iter(item["samples"])))
    item["samples"][sample_id] = (palette, Sample(image_index=body.image_index, crop=body.crop))
    return {"id": sample_id, **palette.model_dump(), "keyColorMap": assignments,
            "imageIndex": body.image_index, "crop": body.crop.model_dump()}


@router.post("/reviews/{review_id}/confirm")
def confirm(review_id: str, body: Confirm, request: Request, repository: Repo):
    item = session(request, review_id)
    evidence = item["evidence"].model_copy(deep=True)
    evidence.title = body.name
    notes = list(item["warnings"])
    colors = []
    if body.sample_id:
        proposal = item["samples"].get(body.sample_id)
        if proposal is None:
            raise IntakeError("Color proposal expired. Sample the crop again.")
        palette, sampled = proposal
        colors = palette.colors
        notes.extend(palette.warnings)
        evidence.warnings.append(f"User-reviewed photo: {evidence.images[sampled.image_index].url}; crop: {sampled.crop.model_dump_json()}; variant: {body.variant}")
    elif body.use_explicit_colors:
        colors = explicit_colors(evidence)
    if body.color_ids:
        if len(set(body.color_ids)) != len(body.color_ids) or not set(body.color_ids).issubset({c.id for c in colors}):
            raise IntakeError("Choose colors from the current proposal.")
        colors = [c for c in colors if c.id in body.color_ids]
    else:
        colors = []
    key_color_map = {}
    if body.key_samples:
        if item["kind"] != "keycaps" or body.layout is None:
            raise IntakeError("Per-key colors require a keycap review and a supported keyboard layout.")
        template = build_keyboard_from_template(LayoutTemplate(body.layout), keyboard_id="review-layout",
            manufacturer="Generic", model="Review", source_url=evidence.source_url)
        if not set(body.key_samples).issubset({key.id for key in template.keys}):
            raise IntakeError("Per-key assignments contain keys outside the selected layout.")
        by_id = {color.id: color for color in colors}
        for key_id, choice in body.key_samples.items():
            proposal = item["samples"].get(choice.sample_id)
            if proposal is None:
                raise IntakeError(f"Sample for {key_id} expired. Sample that key again.")
            palette, sampled = proposal
            color = next((c for c in palette.colors if c.id == choice.color_id), None)
            if color is None:
                raise IntakeError(f"Choose a sampled color for {key_id}.")
            by_id[color.id] = color.model_copy(update={"name": f"Photo {color.hex}"})
            key_color_map[key_id] = color.id
            evidence.warnings.append(f"Key {key_id}: {color.hex}; photo: {evidence.images[sampled.image_index].url}; crop: {sampled.crop.model_dump_json()}")
            notes.extend(palette.warnings)
        colors = list(by_id.values())
    name = body.name + (f" — {body.variant}" if body.variant else "")
    identifier = f"{item['kind']}-review-{uuid4()}"
    if item["kind"] == "keyboard":
        if body.layout is None:
            raise IntakeError("Choose a supported ANSI keyboard layout.")
        if body.sample_id and len(colors) != 1:
            raise IntakeError("Select exactly one sampled case color.")
        layout = {"ANSI_65": LayoutTemplate.ANSI_65, "ANSI_75": LayoutTemplate.ANSI_75, "ANSI_TKL": LayoutTemplate.ANSI_TKL}[body.layout]
        original = item["keyboard"]
        product = build_keyboard_from_template(layout, keyboard_id=identifier,
            manufacturer=original.manufacturer if original else "User reviewed", model=name,
            source_url=evidence.source_url, case_color="#303735")
        case_color = colors[0].hex if colors else None
        if case_color is None:
            notes.append("Case color has not been sampled. The current workbench case color is retained.")
    else:
        if not colors:
            raise IntakeError("Sample a keycap crop or select explicit color codes, then select colors to apply.")
        product, _ = keycaps_from_evidence(evidence, colors)
        product = KeycapSet.model_validate({**product.model_dump(), "id": identifier, "name": name, "colors": colors})
        case_color = None
    evidence.warnings.extend(notes)
    evidence.warnings.append(f"Confirmed variant: {body.variant or 'unspecified'}; selected colors: {', '.join(c.hex for c in colors) or 'none'}")
    product = repository.save_product(product, evidence, reviewed_revision=True)
    return {"keyboard": product if isinstance(product, KeyboardDefinition) else None,
            "keycapSet": product if isinstance(product, KeycapSet) else None,
            "caseColor": case_color, "keyColorMap": key_color_map, "warnings": list(dict.fromkeys(notes))}
