"""API-compatible LLM provider implementation.

Sends API-compatible chat completion requests via httpx.
When ``api_key`` is empty, uses the SuperGrok OAuth access token.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from x2video.auth.oauth import GrokLoginRequiredError, get_access_token
from x2video.config.schema import LLMConfig
from x2video.llm.base import LLMProvider
from x2video.util import parse_json_payload


class APICompatibleLLMProvider(LLMProvider):
    """LLM provider that speaks an API-compatible chat completion protocol."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        base = (config.api_base_url or "https://api.x.ai/v1").rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=base,
            headers={"Content-Type": "application/json"},
            timeout=config.timeout_seconds,
        )

    def _headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        key = (self.config.api_key or "").strip()
        if not key:
            try:
                key = get_access_token(force_refresh=force_refresh)
            except GrokLoginRequiredError as exc:
                raise RuntimeError(
                    "LLM API key missing and no SuperGrok login. "
                    "Set X2VIDEO_LLM_API_KEY or run `x2video auth login`."
                ) from exc
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            "/chat/completions", json=body, headers=self._headers()
        )
        if response.status_code == 401:
            response = await self._client.post(
                "/chat/completions",
                json=body,
                headers=self._headers(force_refresh=True),
            )
        if response.status_code >= 400:
            detail = response.text[:800]
            raise RuntimeError(f"LLM HTTP {response.status_code}: {detail}")
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("LLM response was not a JSON object")
        return data

    @staticmethod
    def _content(data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise RuntimeError("LLM response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LLM response missing text content")
        return content

    async def complete(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> str:
        """Send a chat completion request and return the response text."""
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        return self._content(await self._post(body))

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        output_schema: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat completion and parse JSON. Falls back if schema mode fails."""
        base_body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        schema_body = {
            **base_body,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": output_schema, "strict": False},
            },
        }
        try:
            content = self._content(await self._post(schema_body))
        except RuntimeError:
            json_body = {**base_body, "response_format": {"type": "json_object"}}
            try:
                content = self._content(await self._post(json_body))
            except RuntimeError:
                hint = {
                    "role": "user",
                    "content": "Respond with ONLY a JSON object matching the requested schema.",
                }
                content = await self.complete([*messages, hint], **kwargs)
        parsed = parse_json_payload(content)
        if not isinstance(parsed, (dict, list)):
            raise RuntimeError("LLM structured output was not JSON")
        if isinstance(parsed, list):
            return {"items": parsed}
        return parsed

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()
