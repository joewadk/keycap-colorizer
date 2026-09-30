"""Deterministic photo-inspired suggestions, never claims of exact key detection."""
from collections import Counter, deque
from pathlib import Path

from PIL import Image

from app.colors.sampling import Crop, SamplingError, _decode, _distance, sample_pixels
from app.models.keyboard import KeyboardDefinition


def without_border_background(image: Image.Image) -> tuple[Image.Image, bool]:
    """Remove only connected, nearly uniform outer background; keep enclosed white keys."""
    width, height = image.size
    pixels = image.load()
    border = {(x, y) for x in range(width) for y in (0, height - 1)}
    border.update((x, y) for x in (0, width - 1) for y in range(height))
    opaque = [pixels[x, y][:3] for x, y in border if pixels[x, y][3] >= 240]
    if not opaque:
        return image, False
    dominant = Counter(opaque).most_common(1)[0][0]
    if sum(_distance(rgb, dominant) <= 18 ** 2 for rgb in opaque) < .7 * len(opaque):
        return image, False
    pending = deque(border)
    removed = set()
    visited = set()
    while pending:
        x, y = pending.popleft()
        if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
            continue
        visited.add((x, y))
        if pixels[x, y][3] < 240 or _distance(pixels[x, y], dominant) > 18 ** 2:
            continue
        removed.add((x, y))
        pending.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    if not removed or len(removed) > .9 * width * height:
        return image, False
    output = image.copy()
    for point in removed:
        output.putpixel(point, (0, 0, 0, 0))
    return output, True


def quick_fit(path: Path, keyboard: KeyboardDefinition, crop: Crop, strategy: str = "scheme"):
    image = _decode(path, crop)
    cleaned, removed = without_border_background(image)
    try:
        palette = sample_pixels(cleaned)
    except SamplingError:
        palette = sample_pixels(image)
        removed = False
    primary = palette.colors[0]
    secondary = palette.colors[min(1, len(palette.colors) - 1)]
    accent = palette.colors[min(2, len(palette.colors) - 1)]
    assignments = {}
    for key in keyboard.keys:
        color = primary
        if "modifiers" in key.group or "navigation-cluster" in key.group or "function-row" in key.group:
            color = secondary
        if key.id in {"esc", "enter"} or "arrow-keys" in key.group:
            color = accent
        assignments[key.id] = color.id
    if strategy == "positions":
        width_u = max(key.x + key.width_u for key in keyboard.keys)
        height_u = max(key.y + key.height_u for key in keyboard.keys)
        rgb = {c.id: tuple(bytes.fromhex(c.hex[1:])) for c in palette.colors}
        missed = 0
        for key in keyboard.keys:
            # Sample central surfaces rather than edges/legends. Fit the entire key rectangle,
            # not the case, to the selected crop. This assumes a top-down matching layout.
            box = (round((key.x + key.width_u * .25) / width_u * image.width),
                   round((key.y + key.height_u * .25) / height_u * image.height),
                   round((key.x + key.width_u * .75) / width_u * image.width),
                   round((key.y + key.height_u * .75) / height_u * image.height))
            try:
                local = sample_pixels(image.crop(box), max_colors=1).colors[0]
                assignments[key.id] = min(rgb, key=lambda color: _distance(rgb[color], bytes.fromhex(local.hex[1:])))
            except SamplingError:
                missed += 1
        palette.warnings.append("Position fit assumes a straight-on photo of the same layout, cropped to the outer key edges. Perspective and different layouts can misassign colors.")
        if missed:
            palette.warnings.append(f"{missed} small or unclear key regions use the suggested group colors; correct them manually.")
    else:
        palette.warnings.append("Suggested color scheme: dominant color for letters, next color for modifiers/functions, third color for accents. This does not reconstruct the photographed key positions.")
    palette.warnings.append("Uniform border background was excluded." if removed else "Background could not be confidently excluded; crop around the keycaps if needed.")
    palette.warnings.append("Review before applying. Case colors, shadows, and unrelated objects may still be included.")
    return palette, assignments
