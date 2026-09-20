import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.ingestion.models import PageEvidence
from app.layouts import LayoutTemplate, build_keyboard_from_template
from app.models.keycap import KeycapSet
from app.storage.models import ConfigurationCreate
from app.storage.repository import Repository, Conflict, NotFound, InvalidConfiguration, StorageError


@pytest.fixture
def products():
    keyboard = build_keyboard_from_template(LayoutTemplate.ANSI_75, keyboard_id="board", manufacturer="Test",
        model="75", source_url="https://example.com/board")
    keycaps = KeycapSet(id="kit", manufacturer="Test", name="Forest", source_url="https://example.com/kit",
        colors=[dict(id="forest", name="Forest", hex="#2F5141", source="manufacturer")])
    return keyboard, keycaps


@pytest.fixture
def repository(tmp_path, products):
    repo = Repository(tmp_path / "nested/products.db")
    for product in products:
        repo.save_product(product)
    return repo


def request(**changes):
    return ConfigurationCreate(keyboard_id="board", keycap_set_id="kit", key_color_map={"esc": "forest"}, **changes)


def test_roundtrip_survives_new_repository_instance(repository, products):
    saved = repository.save_configuration(request(name="First design"))
    restored = Repository(repository.path).get_configuration(saved.configuration.id)
    assert restored == saved
    assert restored.keyboard == products[0] and restored.keycap_set == products[1]
    assert restored.configuration.key_color_map == {"esc": "forest"}
    assert restored.configuration.date_created.utcoffset() is not None
    assert restored.compatibility.status == "unknown"


def test_canonical_url_lookup_and_evidence(tmp_path, products):
    repo = Repository(tmp_path / "products.db")
    keyboard = type(products[0]).model_validate({**products[0].model_dump(), "sourceUrl": "https://EXAMPLE.com:443/board#specs"})
    evidence = PageEvidence(source_url="https://example.com/board", final_url="https://example.com/board", title="Test evidence")
    saved = repo.save_product(keyboard, evidence)
    assert str(saved.source_url) == "https://example.com/board"
    assert repo.find_product("https://EXAMPLE.com:443/board#other", "keyboard") == saved
    assert repo.find_product("https://example.com/board", "keycaps") is None
    assert repo.get_evidence(saved.id) == evidence


def test_idempotent_import_and_conflicts_preserve_saved_products(repository, products):
    assert repository.save_product(products[0]) == products[0]
    for change in ({"model": "Changed"}, {"id": "duplicate-url"}):
        with pytest.raises(Conflict):
            repository.save_product(products[0].model_copy(update=change))
    with pytest.raises(Conflict):
        repository.save_product(products[1].model_copy(update={"id": "board"}))
    assert repository.get_product("board") == products[0]


@pytest.mark.parametrize("mapping", [{"fake": "forest"}, {"esc": "fake"}, {"": "forest"}, {"esc": ""}])
def test_invalid_maps_do_not_create_rows(repository, mapping):
    from pydantic import ValidationError
    with pytest.raises((InvalidConfiguration, ValidationError)):
        repository.save_configuration(ConfigurationCreate(keyboard_id="board", keycap_set_id="kit", key_color_map=mapping))
    assert repository.list_configurations() == []


def test_missing_and_wrong_product_types(repository):
    with pytest.raises(NotFound):
        repository.save_configuration(ConfigurationCreate(keyboard_id="missing", keycap_set_id="kit"))
    with pytest.raises(InvalidConfiguration):
        repository.save_configuration(ConfigurationCreate(keyboard_id="kit", keycap_set_id="board"))
    with pytest.raises(NotFound):
        repository.get_configuration("missing")
    with pytest.raises(NotFound):
        repository.get_product("' OR 1=1 --")
    assert repository.list_configurations() == []


def test_list_pagination_and_empty_mapping(repository):
    first = repository.save_configuration(ConfigurationCreate(keyboard_id="board", keycap_set_id="kit"))
    second = repository.save_configuration(request(name="O'Brien's design"))
    assert repository.list_configurations(limit=1)[0] == second.configuration
    assert repository.list_configurations(limit=1, offset=1)[0] == first.configuration


def test_concurrent_saves_have_unique_ids(repository):
    with ThreadPoolExecutor(max_workers=4) as pool:
        saved = list(pool.map(lambda _: repository.save_configuration(request()), range(8)))
    assert len({item.configuration.id for item in saved}) == 8
    assert len(repository.list_configurations()) == 8


