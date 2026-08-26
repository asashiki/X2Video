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

        cfg = config.model_copy()
        if not (cfg.api_base_url or "").strip():
            cfg.api_base_url = "https://api.x.ai/v1"
        if not (cfg.model or "").strip():
            cfg.model = "grok-4-1-fast-reasoning"
        return APICompatibleLLMProvider(cfg)

    raise ValueError(
        f"Unknown LLM provider: '{config.provider}'. "
        "Set [llm].provider to \"api\" for a generic API-compatible endpoint."
    )
