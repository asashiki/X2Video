"""Hard Filter — rule-based engagement / time-window thresholds."""

from __future__ import annotations

from x2video.config.schema import HardFilterConfig
from x2video.source.models import CandidateTweet
from x2video.util import tweet_age_hours


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
    if not is_fresh(candidate, config.max_age_hours):
        return False
    return True


def is_fresh(candidate: CandidateTweet, max_age_hours: int) -> bool:
    if max_age_hours <= 0:
        return True
    age = tweet_age_hours(candidate.created_at)
    if age is None:
        return True
    return age <= max_age_hours


def apply_hard_filter(
    candidates: list[CandidateTweet],
    config: HardFilterConfig,
) -> list[CandidateTweet]:
    return [c for c in candidates if passes_hard_filter(c, config)]
