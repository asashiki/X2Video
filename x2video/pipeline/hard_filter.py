"""Hard Filter — rule-based engagement / time-window thresholds."""

from __future__ import annotations

from x2video.config.schema import HardFilterConfig
from x2video.source.models import CandidateTweet


def passes_hard_filter(
    candidate: CandidateTweet,
    config: HardFilterConfig,
) -> bool:
    if candidate.likes < config.min_likes:
        return False
    if candidate.retweets < config.min_retweets:
        return False
    if candidate.replies < config.min_replies:
        return False
    if config.views_threshold > 0 and candidate.views < config.views_threshold:
        return False
    return True


def apply_hard_filter(
    candidates: list[CandidateTweet],
    config: HardFilterConfig,
) -> list[CandidateTweet]:
    return [c for c in candidates if passes_hard_filter(c, config)]
