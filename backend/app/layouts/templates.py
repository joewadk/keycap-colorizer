from enum import StrEnum
from typing import Annotated, NamedTuple

from pydantic import Field

from app.models.base import DomainModel
from app.models.keyboard import (
    KeyboardCase,
    KeyboardDefinition,
    KeyboardFeatures,
    KeyboardKey,
    LayoutType,
)


U_MM = 19.05


class LayoutTemplate(StrEnum):
    ANSI_65 = "ANSI_65"
    ANSI_75 = "ANSI_75"
    ANSI_TKL = "ANSI_TKL"


class LayoutOverrides(DomainModel):
    right_shift_width: Annotated[float, Field(gt=0, le=4)] | None = None
    knob: bool | None = None
    screen: bool | None = None
    badge: bool | None = None


class KeySpec(NamedTuple):
    id: str
    legend: str
    width: float = 1.0


class Gap(NamedTuple):
    width: float


def key(id: str, legend: str, width: float = 1.0) -> KeySpec:
    return KeySpec(id, legend, width)


def gap(width: float) -> Gap:
    return Gap(width)


NUMBER_ROW = [
    key("grave", "`"),
    *[key(f"digit-{value}", value) for value in "1234567890"],
    key("minus", "-"),
    key("equal", "="),
    key("backspace", "Backspace", 2),
]
Q_ROW = [
    key("tab", "Tab", 1.5),
    *[key(letter.lower(), letter) for letter in "QWERTYUIOP"],
    key("bracket-left", "["),
    key("bracket-right", "]"),
    key("backslash", "\\", 1.5),
]
HOME_ROW = [
    key("caps-lock", "Caps", 1.75),
    *[key(letter.lower(), letter) for letter in "ASDFGHJKL"],
    key("semicolon", ";"),
    key("quote", "'"),
    key("enter", "Enter", 2.25),
]
SHIFT_ROW = [
    key("left-shift", "Shift", 2.25),
    *[key(letter.lower(), letter) for letter in "ZXCVBNM"],
    key("comma", ","),
    key("period", "."),
    key("slash", "/"),
]
BOTTOM_TKL = [
    key("left-control", "Ctrl", 1.25),
    key("left-meta", "Win", 1.25),
    key("left-alt", "Alt", 1.25),
    key("space", "", 6.25),
    key("right-alt", "Alt", 1.25),
    key("right-meta", "Win", 1.25),
    key("menu", "Menu", 1.25),
    key("right-control", "Ctrl", 1.25),
]
BOTTOM_COMPACT = [
    key("left-control", "Ctrl", 1.25),
    key("left-meta", "Win", 1.25),
    key("left-alt", "Alt", 1.25),
    key("space", "", 6.25),
    key("right-alt", "Alt", 1.25),
    key("function", "Fn"),
    key("right-control", "Ctrl"),
]

FUNCTION_ROW_TKL = [
    key("esc", "Esc"), gap(1),
    *[key(f"f{i}", f"F{i}") for i in range(1, 5)], gap(0.5),
    *[key(f"f{i}", f"F{i}") for i in range(5, 9)], gap(0.5),
    *[key(f"f{i}", f"F{i}") for i in range(9, 13)], gap(0.25),
    key("print-screen", "PrtSc"), key("scroll-lock", "Scroll"), key("pause", "Pause"),
]
FUNCTION_ROW_75 = [
    key("esc", "Esc"), gap(0.5),
    *[key(f"f{i}", f"F{i}") for i in range(1, 5)], gap(0.25),
    *[key(f"f{i}", f"F{i}") for i in range(5, 9)], gap(0.25),
    *[key(f"f{i}", f"F{i}") for i in range(9, 13)],
    key("print-screen", "PrtSc"), key("insert", "Ins"), key("delete", "Del"),
]


def _groups_for(key_id: str) -> list[str]:
    groups = ["entire-keyboard"]
    if len(key_id) == 1 and key_id.isalpha():
        groups.append("alphas")
    if key_id in {"w", "a", "s", "d"}:
        groups.append("wasd")
    if key_id == "esc" or (key_id.startswith("f") and key_id[1:].isdigit()):
        groups.append("function-row")
    if key_id.startswith("arrow-"):
        groups.append("arrow-keys")
    if key_id in {
        "insert", "delete", "home", "end", "page-up", "page-down",
        "print-screen", "scroll-lock", "pause",
    }:
        groups.append("navigation-cluster")
    if key_id in {
        "tab", "caps-lock", "backspace", "enter", "left-shift", "right-shift",
        "left-control", "right-control", "left-meta", "right-meta", "left-alt",
        "right-alt", "menu", "function", "space",
    }:
        groups.append("modifiers")
    return groups


