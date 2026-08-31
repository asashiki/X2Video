"""API-compatible TTS provider.

Used when TTS_PROVIDER=api. Speaks either a T2A-style JSON endpoint
or an OpenAI-compatible /audio/speech endpoint, depending on the URL.
"""

from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from x2video.config.schema import TTSConfig
from x2video.tts.base import TTSProvider


def _speed_from_rate(rate: str) -> float:
    text = (rate or "").strip()
    match = re.match(r"^([+-]?)(\d+(?:\.\d+)?)%?$", text)
    if not match:
        return 1.0
    sign, value = match.group(1), float(match.group(2))
    if text.endswith("%") or sign:
        delta = value / 100.0
        if sign == "-":
            delta = -delta
        elif sign == "" and not text.endswith("%"):
            return min(max(value, 0.5), 2.0)
        return min(max(1.0 + delta, 0.5), 2.0)
    return min(max(value, 0.5), 2.0)


def is_t2a_endpoint(url: str) -> bool:
    return "t2a" in (url or "").lower()


def decode_tts_audio(payload: object) -> bytes:
    """Accept hex, base64, or raw bytes from a TTS JSON body."""
    if isinstance(payload, bytes):
        return payload
    if not isinstance(payload, str) or not payload:
        raise RuntimeError("TTS API returned empty audio")
    compact = payload.strip()
    try:
        if re.fullmatch(r"[0-9a-fA-F]+", compact) and len(compact) % 2 == 0:
            return binascii.unhexlify(compact)
    except (binascii.Error, ValueError):
        pass
    try:
        return base64.b64decode(compact, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("TTS API audio could not be decoded") from exc


class APITTSProvider(TTSProvider):
    """TTS provider that speaks a generic API-compatible TTS protocol."""

    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        timeout = max(int(config.api_timeout_seconds or 60), 60)
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def synthesize(self, text: str, output_path: Path, **kwargs) -> Path:
        spoken = (text or "").strip()
        if not spoken:
            raise ValueError("TTS text is empty")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if is_t2a_endpoint(self.config.api_base_url):
            audio = await self._synthesize_t2a(spoken, **kwargs)
        else:
            audio = await self._synthesize_openai(spoken, **kwargs)
        output_path.write_bytes(audio)
        return output_path

    async def _synthesize_t2a(self, text: str, **kwargs) -> bytes:
        voice = kwargs.get("api_voice", self.config.api_voice)
        model = kwargs.get("api_model", self.config.api_model) or "speech-2.6-hd"
        fmt = kwargs.get("api_format", self.config.api_format) or "mp3"
        body = {
            "model": model,
            "text": text,
            "stream": False,
            "language_boost": "auto",
            "voice_setting": {
                "voice_id": voice,
                "speed": _speed_from_rate(self.config.rate),
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": fmt,
                "channel": 1,
            },
        }
        response = await self._client.post(self.config.api_base_url, json=body)
        response.raise_for_status()
        payload = response.json()
        status = (payload.get("base_resp") or {}).get("status_code")
        if status not in (0, None):
            message = (payload.get("base_resp") or {}).get("status_msg") or "unknown error"
            raise RuntimeError(f"TTS API failed: {message}")
        audio = (
            (payload.get("data") or {}).get("audio")
            or payload.get("audio")
            or payload.get("audio_file")
        )
        return decode_tts_audio(audio)

    async def _synthesize_openai(self, text: str, **kwargs) -> bytes:
        base = self.config.api_base_url.rstrip("/")
        parsed = urlparse(base)
        path = parsed.path or ""
        url = base if path.endswith("/audio/speech") else f"{base}/audio/speech"
        body = {
            "model": kwargs.get("api_model", self.config.api_model),
            "input": text,
            "voice": kwargs.get("api_voice", self.config.api_voice),
            "response_format": kwargs.get("api_format", self.config.api_format),
        }
        response = await self._client.post(url, json=body)
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        await self._client.aclose()
