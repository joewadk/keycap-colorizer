from PIL import Image, ImageDraw
import pytest

from app.colors.quick_fit import quick_fit, without_border_background
from app.colors.sampling import Crop, SamplingError
from app.layouts import LayoutTemplate, build_keyboard_from_template


def board(layout=LayoutTemplate.ANSI_75):
    return build_keyboard_from_template(layout, keyboard_id="test", manufacturer="Test", model="Test", source_url="https://example.com/test")


@pytest.mark.parametrize("layout", list(LayoutTemplate))
def test_scheme_fills_every_key_with_real_sampled_colors(tmp_path, layout):
    image = Image.new("RGB", (300, 100), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 210, 80), fill="#668855")
    draw.rectangle((220, 20, 260, 80), fill="#333333")
    draw.rectangle((270, 20, 280, 80), fill="#BB4422")
    path = tmp_path / "scheme.png"; image.save(path)
    keyboard = board(layout)
    palette, mapping = quick_fit(path, keyboard, Crop())
    assert set(mapping) == {key.id for key in keyboard.keys}
    assert set(mapping.values()).issubset({color.id for color in palette.colors})
    assert "#FFFFFF" not in {color.hex for color in palette.colors}
    assert mapping["a"] == "sample-668855"
    assert mapping["enter"] == "sample-bb4422"
    assert all(color.source == "image_sample" for color in palette.colors)
    assert quick_fit(path, keyboard, Crop())[1] == mapping


def test_background_removal_preserves_enclosed_white_keys():
    image = Image.new("RGBA", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 90, 90), fill="black")
    draw.rectangle((30, 30, 70, 70), fill="white")
    cleaned, removed = without_border_background(image)
    assert removed and cleaned.getpixel((0, 0))[3] == 0
    assert cleaned.getpixel((50, 50)) == (255, 255, 255, 255)


def test_position_fit_and_monochrome_fallback(tmp_path):
    keyboard = board()
    width = max(k.x + k.width_u for k in keyboard.keys)
    height = max(k.y + k.height_u for k in keyboard.keys)
    image = Image.new("RGB", (int(width * 50), int(height * 50)), "#111111")
    draw = ImageDraw.Draw(image)
    for key in keyboard.keys:
        fill = "#C5795E" if key.id == "esc" or "function-row" in key.group else "#D8DBD1"
        draw.rectangle((int(key.x*50+2), int(key.y*50+2), int((key.x+key.width_u)*50-2), int((key.y+key.height_u)*50-2)), fill=fill)
    path = tmp_path / "board.png"; image.save(path)
    palette, mapping = quick_fit(path, keyboard, Crop(), "positions")
    assert mapping["esc"] == "sample-c5795e"
    assert mapping["f1"] == "sample-c5795e"
    assert mapping["a"] == "sample-d8dbd1"
    assert any("straight-on" in note for note in palette.warnings)
    Image.new("RGB", (100, 100), "#123456").save(path)
    assert set(quick_fit(path, keyboard, Crop())[1].values()) == {"sample-123456"}
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(path)
    with pytest.raises(SamplingError):
        quick_fit(path, keyboard, Crop())
