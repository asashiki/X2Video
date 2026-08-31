"""Config discovery and environment overrides."""

from __future__ import annotations

from pathlib import Path

from x2video.config.loader import load_config
from x2video.tts.api_impl import _speed_from_rate, decode_tts_audio, is_t2a_endpoint


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


def test_machine_t2a_env_selects_api_tts(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / "x2video.toml"
    cfg_path.write_text('domain_keywords = ["AI"]\n[tts]\nprovider = "edge"\n', encoding="utf-8")
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("X2VIDEO_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("X2VIDEO_TTS_API_KEY", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "")
    monkeypatch.setenv("MINIMAX_API_BASE_URL", "https://api.example.test/v1/t2a_v2")
    monkeypatch.setenv("MINIMAX_CN_API_KEY", "cn-secret")
    monkeypatch.setenv("MINIMAX_VOICE_ID_MAI", "MaiClone")
    cfg = load_config(str(cfg_path))
    assert cfg.tts.provider == "api"
    assert cfg.tts.api_base_url.endswith("/t2a_v2")
    assert cfg.tts.api_voice == "MaiClone"
    assert cfg.tts.api_key


def test_t2a_audio_decode_and_speed() -> None:
    assert is_t2a_endpoint("https://api.example.test/v1/t2a_v2")
    assert not is_t2a_endpoint("https://api.example.test/v1")
    assert decode_tts_audio("4869") == b"Hi"
    assert _speed_from_rate("+12%") == 1.12
