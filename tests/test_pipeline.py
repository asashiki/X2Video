"""Pipeline helpers: ledger, hard filter, script, cards HTML, ASS timing."""

from __future__ import annotations

from pathlib import Path

from x2video.config.schema import HardFilterConfig
from x2video.pipeline.card import build_card_html, is_image_url
from x2video.pipeline.hard_filter import apply_hard_filter
from x2video.pipeline.ledger import Ledger
from x2video.pipeline.models import DigestScript, Pick, ScriptSegment
from x2video.pipeline.render import build_ass, format_ass_time
from x2video.pipeline.workdir import resolve_run_dir
from x2video.source.models import CandidateTweet
from x2video.util import format_count, parse_json_payload, split_subtitles


def test_ledger_seen_and_picks(tmp_path: Path) -> None:
    ledger = Ledger.load(tmp_path)
    assert not ledger.is_seen("1")
    ledger.mark_seen(["1", "2"])
    ledger.mark_picks(["2"], extra={"date": "2026-08-27"})
    ledger.save()
    loaded = Ledger.load(tmp_path)
    assert loaded.is_seen("1")
    assert loaded.is_pick("2")
    assert not loaded.is_pick("1")


def test_hard_filter_drops_low_engagement() -> None:
    cfg = HardFilterConfig(min_likes=100, min_retweets=10, min_replies=0, views_threshold=0)
    keep = CandidateTweet(id="1", text="a", likes=200, retweets=20)
    drop = CandidateTweet(id="2", text="b", likes=10, retweets=0)
    out = apply_hard_filter([keep, drop], cfg)
    assert [c.id for c in out] == ["1"]


def test_resolve_run_dir(tmp_path: Path) -> None:
    path = resolve_run_dir(tmp_path, "2026-08-27")
    assert path == tmp_path / "2026-08-27"
    assert path.exists()


def test_spoken_texts_wraps_hook_and_outro() -> None:
    script = DigestScript(
        hook="开场。",
        outro="下期见。",
        segments=[
            ScriptSegment(pick_id="a", narration="第一条。"),
            ScriptSegment(pick_id="b", narration="第二条。"),
        ],
    )
    spoken = script.spoken_texts()
    assert spoken[0].startswith("开场")
    assert "第一条" in spoken[0]
    assert spoken[1].endswith("下期见。")
    assert "第二条" in spoken[1]


def test_parse_json_payload_fenced() -> None:
    data = parse_json_payload("```json\n{\"tweets\":[1]}\n```")
    assert data["tweets"] == [1]


def test_split_subtitles_breaks_on_punctuation() -> None:
    lines = split_subtitles("今天有大新闻。模型能在本地跑了！你觉得呢")
    assert any("大新闻" in line for line in lines)
    assert all(len(line) <= 22 for line in lines)


def test_format_count() -> None:
    assert format_count(999) == "999"
    assert format_count(1500) == "1.5K"
    assert format_count(1_200_000) == "1.2M"


def test_is_image_url_skips_videos() -> None:
    assert is_image_url("https://pbs.twimg.com/media/abc.jpg")
    assert not is_image_url("https://video.twimg.com/amplify_video/1/vid/avc1/x.mp4")


def test_card_html_contains_translation() -> None:
    pick = Pick(
        id="99",
        text="Hello <b>world</b>",
        author_name="Alice",
        author_username="alice",
        translation="你好世界",
        likes=12,
        url="https://x.com/alice/status/99",
    )
    doc = build_card_html(pick)
    assert "你好世界" in doc
    assert "&lt;b&gt;world&lt;/b&gt;" in doc
    assert "@alice" in doc or ">alice<" in doc


def test_ass_timing_covers_duration() -> None:
    ass = build_ass(["第一句", "第二句"], 4.0)
    assert "第一句" in ass
    assert format_ass_time(4.0) in ass
