"""TTS provider factory — dispatching on config.provider."""

from x2video.config.schema import TTSConfig
from x2video.tts.base import TTSProvider


def create_tts_provider(config: TTSConfig) -> TTSProvider:
    """Instantiate a TTS provider based on configuration.

    Args:
        config: Validated TTS configuration.

    Returns:
        A concrete TTSProvider instance.

    Raises:
        ValueError: If config.provider is not recognized.
    """
    if config.provider == "edge":
        from x2video.tts.edge_impl import EdgeTTSProvider

        return EdgeTTSProvider(config)

    if config.provider == "api":
        from x2video.tts.api_impl import APITTSProvider

        return APITTSProvider(config)

    raise ValueError(
        f"Unknown TTS provider: '{config.provider}'. "
        "Set [tts].provider to \"edge\" (free) or \"api\" (external service)."
    )
