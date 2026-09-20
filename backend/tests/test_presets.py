import json
from pathlib import Path

import pytest

from app.layouts import LayoutTemplate, build_keyboard_from_template
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet
from app.storage.models import ConfigurationCreate
from app.storage.repository import Repository


BOARDS = json.loads((Path(__file__).resolve().parents[2] / "frontend/src/data/boardPresets.json").read_text())


@pytest.mark.parametrize("data,template", zip(BOARDS, [LayoutTemplate.ANSI_75, LayoutTemplate.ANSI_TKL]))
def test_offline_board_snapshots_match_backend_templates(data, template):
    board = KeyboardDefinition.model_validate(data)
    generated = build_keyboard_from_template(template, keyboard_id=board.id, manufacturer=board.manufacturer,
        model=board.model, source_url=str(board.source_url))
    assert board == generated
    for index, key in enumerate(board.keys):
        for other in board.keys[index + 1:]:
            assert (key.x + key.width_u <= other.x or other.x + other.width_u <= key.x
                    or key.y + key.height_u <= other.y or other.y + other.height_u <= key.y)


@pytest.mark.parametrize("data", BOARDS)
def test_preset_palette_and_each_board_survive_storage_roundtrip(tmp_path, data):
    repo = Repository(tmp_path / "presets.db")
    board = KeyboardDefinition.model_validate(data)
    kit = KeycapSet(id="common-v1", manufacturer="Local Preset", name="Common colors", profile="Unknown",
        colors=[dict(id="red", name="Red", hex="#C94040", source="preset")],
        source_url="https://example.com/presets/common/v1")
    repo.save_product(board)
    repo.save_product(kit)
    saved = repo.save_configuration(ConfigurationCreate(keyboard_id=board.id, keycap_set_id=kit.id,
        key_color_map={"esc": "red", "arrow-up": "red"}))
    restored = Repository(repo.path).get_configuration(saved.configuration.id)
    assert restored == saved
    assert restored.keycap_set.colors[0].source == "preset"
    assert restored.compatibility.status == "unknown"
