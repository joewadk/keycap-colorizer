from collections import defaultdict
from io import BytesIO
from pathlib import Path
from statistics import median
from typing import Annotated
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, model_validator

from app.models.base import DomainModel
from app.models.keycap import KeycapColor

MAX_BYTES = 8_000_000
MAX_PIXELS = 16_000_000
MAX_DIMENSION = 8192
APPROXIMATE = "Image colors are approximate, not calibrated real-world colors. Lighting, backgrounds, and camera processing affect results."


class SamplingError(ValueError):
    pass


class Crop(DomainModel):
    """Fractional rectangle in the EXIF-oriented image, not original pixel coordinates."""
    left: Annotated[float, Field(ge=0, lt=1)] = 0
    top: Annotated[float, Field(ge=0, lt=1)] = 0
    right: Annotated[float, Field(gt=0, le=1)] = 1
    bottom: Annotated[float, Field(gt=0, le=1)] = 1

    @model_validator(mode="after")
    def nonempty(self):
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("Crop must have positive width and height")
        return self


class PaletteResult(DomainModel):
    colors: list[KeycapColor]
    warnings: list[str]


def _decode(path: Path, crop: Crop) -> Image.Image:
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise SamplingError("Image exceeds the 8 MB sampling limit.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=["PNG", "JPEG", "WEBP", "GIF"]) as source:
                if source.width * source.height > MAX_PIXELS or max(source.size) > MAX_DIMENSION:
                    raise SamplingError("Image dimensions exceed the safe decoding limit.")
                if getattr(source, "is_animated", False):
                    raise SamplingError("Choose a still product image, not an animation.")
                # Validate/decode before copying. EXIF orientation makes crop coordinates predictable.
                source.load()
                oriented = ImageOps.exif_transpose(source)
                w, h = oriented.size
                box = (round(crop.left * w), round(crop.top * h), round(crop.right * w), round(crop.bottom * h))
                if box[2] - box[0] < 3 or box[3] - box[1] < 3:
                    raise SamplingError("Choose an image crop at least 3 pixels wide and high.")
                image = oriented.crop(box).convert("RGBA")
                # Nearest avoids inventing blended colors at key/background boundaries.
                image.thumbnail((256, 256), Image.Resampling.NEAREST)
                return image
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise SamplingError("Cannot decode this image safely. Use a valid PNG, JPEG, WebP, or still GIF.") from None


def _distance(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3))


def sample_image(path: Path, *, crop: Crop | None = None, max_colors: int = 6) -> PaletteResult:
    if isinstance(max_colors, bool) or not isinstance(max_colors, int) or not 1 <= max_colors <= 12:
        raise SamplingError("max_colors must be an integer between 1 and 12.")
    image = _decode(path, crop or Crop())
    pixels = image.load()
    bins = defaultdict(list)
    for y in range(1, image.height - 1):
        for x in range(1, image.width - 1):
            center = pixels[x, y]
            neighbors = [pixels[x - 1, y], pixels[x + 1, y], pixels[x, y - 1], pixels[x, y + 1]]
            # Prefer locally flat surfaces. Narrow legends, specular dots, and edges are downweighted
            # spatially, not by brightness: genuine black and white keycaps remain eligible.
            if center[3] < 240 or any(n[3] < 240 or _distance(center, n) > 30 ** 2 for n in neighbors):
                continue
            rgb = center[:3]
            bins[tuple(v // 24 for v in rgb)].append(rgb)
    total = sum(map(len, bins.values()))
    if total < 9:
        raise SamplingError("Not enough opaque, flat pixels to sample. Try a larger, clearer crop of the keycaps.")
    clusters = []
    for _, values in sorted(bins.items(), key=lambda item: (-len(item[1]), item[0])):
        representative = tuple(int(median(v[i] for v in values)) for i in range(3))
        closest = min(clusters, key=lambda c: _distance(c[0], representative), default=None)
        if closest is not None and _distance(closest[0], representative) <= 36 ** 2:
            closest[1].extend(values)
        else:
            clusters.append([representative, list(values)])
    ranked = sorted(clusters, key=lambda c: (-len(c[1]), c[0]))
    colors = []
    for _, values in ranked:
        if len(values) / total < 0.02:
            continue
        rgb = tuple(int(median(v[i] for v in values)) for i in range(3))
        hex_value = "#" + "".join(f"{v:02X}" for v in rgb)
        spread = median(_distance(v, rgb) for v in values) ** 0.5
        # Heuristic confidence in this sample only; never a calibrated accuracy probability.
        confidence = round(max(0.2, min(0.75, 0.55 + 0.2 * len(values) / total - spread / 150)), 2)
        colors.append(KeycapColor(id=f"sample-{hex_value[1:].lower()}", name=f"Sample {len(colors) + 1}",
                                  hex=hex_value, source="image_sample", confidence=confidence))
        if len(colors) == max_colors:
            break
    if not colors:
        raise SamplingError("No dominant colors found. Crop more closely around the keycaps.")
    notes = [APPROXIMATE, "Confidence is a heuristic. Small accents below 2% of retained pixels may be omitted."]
    if crop is None:
        notes.append("Whole image sampled: backgrounds and case colors may be included. Use a crop around keycap surfaces; automatic keycap detection is not implemented.")
    else:
        notes.append("Only the supplied crop was sampled; it may still contain legends, shadows, or backgrounds.")
    return PaletteResult(colors=colors, warnings=notes)
