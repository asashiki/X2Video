"""LLM provider factory — dispatching on config.provider."""

from x2video.config.schema import LLMConfig
from x2video.llm.base import LLMProvider


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """Instantiate an LLM provider based on configuration.

    Args:
        config: Validated LLM configuration.

    Returns:
        A concrete LLMProvider instance.

    Raises:
        ValueError: If config.provider is not recognized.
    """
    if config.provider == "api":
        from x2video.llm.api_impl import APICompatibleLLMProvider

        return APICompatibleLLMProvider(config)

    raise ValueError(
        f"Unknown LLM provider: '{config.provider}'. "
        "Set [llm].provider to \"api\" for a generic API-compatible endpoint."
    )
