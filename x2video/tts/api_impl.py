"""API-compatible TTS provider.

Used when TTS_PROVIDER=api. Sends TTS requests to a configured
compatible endpoint via httpx.
"""

from pathlib import Path

import httpx

from x2video.config.schema import TTSConfig
from x2video.tts.base import TTSProvider


class APITTSProvider(TTSProvider):
    """TTS provider that speaks a generic API-compatible TTS protocol."""

    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.api_base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.api_timeout_seconds,
        )

    async def synthesize(
        self, text: str, output_path: Path, **kwargs
    ) -> Path:
        """Send a TTS request to the configured API endpoint."""
        body = {
            "model": kwargs.get("api_model", self.config.api_model),
            "input": text,
            "voice": kwargs.get("api_voice", self.config.api_voice),
            "response_format": kwargs.get("api_format", self.config.api_format),
        }
        response = await self._client.post("/audio/speech", json=body)
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return output_path

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()
