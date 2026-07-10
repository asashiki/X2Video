"""Edge TTS provider — free, no API key required.

Uses the `edge-tts` library. This provider is the default.
"""

from pathlib import Path

import edge_tts

from x2video.config.schema import TTSConfig
from x2video.tts.base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """TTS provider backed by the Edge free TTS service."""

    def __init__(self, config: TTSConfig) -> None:
        self.config = config

    async def synthesize(
        self, text: str, output_path: Path, **kwargs
    ) -> Path:
        """Convert text to speech using Edge TTS.

        Args:
            text: Narration text.
            output_path: Destination MP3 path.
        """
        voice = kwargs.get("voice", self.config.voice)
        rate = kwargs.get("rate", self.config.rate)
        volume = kwargs.get("volume", self.config.volume)
        pitch = kwargs.get("pitch", self.config.pitch)

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
        await communicate.save(str(output_path))
        return output_path
