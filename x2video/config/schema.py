"""Configuration data models.

All field names and docstrings use CONTEXT.md glossary terms.
No vendor-specific names in config keys, values, or docstrings.
"""

from pydantic import BaseModel


class HardFilterConfig(BaseModel):
    """Hard filter thresholds — rule-based, no semantic judgment.

    Applied at the fetch stage to narrow candidates by time window
    and engagement metrics.
    """

    time_window_hours: int = 24
    min_likes: int = 100
    min_retweets: int = 10
    min_replies: int = 0
    views_threshold: int = 0


class CurationConfig(BaseModel):
    """Curation / LLM scoring parameters.

    Controls the second-stage filtering where an LLM scores candidates
    on their suitability for a Chinese short video.
    """

    top_n: int = 5
    blocking_mode: bool = True  # True = Gate 1 waits for user; False = direct
    max_candidates: int = 50


class LLMConfig(BaseModel):
    """LLM provider configuration (neutral naming)."""

    provider: str = "api"  # "api" = generic API-compatible endpoint
    api_base_url: str = ""
    api_key: str = ""  # overridden from env, never committed
    # NOTE: Validation (non-empty when provider="api") belongs at the
    # call site (curate.py, script.py), not here. Subcommands that don't
    # call LLM (fetch, card) must not be blocked by a missing key.
    model: str = ""
    timeout_seconds: int = 60
    max_tokens: int = 4096
    temperature: float = 0.7


class TTSConfig(BaseModel):
    """TTS provider configuration. Defaults to Edge free TTS.

    API fields are only read when provider == "api".
    """

    provider: str = "edge"  # "edge" or "api"
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
    # API mode fields (only used when provider == "api")
    api_base_url: str = ""
    api_key: str = ""  # overridden from env
    # NOTE: Validation (non-empty when provider="api") belongs at the
    # call site (render.py), not here. Subcommands that don't call TTS
    # (fetch, card, script) must not be blocked by a missing key.
    api_model: str = ""
    api_voice: str = ""
    api_format: str = "mp3"
    api_timeout_seconds: int = 60


class X2VideoConfig(BaseModel):
    """Root configuration — single source of truth for all tunable parameters."""

    domain_keywords: list[str] = [
        "AI",
        "artificial intelligence",
        "machine learning",
        "LLM",
    ]
    hard_filter: HardFilterConfig = HardFilterConfig()
    curation: CurationConfig = CurationConfig()
    llm: LLMConfig = LLMConfig()
    tts: TTSConfig = TTSConfig()
    work_dir: str = "work"
    final_dir: str = "final"
