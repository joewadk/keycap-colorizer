import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from app.agents.models import ProductUnderstanding
from app.agents.provider import ModelError, OpenAIModel
from app.agents.service import UnderstandingService, configured_model
from app.config import Settings
from app.ingestion.models import PageEvidence


EVIDENCE = PageEvidence(source_url="https://example.com/board", final_url="https://example.com/board",
                        title="Compact ANSI 75 keyboard", text_excerpt="Untrusted product text")


def facts(**changes):
    return {"productType": "keyboard", "confidence": 0.95, "manufacturer": "Example",
            "name": "Compact 75", "layoutTemplate": "ANSI_75", "layoutConfidence": 0.9,
            "knob": None, "screen": None, "badge": None, "colorNames": ["Black"], "notes": [], **changes}


def analyze(*responses):
    model = AsyncMock()
    model.complete.side_effect = responses
    result = asyncio.run(UnderstandingService(model).understand(EVIDENCE))
    return result, model


def test_disabled_preserves_evidence_without_network():
    result = asyncio.run(UnderstandingService().understand(EVIDENCE))
    assert result.status == "disabled" and result.evidence == EVIDENCE
    assert result.understanding is None


def test_success_is_facts_not_geometry():
    result, model = analyze(json.dumps(facts()))
    assert result.status == "complete"
    assert result.understanding.layout_template == "ANSI_75"
    assert "keys" not in result.understanding.model_dump()
    assert model.complete.call_count == 1
    assert "untrusted" in model.complete.call_args.kwargs["instructions"]


@pytest.mark.parametrize("changes", [
    {"confidence": 0.4}, {"layoutConfidence": 0.4}, {"layoutTemplate": None},
    {"manufacturer": None}, {"name": None},
    {"productType": "unknown", "layoutTemplate": None},
])
def test_ambiguous_products_need_review(changes):
    result, model = analyze(json.dumps(facts(**changes)))
    assert result.status == "needs_review" and result.evidence == EVIDENCE
    assert model.complete.call_count == 1


def test_keycaps_do_not_require_a_layout():
    result, _ = analyze(json.dumps(facts(productType="keycaps", layoutTemplate=None, layoutConfidence=0)))
    assert result.status == "complete"


@pytest.mark.parametrize("bad", ["not JSON", "{}", json.dumps(facts(confidence=2)),
    json.dumps(facts(layoutTemplate="ISO_60")), json.dumps(facts(keys=[])),
    json.dumps(facts(productType="keycaps")), json.dumps(facts(knob="true"))])
def test_invalid_data_retries_once_then_succeeds(bad):
    result, model = analyze(bad, json.dumps(facts()))
    assert result.status == "complete" and model.complete.call_count == 2
    assert "previous response failed validation" in model.complete.call_args.kwargs["instructions"]


def test_two_invalid_results_fail_cleanly():
    result, model = analyze("SECRET bad data", "SECRET bad data")
    assert result.status == "failed" and model.complete.call_count == 2
    assert result.evidence == EVIDENCE and "SECRET" not in result.message


def test_provider_errors_are_not_retried():
    result, model = analyze(ModelError("AI request timed out."))
    assert result.status == "failed" and model.complete.call_count == 1


def test_oversized_metadata_does_not_make_paid_request():
    model = AsyncMock()
    evidence = EVIDENCE.model_copy(update={"products": [{"data": "x" * 61000}]})
    result = asyncio.run(UnderstandingService(model).understand(evidence))
    assert result.status == "needs_review"
    model.complete.assert_not_called()


def envelope(text=None, **changes):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": text or json.dumps(facts())}]}], **changes}


def invoke(handler):
    provider = OpenAIModel(SecretStr("test-secret"), "test-model", transport=httpx.MockTransport(handler))
    return asyncio.run(provider.complete(instructions="instructions", evidence="evidence",
                       schema=ProductUnderstanding.model_json_schema()))


def test_openai_wire_contract():
    def handler(request):
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == "Bearer test-secret"
        body = json.loads(request.content)
        assert body["store"] is False and body["model"] == "test-model"
        assert body["text"]["format"]["strict"] is True
        schema = body["text"]["format"]["schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        return httpx.Response(200, json=envelope())
    assert json.loads(invoke(handler))["name"] == "Compact 75"


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500])
def test_http_failures_hide_response_body(status):
    with pytest.raises(ModelError, match=f"HTTP {status}") as error:
        invoke(lambda request: httpx.Response(status, text="test-secret"))
    assert "test-secret" not in str(error.value)


@pytest.mark.parametrize("response", [[], {}, envelope(status="incomplete"),
    envelope(output=[]), envelope(output=[{"type": "message", "content": [{"type": "refusal"}]}])])
def test_bad_envelopes_fail_cleanly(response):
    with pytest.raises(ModelError):
        invoke(lambda request: httpx.Response(200, json=response))


def test_timeout_is_clean():
    def handler(request):
        raise httpx.ReadTimeout("test-secret")
    with pytest.raises(ModelError, match="timed out"):
        invoke(handler)


def test_settings_disable_by_default_and_require_both_credentials(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert configured_model(Settings(_env_file=None, ai_provider="")) is None
    with pytest.raises(ModelError, match="OPENAI_MODEL"):
        configured_model(Settings(_env_file=None, ai_provider="openai", openai_api_key="", openai_model=""))


@pytest.mark.parametrize("enabled", [True, False])
def test_capabilities_do_not_expose_secrets(enabled):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import get_settings
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None,
        ai_provider="openai" if enabled else "", openai_api_key="test-secret", openai_model="test-model")
    with TestClient(app) as client:
        response = client.get("/api/capabilities")
    assert response.status_code == 200 and response.json()["aiEnabled"] == enabled
    assert "test-secret" not in response.text
