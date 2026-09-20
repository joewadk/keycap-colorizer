from pathlib import Path

from app.colors.sampling import Crop, PaletteResult, SamplingError, sample_image
from app.models.keycap import ColorSource, KeycapColor


def select_palette(*, manufacturer: list[KeycapColor] | None = None, image: Path | None = None,
                   crop: Crop | None = None, estimates: list[KeycapColor] | None = None) -> PaletteResult:
    """Select supplied evidence by provenance. Never infer manufacturer codes from color names."""
    for colors, source in ((manufacturer, ColorSource.MANUFACTURER), (estimates, ColorSource.MODEL_ESTIMATE)):
        if colors and (any(c.source != source for c in colors) or len({c.id for c in colors}) != len(colors)):
            raise SamplingError("Supplied palette has incorrect provenance or duplicate color IDs.")
    if manufacturer:
        return PaletteResult(colors=manufacturer, warnings=["Manufacturer-provided codes; screen appearance may differ from physical keycaps."])
    notes = []
    if image is not None:
        try:
            return sample_image(image, crop=crop)
        except SamplingError as error:
            notes.append(str(error))
    if estimates:
        return PaletteResult(colors=estimates, warnings=notes + ["Model-estimated colors are an uncalibrated fallback, not manufacturer specifications."])
    raise SamplingError("No usable color evidence. " + " ".join(notes))
