"""Pluggable candidate data sources (X MCP, SuperGrok X Search, …)."""

from x2video.source.base import CandidateSource
from x2video.source.factory import create_source
from x2video.source.models import CandidateTweet

__all__ = [
    "CandidateSource",
    "CandidateTweet",
    "create_source",
]
