"""Pipeline helpers: ledger, hard filter, script, cards HTML, ASS timing."""

from __future__ import annotations

from pathlib import Path

from x2video.config.schema import HardFilterConfig
from datetime import datetime, timedelta, timezone

from x2video.pipeline.card import (
    build_card_html,
    build_cover_html,
    build_opener_html,
    clip_display_text,
    is_image_url,
)
from x2video.pipeline.hard_filter import apply_hard_filter
from x2video.pipeline.ledger import Ledger
from x2video.pipeline.models import DigestScript, Pick, ScriptSegment
from x2video.pipeline.render import build_ass, build_ass_cues, format_ass_time
from x2video.pipeline.workdir import resolve_run_dir
from x2video.source.models import CandidateTweet
from x2video.util import (
    ensure_date_lead,
    format_count,
    format_md_date,
    parse_json_payload,
    punchline,
    split_subtitles,
)


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


def test_hard_filter_drops_stale_tweets() -> None:
    now = datetime.now(timezone.utc)
    cfg = HardFilterConfig(min_likes=0, min_retweets=0, max_age_hours=48)
    fresh = CandidateTweet(
        id="1",
        text="a",
        likes=10,
        retweets=1,
        created_at=now.isoformat().replace("+00:00", "Z"),
    )
    stale = CandidateTweet(
        id="2",
        text="b",
        likes=10,
        retweets=1,
        created_at=(now - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
    )
    out = apply_hard_filter([fresh, stale], cfg)
    assert [c.id for c in out] == ["1"]


def test_format_md_date_news_desk() -> None:
    assert format_md_date("2026-08-26T15:41:37Z") == "8月26日"


def test_punchline_is_short_hook() -> None:
    line = punchline("Google研究者证明，LLM推理验证器一直算错分数。改用过程优势验证器后效率提升。")
    assert 4 <= len(line) <= 14
    assert "。" not in line


def test_ensure_date_lead_prefixes_once() -> None:
    assert ensure_date_lead("DeepMind发了论文。", "8月27日") == "8月27日，DeepMind发了论文。"
    assert ensure_date_lead("8月27日，已经有了。", "8月27日") == "8月27日，已经有了。"


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
    assert script.opener_text() == "开场。"
    assert spoken[0] == "第一条。"
    assert "开场" not in spoken[0]
    assert spoken[1].endswith("下期见。")
    assert "第二条" in spoken[1]


def test_parse_json_payload_fenced() -> None:
    data = parse_json_payload("```json\n{\"tweets\":[1]}\n```")
    assert data["tweets"] == [1]


def test_split_subtitles_breaks_on_punctuation() -> None:
    lines = split_subtitles("今天有大新闻。模型能在本地跑了！你觉得呢")
    assert any("大新闻" in line for line in lines)
    assert all(len(line) <= 22 for line in lines)


def test_split_subtitles_does_not_leave_orphan_period() -> None:
    text = "Google DeepMind新论文直接把LLM推理验证器打分方式推翻了。他们用过程优势验证器代替老方法。"
    lines = split_subtitles(text)
    assert all(line.strip() not in {"。", "！", "？"} for line in lines)
    assert any("推翻了" in line for line in lines)


def test_format_count() -> None:
    assert format_count(999) == "999"
    assert format_count(1500) == "1.5K"
    assert format_count(1_200_000) == "1.2M"


def test_opener_html_has_hook() -> None:
    doc = build_opener_html("圈里这几条都在转", count=5, date_label="8月27日")
    assert "圈里这几条都在转" in doc
    assert "5 条热帖" in doc
    assert "今日外网" in doc
    assert "8月27日" in doc


def test_cover_html_is_news_desk() -> None:
    doc = build_cover_html(
        title="本地模型能跑了",
        date_label="8月27日",
        sub="2 条热帖",
        bg_style="background:#000",
    )
    assert "8月27日" in doc
    assert "本地模型能跑了" in doc
    assert "1080px" in doc and "1440px" in doc


def test_clip_display_text_adds_ellipsis() -> None:
    long = "A" * 80 + "\n" + "B" * 200
    clipped = clip_display_text(long, 120)
    assert clipped.endswith("…")
    assert len(clipped) < len(long)


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
        created_at="2026-08-26T12:00:00Z",
    )
    doc = build_card_html(pick, index=2, total=6)
    assert "你好世界" in doc
    assert "&lt;b&gt;world&lt;/b&gt;" in doc
    assert "@alice" in doc or ">alice<" in doc
    assert "border-left" not in doc
    assert "中文翻译" not in doc
    assert "X2Video" not in doc
    assert "译自英文" in doc
    assert "02" in doc
    assert "punch" in doc
    assert "background-image" in doc or "radial-gradient" in doc
    assert "8月26日" in doc


def test_ass_timing_covers_duration() -> None:
    ass = build_ass(["第一句", "第二句"], 4.0)
    assert "第一句" in ass
    assert format_ass_time(4.0) in ass


def test_ass_cues_use_exact_times() -> None:
    ass = build_ass_cues([("先看这条", 0.0, 1.2), ("下一条更狠", 1.2, 2.5)])
    assert "先看这条" in ass
    assert format_ass_time(1.2) in ass
    assert format_ass_time(2.5) in ass
