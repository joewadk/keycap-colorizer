from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    ColorSource,
    Configuration,
    KeyboardCase,
    KeyboardDefinition,
    KeyboardKey,
    KeycapColor,
    KeycapProfile,
    KeycapSet,
    LayoutType,
    SupportedKey,
)


def keyboard_data() -> dict:
    return {
        "id": "board-1",
        "manufacturer": "Acme",
        "model": "Compact 65",
        "layout_type": "65",
        "case": {"color": "black", "width_mm": 320},
        "keys": [
            {"id": "esc", "legend": "Esc", "row": 0, "x": 0, "y": 0},
            {
                "id": "space",
                "legend": "",
                "row": 4,
                "x": 3,
                "y": 4,
                "width_u": 6.25,
                "stabilizer": True,
                "group": ["modifiers"],
            },
        ],
        "source_url": "https://example.com/keyboard",
    }


def color_data() -> dict:
    return {
        "id": "forest",
        "name": "Forest Green",
        "hex": "2f5d3a",
        "source": "manufacturer",
    }


def test_keyboard_definition_accepts_normalized_geometry() -> None:
    keyboard = KeyboardDefinition.model_validate(keyboard_data())

    assert keyboard.layout_type is LayoutType.SIXTY_FIVE
    assert keyboard.keys[1].width_u == 6.25
    assert keyboard.keys[1].stabilizer is True
    assert keyboard.features.knob is False


def test_domain_models_accept_and_serialize_frontend_camel_case() -> None:
    data = keyboard_data()
    data["layoutType"] = data.pop("layout_type")
    data["sourceUrl"] = data.pop("source_url")
    data["keys"][1]["widthU"] = data["keys"][1].pop("width_u")
    keyboard = KeyboardDefinition.model_validate(data)

    serialized = keyboard.model_dump(mode="json")
    assert serialized["layoutType"] == "65"
    assert serialized["keys"][1]["widthU"] == 6.25
    assert serialized["sourceUrl"] == "https://example.com/keyboard"


@pytest.mark.parametrize("field,value", [("width_u", 0), ("height_u", -1)])
def test_keyboard_key_rejects_non_positive_dimensions(field: str, value: float) -> None:
    data = {"id": "a", "legend": "A", "row": 2, "x": 0, "y": 0, field: value}
    with pytest.raises(ValidationError):
        KeyboardKey.model_validate(data)


def test_keyboard_rejects_duplicate_key_ids() -> None:
    data = keyboard_data()
    data["keys"][1]["id"] = "esc"
    with pytest.raises(ValidationError, match="key IDs must be unique"):
        KeyboardDefinition.model_validate(data)


def test_keyboard_rejects_unknown_fields_and_invalid_urls() -> None:
    data = keyboard_data()
    data["source_url"] = "not-a-url"
    data["unexpected"] = True
    with pytest.raises(ValidationError) as error:
        KeyboardDefinition.model_validate(data)
    assert {item["type"] for item in error.value.errors()} == {"url_parsing", "extra_forbidden"}


def test_keycap_color_normalizes_hex() -> None:
    color = KeycapColor.model_validate(color_data())
    assert color.hex == "#2F5D3A"
    assert color.source is ColorSource.MANUFACTURER


@pytest.mark.parametrize("hex_value", ["#FFF", "#GG0000", "1234567", "blue"])
def test_keycap_color_rejects_invalid_hex(hex_value: str) -> None:
    data = color_data()
    data["hex"] = hex_value
    with pytest.raises(ValidationError, match="six-digit RGB"):
        KeycapColor.model_validate(data)


def test_color_confidence_is_bounded() -> None:
    data = color_data()
    data.update(source="image_sample", confidence=1.1)
    with pytest.raises(ValidationError):
        KeycapColor.model_validate(data)


def test_keycap_set_validates_supported_keys() -> None:
    keycap_set = KeycapSet(
        id="caps-1",
        manufacturer="Acme",
        name="Forest",
        profile=KeycapProfile.CHERRY,
        colors=[color_data()],
        supported_keys=[SupportedKey(legend="Space", width_u=6.25, quantity=1)],
        source_url="https://example.com/keycaps",
    )
    assert keycap_set.supported_keys[0].width_u == 6.25


def test_keycap_set_requires_colors_and_unique_color_ids() -> None:
    base = {
        "id": "caps-1",
        "manufacturer": "Acme",
        "name": "Forest",
        "source_url": "https://example.com/keycaps",
    }
    with pytest.raises(ValidationError):
        KeycapSet.model_validate({**base, "colors": []})
    with pytest.raises(ValidationError, match="color IDs must be unique"):
        KeycapSet.model_validate({**base, "colors": [color_data(), color_data()]})


def test_configuration_defaults_to_timezone_aware_timestamp() -> None:
    configuration = Configuration(
        id="config-1",
        keyboard_id="board-1",
        keycap_set_id="caps-1",
        key_color_map={"esc": "forest"},
    )
    assert configuration.date_created.utcoffset() is not None
    assert configuration.key_color_map == {"esc": "forest"}


def test_configuration_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        Configuration(
            id="config-1",
            keyboard_id="board-1",
            keycap_set_id="caps-1",
            date_created=datetime(2026, 1, 1),
        )


def test_case_dimensions_must_be_physical() -> None:
    with pytest.raises(ValidationError):
        KeyboardCase(color="black", height_mm=0)
