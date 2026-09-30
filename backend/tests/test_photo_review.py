from io import BytesIO
from unittest.mock import AsyncMock
import sqlite3

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.api.storage import get_repository
from app.config import Settings, get_settings
from app.ingestion.urls import IntakeError
from app.main import create_app
from app.storage.repository import Repository
from app.workflows.service import FIXTURE_KEYBOARD_URL, FIXTURE_KEYCAP_URL


@pytest.fixture
def client(tmp_path):
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: Repository(tmp_path / "products.db")
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, data_dir=str(tmp_path), database_path=str(tmp_path / "products.db"))
    with TestClient(app) as client:
        yield client


def prepare(client, kind):
    response = client.post("/api/ingestion/reviews", json={"kind": kind, "url": FIXTURE_KEYBOARD_URL if kind == "keyboard" else FIXTURE_KEYCAP_URL})
    assert response.status_code == 200, response.text
    return response.json()


def sample(client, review, crop):
    response = client.post(f"/api/ingestion/reviews/{review['id']}/sample", json={"imageIndex": 0, "crop": crop})
    assert response.status_code == 200, response.text
    return response.json()


def confirm(client, review, proposal, *, color_ids=None):
    response = client.post(f"/api/ingestion/reviews/{review['id']}/confirm", json={
        "name": review["title"], "layout": review["layout"], "variant": "Test photo",
        "sampleId": proposal["id"], "colorIds": color_ids or [c["id"] for c in proposal["colors"]],
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_real_photo_crops_case_and_keys_save_restore_and_revisions(client):
    board = prepare(client, "keyboard")
    photo = client.get(f"/api/ingestion/reviews/{board['id']}/images/0")
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/png"
    housing = sample(client, board, {"left": .1, "top": .12, "right": .9, "bottom": .25})
    assert [c["hex"] for c in housing["colors"]] == ["#245577"]
    applied_board = confirm(client, board, housing)
    assert applied_board["caseColor"] == "#245577"
    assert applied_board["keyboard"]["case"]["color"] == "#303735"

    caps = prepare(client, "keycaps")
    palette = sample(client, caps, {"left": .2, "top": .35, "right": .8, "bottom": .65})
    assert {c["hex"] for c in palette["colors"]} == {"#D8DBD1", "#C5795E"}
    applied_caps = confirm(client, caps, palette)
    kit = applied_caps["keycapSet"]
    assert all(c["source"] == "image_sample" for c in kit["colors"])
    saved = client.post("/api/configurations", json={"keyboardId": applied_board["keyboard"]["id"], "keycapSetId": kit["id"],
        "caseColor": applied_board["caseColor"], "keyColorMap": {"esc": kit["colors"][0]["id"]}})
    assert saved.status_code == 201, saved.text
    snapshot = saved.json()
    revised = confirm(client, caps, palette, color_ids=[kit["colors"][0]["id"]])
    assert revised["keycapSet"]["id"] != kit["id"]
    # Manual reimport by Save design remains idempotent after another review of the URL.
    assert client.post("/api/products/manual", json={"kind": "keycaps", "product": kit}).status_code == 201
    restored = client.get(f"/api/configurations/{snapshot['configuration']['id']}").json()
    assert restored == snapshot


def test_failed_keycaps_do_not_prevent_keyboard_confirmation(client, monkeypatch):
    board = prepare(client, "keyboard")
    monkeypatch.setattr("app.ingestion.service.ScrapingService.scrape", AsyncMock(side_effect=IntakeError("Store blocked the request.")))
    failed = client.post("/api/ingestion/reviews", json={"kind": "keycaps", "url": "https://shop.example/caps"})
    assert failed.status_code == 422 and "upload" in failed.json()["detail"]
    confirmed = client.post(f"/api/ingestion/reviews/{board['id']}/confirm", json={"name": "Working board", "layout": "ANSI_75"})
    assert confirmed.status_code == 200 and len(confirmed.json()["keyboard"]["keys"]) == 84


def test_uploaded_photo_manual_fallback_and_invalid_inputs(client):
    review = client.post("/api/ingestion/reviews", json={"kind": "keyboard", "manual": True}).json()
    base = f"/api/ingestion/reviews/{review['id']}"
    assert client.post(base + "/upload", content=b"not an image").status_code == 422
    image = Image.new("RGB", (100, 100), "#B04080")
    output = BytesIO(); image.save(output, format="PNG")
    uploaded = client.post(base + "/upload", content=output.getvalue())
    assert uploaded.status_code == 200
    review = uploaded.json()["review"]
    proposal = sample(client, review, {"left": .1, "top": .1, "right": .9, "bottom": .9})
    assert proposal["colors"][0]["hex"] == "#B04080"
    review["layout"] = "ANSI_65"
    assert confirm(client, review, proposal)["caseColor"] == "#B04080"
    assert client.post(base + "/sample", json={"imageIndex": 99, "crop": {}}).status_code == 404
    assert client.post(base + "/sample", json={"imageIndex": 0, "crop": {"left": .9, "right": .1}}).status_code == 422
    invalid = client.post(base + "/confirm", json={"name": "X", "layout": "ANSI_65", "sampleId": proposal["id"], "colorIds": ["invented"]})
    assert invalid.status_code == 422
    assert client.get("/api/ingestion/reviews/missing/images/0").status_code == 404


def test_v1_migration_preserves_configuration_foreign_keys(tmp_path):
    from app.layouts import LayoutTemplate, build_keyboard_from_template
    from app.models.keycap import KeycapSet
    from app.storage.models import ConfigurationCreate
    path = tmp_path / "v1.db"
    board = build_keyboard_from_template(LayoutTemplate.ANSI_75, keyboard_id="board", manufacturer="Test", model="Board", source_url="https://shop.example/board")
    kit = KeycapSet(id="caps", manufacturer="Test", name="Caps", source_url="https://shop.example/caps",
        colors=[dict(id="red", name="Red", hex="#FF0000", source="manufacturer")])
    # Build an actual v1 schema (including URL uniqueness), then migrate with saved references.
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE products(id TEXT PRIMARY KEY, kind TEXT NOT NULL, url TEXT NOT NULL, data TEXT NOT NULL, evidence TEXT, UNIQUE(kind,url));
            CREATE TABLE configurations(id TEXT PRIMARY KEY, keyboard_id TEXT NOT NULL REFERENCES products(id), keycap_set_id TEXT NOT NULL REFERENCES products(id), data TEXT NOT NULL, compatibility TEXT NOT NULL);
            PRAGMA user_version=1;
        """)
        for kind, product in [("keyboard", board), ("keycaps", kit)]:
            db.execute("INSERT INTO products VALUES(?,?,?,?,NULL)", (product.id, kind, str(product.source_url), product.model_dump_json()))
        from app.models.configuration import Configuration
        from app.services.compatibility import check_compatibility
        config = Configuration(id="saved", keyboard_id="board", keycap_set_id="caps", key_color_map={"esc": "red"}, case_color="#ABCDEF")
        db.execute("INSERT INTO configurations VALUES(?,?,?,?,?)", (config.id, "board", "caps", config.model_dump_json(), check_compatibility(board, kit).model_dump_json()))
    repo = Repository(path)
    assert repo.get_configuration("saved").configuration.case_color == "#ABCDEF"
    revised = kit.model_copy(update={"id": "caps-revised", "name": "New revision"})
    repo.save_product(revised, reviewed_revision=True)
    assert repo.get_configuration("saved").keycap_set.name == "Caps"
    assert repo.find_product(str(kit.source_url), "keycaps").id == revised.id
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_per_key_photo_samples_are_validated_and_saved(client):
    board = prepare(client, "keyboard")
    keyboard = client.post(f"/api/ingestion/reviews/{board['id']}/confirm", json={"name": "Board", "layout": "ANSI_75"}).json()["keyboard"]
    caps = prepare(client, "keycaps")
    bone = sample(client, caps, {"left": .2, "top": .35, "right": .4, "bottom": .65})
    clay = sample(client, caps, {"left": .6, "top": .35, "right": .8, "bottom": .65})
    choices = {"esc": {"sampleId": clay["id"], "colorId": clay["colors"][0]["id"]},
               "f1": {"sampleId": bone["id"], "colorId": bone["colors"][0]["id"]}}
    base = f"/api/ingestion/reviews/{caps['id']}/confirm"
    body = {"name": "Per-key caps", "layout": "ANSI_75", "keySamples": choices}
    response = client.post(base, json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["keyColorMap"] == {"esc": clay["colors"][0]["id"], "f1": bone["colors"][0]["id"]}
    assert len(result["keycapSet"]["colors"]) == 2
    saved = client.post("/api/configurations", json={"keyboardId": keyboard["id"], "keycapSetId": result["keycapSet"]["id"], "keyColorMap": result["keyColorMap"]}).json()
    restored = client.get(f"/api/configurations/{saved['configuration']['id']}").json()
    assert restored["configuration"]["keyColorMap"] == result["keyColorMap"]
    assert client.post(base, json={**body, "layout": "ANSI_65"}).status_code == 422
    assert client.post(base, json={**body, "keySamples": {"f1": {"sampleId": "expired", "colorId": "fake"}}}).status_code == 422
    assert client.post(base, json={**body, "keySamples": {"f1": {"sampleId": bone["id"], "colorId": "fake"}}}).status_code == 422
    assert client.post(base, json={**body, "layout": None}).status_code == 422


def test_offline_demo_does_not_require_firecrawl_credentials(client):
    response = client.post("/api/ingestion/reviews", json={"kind": "keycaps", "url": FIXTURE_KEYCAP_URL, "provider": "firecrawl"})
    assert response.status_code == 200


def test_quick_fit_can_be_corrected_and_confirmed(client):
    caps = prepare(client, "keycaps")
    base = f"/api/ingestion/reviews/{caps['id']}"
    response = client.post(base + "/quick-fit", json={"imageIndex": 0, "crop": {}, "layout": "ANSI_75"})
    assert response.status_code == 200, response.text
    fit = response.json()
    assert len(fit["keyColorMap"]) == 84
    choices = {key: {"sampleId": fit["id"], "colorId": color} for key, color in fit["keyColorMap"].items()}
    manual = sample(client, caps, {"left": .6, "top": .35, "right": .8, "bottom": .65})
    choices["f1"] = {"sampleId": manual["id"], "colorId": manual["colors"][0]["id"]}
    applied = client.post(base + "/confirm", json={"name": "Quick fitted", "layout": "ANSI_75", "keySamples": choices})
    assert applied.status_code == 200, applied.text
    assert len(applied.json()["keyColorMap"]) == 84
    assert applied.json()["keyColorMap"]["f1"] == "sample-c5795e"
    assert client.post(base + "/quick-fit", json={"imageIndex": 0, "crop": {}, "layout": "ANSI_100"}).status_code == 422
    assert client.post(base + "/quick-fit", json={"imageIndex": 90, "crop": {}, "layout": "ANSI_75"}).status_code == 404
    keyboard = prepare(client, "keyboard")
    assert client.post(f"/api/ingestion/reviews/{keyboard['id']}/quick-fit", json={"imageIndex": 0, "crop": {}, "layout": "ANSI_75"}).status_code == 422


def test_upload_still_available_with_more_than_forty_photos(client):
    from app.ingestion.models import ProductImage
    caps = prepare(client, "keycaps")
    item = client.app.state.photo_reviews[caps["id"]]
    item["evidence"].images.extend(ProductImage(url=f"https://example.com/{i}.png") for i in range(65))
    output = BytesIO(); Image.new("RGB", (20, 20), "red").save(output, format="PNG")
    uploaded = client.post(f"/api/ingestion/reviews/{caps['id']}/upload", content=output.getvalue())
    assert uploaded.status_code == 200
    assert len(uploaded.json()["review"]["images"]) == 67
    assert uploaded.json()["imageIndex"] == 66
