"""Factory for candidate data sources."""

from __future__ import annotations

from x2video.config.schema import SourceConfig, X2VideoConfig
from x2video.source.base import CandidateSource
from x2video.source.grok import DEFAULT_GROK_SEARCH_MODEL, GrokXSearchSource
from x2video.source.x_mcp import XMCPSource


def create_source(config: X2VideoConfig | SourceConfig) -> CandidateSource:
    """Instantiate a candidate source from config.

    Accepts either the root :class:`X2VideoConfig` or a bare
    :class:`SourceConfig`.
    """
    if isinstance(config, SourceConfig):
        source_cfg = config
        min_likes = 0
        min_retweets = 0
    else:
        source_cfg = config.source
        min_likes = config.hard_filter.min_likes
        min_retweets = config.hard_filter.min_retweets

    provider = (source_cfg.provider or "x_mcp").lower().strip()

    if provider in {"grok", "subscription", "xai_oauth", "supergrok"}:
        model = source_cfg.model or DEFAULT_GROK_SEARCH_MODEL
        return GrokXSearchSource(
            model=model,
            api_base=source_cfg.api_base or "https://api.x.ai/v1",
            min_likes=min_likes,
            min_retweets=min_retweets,
            timeout=float(source_cfg.timeout_seconds),
        )

    if provider in {"x_mcp", "x", "mcp"}:
        return XMCPSource()

    raise ValueError(
        f"Unknown source provider: '{source_cfg.provider}'. "
        'Use "x_mcp" (X official MCP + Bearer token) or '
        '"grok" (SuperGrok OAuth + X Search).'
    )
