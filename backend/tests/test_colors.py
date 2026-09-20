import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw
import pytest
from pydantic import ValidationError

from app.colors.sampling import Crop, SamplingError, sample_image
from app.colors.selection import select_palette
from app.models.keycap import KeycapColor


@pytest.fixture
def scene(tmp_path):
    # Synthetic image fixture: exact known colors, no vendor images or network.
    spec = json.loads((Path(__file__).parent / "fixtures/palette_scene.json").read_text())
    image = Image.new("RGB", tuple(spec["size"]), spec["background"])
    draw = ImageDraw.Draw(image)
    for rect in spec["rectangles"]:
        draw.rectangle(rect["box"], fill=rect["color"])
    path = tmp_path / "fixture.png"
    image.save(path)
    return path, spec


def test_crop_removes_background_and_narrow_legends_preserving_dark_light_colors(scene):
    path, spec = scene
    result = sample_image(path, crop=Crop(**spec["crop"]))
    assert sorted(c.hex for c in result.colors) == sorted(spec["expected"])
    assert all(c.source == "image_sample" and 0 < c.confidence <= 0.75 for c in result.colors)
    assert "approximate" in result.warnings[0]
    assert result == sample_image(path, crop=Crop(**spec["crop"]))


def test_whole_image_warns_about_background(scene):
    result = sample_image(scene[0])
    assert "#D000D0" in {c.hex for c in result.colors}
    assert any("backgrounds" in w and "Whole image" in w for w in result.warnings)


@pytest.mark.parametrize("color", ["#000000", "#FFFFFF", "#2F5141"])
def test_solid_black_white_and_green_are_retained(tmp_path, color):
    path = tmp_path / "solid.png"
    Image.new("RGB", (32, 32), color).save(path)
    assert [c.hex for c in sample_image(path).colors] == [color]


def test_transparent_background_is_not_a_color(tmp_path):
    path = tmp_path / "alpha.png"
    image = Image.new("RGBA", (40, 40), (255, 0, 255, 0))
    ImageDraw.Draw(image).rectangle((8, 8, 31, 31), fill=(47, 81, 65, 255))
    image.save(path)
    assert [c.hex for c in sample_image(path).colors] == ["#2F5141"]


def test_empty_transparency_fails(tmp_path):
    path = tmp_path / "alpha.png"
    Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(path)
    with pytest.raises(SamplingError, match="Not enough opaque"):
        sample_image(path)


def test_nearby_colors_merge_to_median(tmp_path):
    path = tmp_path / "gradient.png"
    image = Image.new("RGB", (60, 60), (100, 120, 100))
    ImageDraw.Draw(image).rectangle((30, 0, 59, 59), fill=(108, 128, 108))
    image.save(path)
    assert [c.hex for c in sample_image(path).colors] == ["#687C68"]


@pytest.mark.parametrize("value", [0, 13, True, 1.5])
def test_color_count_bounds(scene, value):
    with pytest.raises(SamplingError, match="integer"):
        sample_image(scene[0], max_colors=value)


def test_max_colors_is_respected(scene):
    assert len(sample_image(scene[0], max_colors=1).colors) == 1


@pytest.mark.parametrize("crop", [{"left": 0.7, "right": 0.2}, {"bottom": 0}, {"left": -1}, {"right": 2}])
def test_invalid_crop(crop):
    with pytest.raises(ValidationError):
        Crop(**crop)


def test_tiny_crop(scene):
    with pytest.raises(SamplingError, match="at least 3"):
        sample_image(scene[0], crop=Crop(right=0.001))


def test_corrupt_and_missing_images(tmp_path):
    path = tmp_path / "bad.png"
    for content in (None, b"not an image", b"\x89PNG\r\n\x1a\n"):
        if content is not None:
            path.write_bytes(content)
        with pytest.raises(SamplingError, match="decode"):
            sample_image(path)


def test_byte_limit_before_decoding(scene, monkeypatch):
    monkeypatch.setattr("app.colors.sampling.MAX_BYTES", 1)
    with pytest.raises(SamplingError, match="8 MB"):
        sample_image(scene[0])


def test_pixel_limit_before_loading(scene, monkeypatch):
    monkeypatch.setattr("app.colors.sampling.MAX_PIXELS", 100)
    with pytest.raises(SamplingError, match="dimensions"):
        sample_image(scene[0])


def test_animation_rejected(tmp_path):
    path = tmp_path / "animated.gif"
    Image.new("RGB", (20, 20), "red").save(path, save_all=True,
        append_images=[Image.new("RGB", (20, 20), "blue")])
    with pytest.raises(SamplingError, match="animation"):
        sample_image(path)


def color(source):
    return KeycapColor(id="forest", name="Forest", hex="#2F5141", source=source)


def test_manufacturer_precedes_image_and_estimate(scene):
    manufacturer = [color("manufacturer")]
    assert select_palette(manufacturer=manufacturer, image=Path("missing"), estimates=[color("model_estimate")]).colors == manufacturer
    assert select_palette(image=scene[0], estimates=[color("model_estimate")]).colors[0].source == "image_sample"


def test_failed_image_uses_explicit_estimates_with_warning():
    result = select_palette(image=Path("missing"), estimates=[color("model_estimate")])
    assert result.colors[0].source == "model_estimate"
    assert any("decode" in w for w in result.warnings)
    assert any("fallback" in w for w in result.warnings)


def test_no_evidence_fails_and_wrong_provenance_rejected():
    with pytest.raises(SamplingError, match="No usable"):
        select_palette()
    with pytest.raises(SamplingError, match="provenance"):
        select_palette(manufacturer=[color("model_estimate")])


def test_cli_outputs_valid_palette_and_clean_failure(scene):
    result = subprocess.run([sys.executable, "-m", "app.colors", str(scene[0]), "--max-colors", "2"], capture_output=True, text=True)
    assert result.returncode == 0
    assert len(json.loads(result.stdout)["colors"]) == 2
    failed = subprocess.run([sys.executable, "-m", "app.colors", "missing.png"], capture_output=True, text=True)
    assert failed.returncode == 1 and "Palette sampling failed" in failed.stderr
    assert "Traceback" not in failed.stderr
