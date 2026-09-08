import pytest
from fastapi.testclient import TestClient

from app.layouts import LayoutTemplate, build_keyboard_from_template
from app.main import app
from app.models.keyboard import KeyboardKey
from app.models.keycap import KeycapSet, SupportedKey
from app.services.compatibility import check_compatibility


def board(template=LayoutTemplate.ANSI_65):
    return build_keyboard_from_template(template, keyboard_id="board", manufacturer="Test", model="Test", source_url="https://example.com/board")


def kit(caps):
    return KeycapSet(id="kit", manufacturer="Test", name="Test", source_url="https://example.com/caps",
                     colors=[dict(id="white", name="White", hex="#FFFFFF", source="manufacturer")], supported_keys=caps)


def inventory(keyboard):
    return [SupportedKey(legend=key.legend or "Space", width_u=key.width_u, quantity=1) for key in keyboard.keys]


@pytest.mark.parametrize("template", list(LayoutTemplate))
def test_complete_inventory_fits_every_template(template):
    keyboard = board(template)
    result = check_compatibility(keyboard, kit(inventory(keyboard)))
    assert result.compatible and not result.missing and not result.uncertain


@pytest.mark.parametrize("key_id", ["space", "left-shift", "right-shift", "enter", "backspace", "left-control", "home"])
def test_missing_critical_key_is_reported(key_id):
    keyboard = board()
    caps = inventory(keyboard)
    index = next(i for i, key in enumerate(keyboard.keys) if key.id == key_id)
    caps.pop(index)
    result = check_compatibility(keyboard, kit(caps))
    assert not result.compatible
    assert result.status == "incompatible"
    assert result.missing
    assert any(issue.required_width_u == keyboard.keys[index].width_u for issue in result.missing)


def test_wrong_right_shift_width_is_missing():
    keyboard = board()
    caps = inventory(keyboard)
    caps[next(i for i, key in enumerate(keyboard.keys) if key.id == "right-shift")].width_u = 2.75
    result = check_compatibility(keyboard, kit(caps))
    assert [issue.key for issue in result.missing] == ["right-shift"]


def test_unknown_inventory_and_quantities_never_claim_fit():
    keyboard = board()
    assert check_compatibility(keyboard, kit([])).status == "unknown"
    caps = inventory(keyboard)
    for cap in caps:
        cap.quantity = None
    result = check_compatibility(keyboard, kit(caps))
    assert result.status == "unknown" and result.uncertain and not result.compatible


def test_shared_blank_inventory_cannot_be_reused():
    keyboard = board()
    keyboard.keys = [KeyboardKey(id=id, legend=id, row=0, x=i, y=0) for i, id in enumerate(["a", "b"])]
    result = check_compatibility(keyboard, kit([SupportedKey(width_u=1, quantity=1)]))
    assert len(result.missing) == 1


def test_matching_reserves_specific_caps_and_does_not_mutate():
    keyboard = board()
    keyboard.keys = [KeyboardKey(id=id, legend=id, row=0, x=i, y=0) for i, id in enumerate(["a", "b"])]
    caps = kit([SupportedKey(width_u=1, quantity=1), SupportedKey(width_u=1, legend="A", quantity=1)])
    before = caps.model_dump()
    assert check_compatibility(keyboard, caps).compatible
    assert caps.model_dump() == before


def test_vertical_numpad_key_needs_height_evidence():
    keyboard = board()
    keyboard.keys = [KeyboardKey(id="numpad-enter", legend="Enter", row=0, x=0, y=0, height_u=2, group=["numpad"])]
    result = check_compatibility(keyboard, kit([SupportedKey(width_u=1, legend="Enter", quantity=1)]))
    assert result.status == "unknown" and result.uncertain[0].key == "numpad-enter"


def test_api_camel_case_contract_and_invalid_input():
    keyboard = board()
    with TestClient(app) as client:
        response = client.post("/api/compatibility/check", json={"keyboard": keyboard.model_dump(mode="json"), "keycapSet": kit([]).model_dump(mode="json")})
        assert response.status_code == 200
        assert response.json()["status"] == "unknown"
        assert response.json()["compatible"] is False
        incomplete = inventory(keyboard)
        incomplete[next(i for i, key in enumerate(keyboard.keys) if key.id == "right-shift")].width_u = 2.75
        response = client.post("/api/compatibility/check", json={"keyboard": keyboard.model_dump(mode="json"), "keycapSet": kit(incomplete).model_dump(mode="json")})
        assert response.json()["missing"][0]["requiredWidthU"] == 1.75
        assert response.json()["status"] == "incompatible"
        assert client.post("/api/compatibility/check", json={}).status_code == 422
