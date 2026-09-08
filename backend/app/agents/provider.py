"""Transport boundary: providers return JSON, never domain geometry."""
import asyncio
import json
from typing import Protocol

import httpx
from pydantic import SecretStr


class ModelError(ValueError):
    pass


class StructuredModel(Protocol):
    async def complete(self, *, instructions: str, evidence: str, schema: dict) -> str: ...


class OpenAIModel:
    def __init__(self, api_key: SecretStr, model: str, *, transport=None):
        if not api_key.get_secret_value().strip() or not model.strip():
            raise ModelError("Configure OPENAI_API_KEY and OPENAI_MODEL to enable AI.")
        self._key = api_key
        self._model = model.strip()
        self._transport = transport

    async def complete(self, *, instructions: str, evidence: str, schema: dict) -> str:
        try:
            async with asyncio.timeout(65):
                async with httpx.AsyncClient(transport=self._transport, timeout=60, trust_env=False) as client:
                    async with client.stream(
                        "POST", "https://api.openai.com/v1/responses",
                        headers={"Authorization": f"Bearer {self._key.get_secret_value()}"},
                        json={"model": self._model, "store": False,
                              "instructions": instructions, "input": evidence,
                              "max_output_tokens": 4000,
                              "text": {"format": {"type": "json_schema", "name": "product_understanding",
                                                  "strict": True, "schema": schema}}},
                    ) as response:
                        if response.status_code != 200:
                            raise ModelError(f"AI request failed (HTTP {response.status_code}). Check model access, key, and quota.")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 1_000_000:
                                raise ModelError("AI response exceeded the size limit.")
            data = json.loads(body)
            if data.get("status") != "completed":
                raise ModelError("AI response was incomplete. Try again or review the product manually.")
            texts = []
            for item in data.get("output", []):
                if item.get("type") != "message":
                    continue
                for part in item.get("content", []):
                    if part.get("type") == "refusal":
                        raise ModelError("AI declined this product analysis. Review the product manually.")
                    if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                        texts.append(part["text"])
            if len(texts) != 1:
                raise ModelError("AI returned no single structured product result.")
            return texts[0]
        except (httpx.TimeoutException, TimeoutError):
            raise ModelError("AI request timed out. Try again later.") from None
        except httpx.HTTPError:
            raise ModelError("Could not contact the AI provider.") from None
        except (ValueError, TypeError, AttributeError) as error:
            if isinstance(error, ModelError):
                raise
            raise ModelError("AI provider returned an invalid response envelope.") from None