def test_corrupt_stored_data_fails_cleanly(repository):
    saved = repository.save_configuration(request())
    with sqlite3.connect(repository.path) as db:
        db.execute("UPDATE configurations SET data='{}' WHERE id=?", (saved.configuration.id,))
    with pytest.raises(StorageError, match="invalid"):
        repository.get_configuration(saved.configuration.id)
    with pytest.raises(StorageError, match="invalid"):
        repository.list_configurations()


def test_foreign_keys_protect_saved_references(repository):
    repository.save_configuration(request())
    with sqlite3.connect(repository.path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM products WHERE id='board'")


def test_case_color_is_saved_without_mutating_product(repository, products):
    saved = repository.save_configuration(request(case_color="#F5F5F5"))
    assert repository.get_configuration(saved.configuration.id).configuration.case_color == "#F5F5F5"
    assert repository.get_product("board").case.color == products[0].case.color
    other = repository.save_configuration(request(case_color="#111111"))
    assert other.configuration.case_color == "#111111"
    assert repository.get_configuration(saved.configuration.id).configuration.case_color == "#F5F5F5"


@pytest.mark.parametrize("value", ["red", "#FFF", "#XXXXXX"])
def test_case_color_rejects_invalid_rgb_values(value):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        request(case_color=value)


def test_newer_schema_is_not_silently_overwritten(repository):
    with sqlite3.connect(repository.path) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(StorageError, match="schema version"):
        repository.get_product("board")


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.api.storage import get_repository
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: Repository(tmp_path / "api.db")
    with TestClient(app) as client:
        yield client


def test_api_manual_import_save_restore_contract(client, products):
    for kind, product in zip(("keyboard", "keycaps"), products):
        imported = client.post("/api/products/manual", json={"kind": kind, "product": product.model_dump(mode="json")})
        assert imported.status_code == 201
        assert client.get(f"/api/products/{product.id}").json() == imported.json()
    assert client.get("/api/keyboards/board").json()["layoutType"] == "75"
    assert client.get("/api/keycaps/kit").json()["colors"][0]["hex"] == "#2F5141"
    saved = client.post("/api/configurations", json=request(name="API design").model_dump(mode="json"))
    assert saved.status_code == 201
    result = saved.json()
    assert result["configuration"]["keyColorMap"] == {"esc": "forest"}
    assert result["compatibility"]["status"] == "unknown"
    assert client.get(f"/api/configurations/{result['configuration']['id']}").json() == result
    assert client.get("/api/configurations").json() == [result["configuration"]]


def test_api_errors_are_typed_and_do_not_write_partial_rows(client, products):
    assert client.get("/api/products/missing").status_code == 404
    assert client.post("/api/products/manual", json={"kind": "keyboard", "product": {}}).status_code == 422
    for kind, product in zip(("keyboard", "keycaps"), products):
        client.post("/api/products/manual", json={"kind": kind, "product": product.model_dump(mode="json")})
    assert client.get("/api/keyboards/kit").status_code == 404
    assert client.get("/api/keycaps/board").status_code == 404
    changed = products[0].model_dump(mode="json")
    changed["model"] = "Replacement"
    assert client.post("/api/products/manual", json={"kind": "keyboard", "product": changed}).status_code == 409
    invalid = request().model_dump(mode="json")
    invalid["keyColorMap"] = {"esc": "missing"}
    assert client.post("/api/configurations", json=invalid).status_code == 422
    invalid["keyColorMap"] = {"esc": ""}
    assert client.post("/api/configurations", json=invalid).status_code == 422
    assert client.get("/api/configurations").json() == []
    assert client.get("/api/configurations?limit=101").status_code == 422
    assert client.get("/api/configurations?offset=-1").status_code == 422


def test_database_path_is_relative_to_project_not_cwd(monkeypatch, tmp_path):
    from pathlib import Path
    from app.api.storage import get_repository
    from app.config import Settings
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None, database_path="data/example.db")
    assert get_repository(settings).path == Path(__file__).resolve().parents[2] / "data/example.db"


def test_api_database_failure_is_clean(client):
    from app.api.storage import get_repository
    class Broken:
        def get_product(self, product_id):
            raise StorageError("Local database could not be read or written.")
    client.app.dependency_overrides[get_repository] = lambda: Broken()
    response = client.get("/api/products/board")
    assert response.status_code == 503 and "detail" in response.json()
