import pytest

from app.layouts import LayoutOverrides, LayoutTemplate, build_keyboard_from_template
from app.layouts.templates import U_MM


def build(template: LayoutTemplate, overrides: LayoutOverrides | None = None):
    return build_keyboard_from_template(
        template,
        keyboard_id=f"test-{template.value.lower()}",
        manufacturer="Fixture",
        model=template.value,
        source_url="https://example.com/keyboard",
        overrides=overrides,
    )


@pytest.mark.parametrize(
    ("template", "expected_count", "expected_rows"),
    [
        (LayoutTemplate.ANSI_65, 68, 5),
        (LayoutTemplate.ANSI_75, 84, 6),
        (LayoutTemplate.ANSI_TKL, 87, 6),
    ],
)
def test_templates_have_canonical_key_counts(template, expected_count, expected_rows) -> None:
    keyboard = build(template)
    assert len(keyboard.keys) == expected_count
    assert len({key.id for key in keyboard.keys}) == expected_count
    assert max(key.row for key in keyboard.keys) + 1 == expected_rows


def test_standard_key_spacing_uses_keyboard_units() -> None:
    keyboard = build(LayoutTemplate.ANSI_65)
    one = next(key for key in keyboard.keys if key.id == "digit-1")
    two = next(key for key in keyboard.keys if key.id == "digit-2")
    backspace = next(key for key in keyboard.keys if key.id == "backspace")
    assert two.x - one.x == 1
    assert backspace.width_u == 2
    assert keyboard.case.width_mm is not None
    assert keyboard.case.width_mm / U_MM > 16


def test_rows_have_unit_vertical_offsets() -> None:
    keyboard = build(LayoutTemplate.ANSI_75)
    esc = next(key for key in keyboard.keys if key.id == "esc")
    grave = next(key for key in keyboard.keys if key.id == "grave")
    assert grave.y - esc.y == 1


def test_spacebar_has_expected_dimensions_and_stabilizer() -> None:
    for template in LayoutTemplate:
        space = next(key for key in build(template).keys if key.id == "space")
        assert space.width_u == 6.25
        assert space.height_u == 1
        assert space.stabilizer is True


def test_logical_groups_are_assigned_deterministically() -> None:
    keys = {key.id: key for key in build(LayoutTemplate.ANSI_TKL).keys}
    assert {"alphas", "wasd"}.issubset(keys["w"].group)
    assert "function-row" in keys["f12"].group
    assert "arrow-keys" in keys["arrow-up"].group
    assert "navigation-cluster" in keys["insert"].group
    assert "modifiers" in keys["left-shift"].group
    assert all("entire-keyboard" in key.group for key in keys.values())


def test_layout_overrides_change_geometry_and_features() -> None:
    keyboard = build(
        LayoutTemplate.ANSI_75,
        LayoutOverrides(right_shift_width=2.0, knob=True, badge=True),
    )
    right_shift = next(key for key in keyboard.keys if key.id == "right-shift")
    assert right_shift.width_u == 2.0
    assert keyboard.features.knob is True
    assert keyboard.features.badge is True


def test_invalid_override_is_rejected() -> None:
    with pytest.raises(ValueError):
        LayoutOverrides(right_shift_width=0)


@pytest.mark.parametrize("template", [LayoutTemplate.ANSI_65, LayoutTemplate.ANSI_75])
def test_compact_bottom_rows_align_with_navigation(template) -> None:
    keyboard = build(template)
    by_id = {key.id: key for key in keyboard.keys}
    assert by_id["arrow-up"].x == by_id["arrow-down"].x
    assert by_id["arrow-right"].x == by_id["home"].x
    assert by_id["right-alt"].width_u == 1
    for row in {key.row for key in keyboard.keys if key.id != "esc"}:
        if template == LayoutTemplate.ANSI_75 and row == 0:
            continue
        assert max(key.x + key.width_u for key in keyboard.keys if key.row == row) == 16.25


@pytest.mark.parametrize("template,edge", [(LayoutTemplate.ANSI_75, 16.25), (LayoutTemplate.ANSI_TKL, 19.25)])
def test_function_row_aligns_with_right_edge(template, edge):
    keyboard = build(template)
    assert max(key.x + key.width_u for key in keyboard.keys if key.row == 0) == edge
    if template == LayoutTemplate.ANSI_TKL:
        by_id = {key.id: key for key in keyboard.keys}
        assert by_id["print-screen"].x == by_id["insert"].x
