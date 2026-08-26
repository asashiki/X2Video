"""Config discovery and environment overrides."""

from __future__ import annotations

from pathlib import Path

from x2video.config.loader import load_config


def test_env_override_nested_and_top_level(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / "x2video.toml"
    cfg_path.write_text(
        'domain_keywords = ["AI"]\n[hard_filter]\nmin_likes = 100\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("X2VIDEO_HARD_FILTER_MIN_LIKES", "500")
    monkeypatch.setenv("X2VIDEO_WORK_DIR", str(tmp_path / "w"))
    monkeypatch.setenv("X2VIDEO_LLM_API_KEY", "secret-key")
    monkeypatch.setenv("TTS_PROVIDER", "edge")
    cfg = load_config(str(cfg_path))
    assert cfg.hard_filter.min_likes == 500
    assert cfg.work_dir == str(tmp_path / "w")
    assert cfg.llm.api_key == "secret-key"
    assert cfg.tts.provider == "edge"
