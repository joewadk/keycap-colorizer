import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.storage import get_repository
from app.ingestion.models import PageEvidence
from app.layouts import LayoutTemplate
from app.main import create_app
from app.storage.repository import Repository
from app.workflows.models import IntakeRequest, ReviewRequired, WorkflowStep
from app.workflows.normalization import classify, explicit_colors, keyboard_from_evidence, keycaps_from_evidence, stable_id
from app.workflows.service import FIXTURE_KEYBOARD_URL, FIXTURE_KEYCAP_URL, IngestionWorkflow

FIXTURES = Path(__file__).parent / "fixtures"


def evidence(name):
    from app.ingestion.extraction import extract_page
    url = FIXTURE_KEYBOARD_URL if name == "keyboard_product.html" else FIXTURE_KEYCAP_URL
    return extract_page((FIXTURES / name).read_text(), url)


def run_workflow(tmp_path, repository=None):
    repo = repository or Repository(tmp_path / "products.db")
    scraper = Mock(scrape=AsyncMock(side_effect=AssertionError("offline fixtures must not use a scraper")))
    image_cache = Mock(download=AsyncMock(side_effect=AssertionError("explicit fixture colors must not download images")))
    workflow = IngestionWorkflow(repo, scraper, tmp_path, image_cache)
    events = []

    async def progress(step, message):
        events.append((step, message))

    result = asyncio.run(workflow.run(IntakeRequest(keyboard_url=FIXTURE_KEYBOARD_URL,
        keycap_url=FIXTURE_KEYCAP_URL), progress))
    return result, events, repo, scraper, image_cache


def test_deterministic_classification_and_normalization():
    keyboard_evidence = evidence("keyboard_product.html")
    keycap_evidence = evidence("keycap_product.html")
    assert classify(keyboard_evidence) == "keyboard"
    assert classify(keycap_evidence) == "keycaps"
    board, warnings = keyboard_from_evidence(keyboard_evidence)
    assert board.layout_type == "75" and len(board.keys) == 84
    assert board.manufacturer == "Example" and board.case.material == "Aluminum"
    assert board.id == stable_id("keyboard", FIXTURE_KEYBOARD_URL)
    assert any("neutral" in warning for warning in warnings)
    colors = explicit_colors(keycap_evidence)
    assert [(color.name, color.hex) for color in colors] == [
        ("Bone", "#D8DBD1"), ("Moss", "#78936A"), ("Forest", "#2F5141"),
        ("Clay", "#C5795E"), ("Charcoal", "#343A38"),
    ]
    keycaps, warnings = keycaps_from_evidence(keycap_evidence)
    assert keycaps.profile == "Cherry" and keycaps.colors == colors
    assert any("inventory" in warning for warning in warnings)


def test_classification_prioritizes_product_identity_over_accessory_mentions():
    keyboard = PageEvidence(
        source_url="https://shop.example/keyboard",
        final_url="https://shop.example/keyboard",
        title="Keychron Q1 QMK Custom Mechanical Keyboard - Version 2",
        description="A fully customized 75% layout mechanical keyboard.",
        text_excerpt="Keycaps PBT keycaps Cherry profile keycap sets and other frequently bought accessories.",
    )
    keycaps = PageEvidence(
        source_url="https://shop.example/keycaps",
        final_url="https://shop.example/keycaps",
        title="PBT Keycap Set for Mechanical Keyboard",
        text_excerpt="Compatible keyboard accessories.",
    )
    assert classify(keyboard) == "keyboard"
    assert classify(keycaps) == "keycaps"


@pytest.mark.parametrize("page", [
    PageEvidence(source_url="https://example.com/unknown", final_url="https://example.com/unknown", title="Mystery item"),
    PageEvidence(source_url="https://example.com/split", final_url="https://example.com/split", title="Split keyboard", text_excerpt="Ergonomic split layout"),
])
def test_uncertain_or_unsupported_keyboard_requires_review(page):
    assert classify(page) in {"unknown", "keyboard"}
    with pytest.raises(ReviewRequired, match="layout|name"):
        keyboard_from_evidence(page)


def test_keycaps_without_codes_or_samples_require_review():
    page = PageEvidence(source_url="https://example.com/caps", final_url="https://example.com/caps",
                        title="Blue keycaps", text_excerpt="Cherry profile PBT keycaps")
    with pytest.raises(ReviewRequired, match="colors"):
        keycaps_from_evidence(page)