def _make_rows(template: LayoutTemplate, right_shift_width: float) -> list[list[KeySpec | Gap]]:
    arrows = [key("arrow-left", "←"), key("arrow-down", "↓"), key("arrow-right", "→")]
    if template is LayoutTemplate.ANSI_65:
        return [
            [*NUMBER_ROW, gap(0.25), key("home", "Home")],
            [*Q_ROW, gap(0.25), key("page-up", "PgUp")],
            [*HOME_ROW, gap(0.25), key("page-down", "PgDn")],
            [*SHIFT_ROW, key("right-shift", "Shift", right_shift_width), gap(0.25), key("arrow-up", "↑"), key("end", "End")],
            [*BOTTOM_COMPACT, gap(0.25), *arrows],
        ]
    if template is LayoutTemplate.ANSI_75:
        return [
            FUNCTION_ROW_75,
            [*NUMBER_ROW, gap(0.25), key("home", "Home")],
            [*Q_ROW, gap(0.25), key("page-up", "PgUp")],
            [*HOME_ROW, gap(0.25), key("page-down", "PgDn")],
            [*SHIFT_ROW, key("right-shift", "Shift", right_shift_width), gap(0.25), key("arrow-up", "↑"), key("end", "End")],
            [*BOTTOM_COMPACT, gap(0.25), *arrows],
        ]
    return [
        FUNCTION_ROW_TKL,
        [*NUMBER_ROW, gap(1.25), key("insert", "Ins"), key("home", "Home"), key("page-up", "PgUp")],
        [*Q_ROW, gap(1.25), key("delete", "Del"), key("end", "End"), key("page-down", "PgDn")],
        [*HOME_ROW],
        [*SHIFT_ROW, key("right-shift", "Shift", right_shift_width), gap(2.25), key("arrow-up", "↑")],
        [*BOTTOM_TKL, gap(1.25), *arrows],
    ]


def _layout_type(template: LayoutTemplate) -> LayoutType:
    return {
        LayoutTemplate.ANSI_65: LayoutType.SIXTY_FIVE,
        LayoutTemplate.ANSI_75: LayoutType.SEVENTY_FIVE,
        LayoutTemplate.ANSI_TKL: LayoutType.TKL,
    }[template]


def build_keyboard_from_template(
    template: LayoutTemplate,
    *,
    keyboard_id: str,
    manufacturer: str,
    model: str,
    source_url: str,
    case_color: str = "#24282A",
    overrides: LayoutOverrides | None = None,
) -> KeyboardDefinition:
    overrides = overrides or LayoutOverrides()
    default_shift = 1.75 if template is not LayoutTemplate.ANSI_TKL else 2.75
    rows = _make_rows(template, overrides.right_shift_width or default_shift)
    keys: list[KeyboardKey] = []

    for row_index, row in enumerate(rows):
        x = 0.0
        for item in row:
            if isinstance(item, Gap):
                x += item.width
                continue
            keys.append(
                KeyboardKey(
                    id=item.id,
                    legend=item.legend,
                    row=row_index,
                    x=x,
                    y=float(row_index),
                    width_u=item.width,
                    stabilizer=item.width >= 2,
                    group=_groups_for(item.id),
                )
            )
            x += item.width

    width_u = max(item.x + item.width_u for item in keys)
    return KeyboardDefinition(
        id=keyboard_id,
        manufacturer=manufacturer,
        model=model,
        layout_type=_layout_type(template),
        case=KeyboardCase(
            color=case_color,
            width_mm=(width_u + 0.5) * U_MM,
            depth_mm=(len(rows) + 0.5) * U_MM,
            corner_radius_mm=6,
        ),
        keys=keys,
        features=KeyboardFeatures(
            knob=overrides.knob or False,
            screen=overrides.screen or False,
            badge=overrides.badge or False,
        ),
        source_url=source_url,
    )
