"""API-compatible LLM provider implementation.

Sends API-compatible chat completion requests via httpx.
"""

from typing import Any

import httpx

from x2video.config.schema import LLMConfig
from x2video.llm.base import LLMProvider


class APICompatibleLLMProvider(LLMProvider):
    """LLM provider that speaks an API-compatible chat completion protocol."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.api_base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout_seconds,
        )

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
        response = await self._client.post("/chat/completions", json=body)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        output_schema: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat completion with JSON Schema structured output."""
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": output_schema,
                },
            },
        }
        response = await self._client.post("/chat/completions", json=body)
        response.raise_for_status()
        data = response.json()
        import json

        return json.loads(data["choices"][0]["message"]["content"])

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()
