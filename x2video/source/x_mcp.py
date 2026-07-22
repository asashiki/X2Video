"""X official MCP data source (placeholder until M1 lands).

Configured with an app-only Bearer token (``X_BEARER_TOKEN`` / env).
This module exists so ``source.provider = "x_mcp"`` is a valid choice
and the factory can dispatch; real MCP search is tracked in issue #1.
"""

from __future__ import annotations

import os

from x2video.source.models import CandidateTweet


class XMCPSource:
    """Native X MCP source — not yet implemented."""

    name = "x_mcp"

    def __init__(self, bearer_token: str | None = None) -> None:
        self.bearer_token = bearer_token or os.environ.get("X_BEARER_TOKEN", "")

    def fetch(
        self,
        keywords: list[str],
        *,
        time_window_hours: int = 24,
        max_results: int = 50,
    ) -> list[CandidateTweet]:
        if not self.bearer_token:
            raise RuntimeError(
                "X MCP source requires X_BEARER_TOKEN (or pass bearer_token). "
                "Alternatively set [source].provider = \"grok\" and run "
                "`x2video auth login` to use SuperGrok subscription tokens."
            )
        raise NotImplementedError(
            "X official MCP search is not implemented yet (issue #1). "
            "Use [source].provider = \"grok\" with `x2video auth login` "
            "to fetch via SuperGrok X Search in the meantime."
        )
