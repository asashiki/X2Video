"""Candidate source protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from x2video.source.models import CandidateTweet


@runtime_checkable
class CandidateSource(Protocol):
    """Fetch candidate tweets for a set of domain keywords.

    Implementations must be replaceable (ADR-0001): X MCP is the MVP
    default; SuperGrok subscription OAuth + X Search is an alternative
    that bills against the subscription token quota instead of X API.
    """

    name: str

    def fetch(
        self,
        keywords: list[str],
        *,
        time_window_hours: int = 24,
        max_results: int = 50,
    ) -> list[CandidateTweet]:
        """Return recent tweets matching *keywords* within the time window."""
        ...
