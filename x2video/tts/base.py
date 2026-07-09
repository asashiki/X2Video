"""Abstract TTS provider interface.

Neutral naming per ADR-0007 — no vendor/model names in class names,
method signatures, or docstrings.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Abstract base for TTS providers — converts text to spoken audio.

    Interface designed for N-item digest from day one (ADR-0003):
    synthesize_batch() accepts a list of text segments, producing
    N audio files for the digest's N picks.
    """

    @abstractmethod
    async def synthesize(
        self, text: str, output_path: Path, **kwargs
    ) -> Path:
        """Convert a single text segment to an audio file.

        Args:
            text: The narration text to speak.
            output_path: Where to write the audio (e.g. work/audio/segment_01.mp3).
            **kwargs: Provider-specific overrides (voice, rate, etc.).

        Returns:
            Path to the written audio file.
        """
        ...

    async def synthesize_batch(
        self, segments: list[str], output_dir: Path, **kwargs
    ) -> list[Path]:
        """Convert N text segments to N audio files (digest narration).

        Default implementation loops synthesize(). Providers may override
        with a more efficient batch implementation.

        Args:
            segments: List of narration text segments (one per pick).
            output_dir: Directory for the output audio files.
            **kwargs: Provider-specific overrides.

        Returns:
            List of paths to the written audio files.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for i, text in enumerate(segments):
            p = output_dir / f"segment_{i:02d}.mp3"
            paths.append(await self.synthesize(text, p, **kwargs))
        return paths