def test_fixture_workflow_emits_ordered_progress_and_saves_products(tmp_path):
    result, events, repo, scraper, image_cache = run_workflow(tmp_path)
    assert result.keyboard.layout_type == "75"
    assert result.keycap_set.colors[0].hex == "#D8DBD1"
    assert result.compatibility.status == "unknown"
    assert result.cached_products == []
    steps = [step for step, _ in events]
    assert steps == [
        WorkflowStep.CHECKING_CACHE,
        WorkflowStep.FETCHING_PAGE, WorkflowStep.EXTRACTING_METADATA,
        WorkflowStep.CLASSIFYING_PRODUCT, WorkflowStep.ANALYZING_LAYOUT, WorkflowStep.SAVING,
        WorkflowStep.FETCHING_PAGE, WorkflowStep.EXTRACTING_METADATA,
        WorkflowStep.CLASSIFYING_PRODUCT, WorkflowStep.EXTRACTING_COLORS, WorkflowStep.SAVING,
        WorkflowStep.VALIDATING,
    ]
    assert repo.find_product(FIXTURE_KEYBOARD_URL, "keyboard") == result.keyboard
    assert repo.get_evidence(result.keyboard.id).title == "Compact 75 Keyboard"
    scraper.scrape.assert_not_called()
    image_cache.download.assert_not_called()


def test_second_workflow_uses_normalized_product_cache(tmp_path):
    first, _, repo, _, _ = run_workflow(tmp_path)
    second, events, _, scraper, images = run_workflow(tmp_path, repo)
    assert second.keyboard == first.keyboard and second.keycap_set == first.keycap_set
    assert second.cached_products == ["keyboard", "keycaps"]
    assert [step for step, _ in events] == [WorkflowStep.CHECKING_CACHE, WorkflowStep.VALIDATING]
    scraper.scrape.assert_not_called()
    images.download.assert_not_called()


def test_api_fixture_job_progresses_to_complete_and_reuses_cache(tmp_path):
    repo = Repository(tmp_path / "api.db")
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repo
    with TestClient(app) as client:
        fixture = client.get("/api/ingestion/fixtures")
        assert fixture.status_code == 200 and "no network" in fixture.json()["message"]
        request = {"keyboardUrl": FIXTURE_KEYBOARD_URL, "keycapUrl": FIXTURE_KEYCAP_URL}
        created = client.post("/api/products/ingest", json=request)
        assert created.status_code == 202 and created.json()["status"] == "queued"
        job_id = created.json()["id"]
        for _ in range(100):
            job = client.get(f"/api/products/ingest/{job_id}").json()
            if job["status"] != "running" and job["status"] != "queued":
                break
        assert job["status"] == "complete", job
        assert job["step"] == "COMPLETE"
        assert job["result"]["keyboard"]["layoutType"] == "75"
        assert job["result"]["keycapSet"]["colors"][2]["name"] == "Forest"
        assert [event["step"] for event in job["events"]][-1] == "COMPLETE"
        second_id = client.post("/api/products/ingest", json=request).json()["id"]
        for _ in range(100):
            second = client.get(f"/api/products/ingest/{second_id}").json()
            if second["status"] == "complete":
                break
        assert second["result"]["cachedProducts"] == ["keyboard", "keycaps"]


def test_api_rejects_bad_urls_before_job_creation(tmp_path):
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: Repository(tmp_path / "api.db")
    with TestClient(app) as client:
        response = client.post("/api/products/ingest", json={"keyboardUrl": "http://localhost/board", "keycapUrl": FIXTURE_KEYCAP_URL})
        assert response.status_code == 422
        assert app.state.ingestion_jobs.jobs == {}
        assert client.get("/api/products/ingest/missing").status_code == 404


def test_api_rejects_the_same_page_for_keyboard_and_keycaps(tmp_path):
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: Repository(tmp_path / "api.db")
    with TestClient(app) as client:
        response = client.post("/api/products/ingest", json={
            "keyboardUrl": "https://shop.example/product",
            "keycapUrl": "https://shop.example/product",
        })
        assert response.status_code == 422
        assert "two different product pages" in response.json()["detail"]
        assert app.state.ingestion_jobs.jobs == {}


@pytest.mark.parametrize("provider,kind", [("playwright", "keyboard"), ("firecrawl", "keycap")])
def test_load_failures_identify_reader_and_product(tmp_path, provider, kind):
    from app.ingestion.urls import IntakeError
    from app.workflows.jobs import IngestionJobs

    url = "https://shop.example/product?tracking=private-value"
    scraper = Mock(provider=provider, scrape=AsyncMock(side_effect=IntakeError("Page timed out.")))
    workflow = IngestionWorkflow(Repository(tmp_path / "products.db"), scraper, tmp_path)
    request = IntakeRequest(
        keyboard_url=url if kind == "keyboard" else FIXTURE_KEYBOARD_URL,
        keycap_url=url if kind == "keycap" else FIXTURE_KEYCAP_URL,
        provider=provider,
    )

    async def run():
        jobs = IngestionJobs()
        created = jobs.create(request, workflow)
        await asyncio.gather(*jobs.tasks)
        return jobs.get(created.id)

    job = asyncio.run(run())
    reader = "Playwright" if provider == "playwright" else "Firecrawl"
    assert job.status == "failed"
    assert job.message == f"{reader} could not read the {kind} page on shop.example. Page timed out."
    assert "private-value" not in job.model_dump_json()
    assert any(f"{kind} product page on shop.example with {reader}" in event.message for event in job.events)
