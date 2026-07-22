"""Shared candidate tweet model for all data sources."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CandidateTweet(BaseModel):
    """A tweet that may enter Hard Filter / Curation.

    Field names follow CONTEXT.md: this is the raw unit before it becomes
    a scored Candidate. Sources must fill as many fields as they can;
    missing optional metrics default to 0 / empty.
    """

    id: str
    text: str
    created_at: str = ""
    author_id: str = ""
    author_name: str = ""
    author_username: str = ""
    author_avatar_url: str = ""
    author_verified: bool = False
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    url: str = ""
    lang: str = ""
    media_urls: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    def engagement_score(self) -> int:
        """Simple engagement proxy used by hard-filter helpers."""
        return self.likes + self.retweets * 2 + self.replies
