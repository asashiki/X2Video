"""Configuration file discovery and loading.

Resolution order:
1. --config CLI flag (passed as explicit path)
2. X2VIDEO_CONFIG environment variable
3. ./x2video.toml (current working directory)
4. ~/.config/x2video/config.toml

TOML provides structure; .env provides secrets (API keys).
Env vars with the X2VIDEO_ prefix override the corresponding
TOML fields after merging.
"""

import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # pragma: no cover

from dotenv import load_dotenv
from pydantic import ValidationError

from x2video.config.schema import X2VideoConfig

_TOP_LEVEL = {"work_dir", "final_dir", "domain_keywords"}
_SECTIONS = ("hard_filter", "curation", "llm", "tts", "source")
_TTS_ALIASES = {
    "TTS_PROVIDER": "provider",
    "TTS_VOICE": "voice",
    "TTS_RATE": "rate",
    "TTS_VOLUME": "volume",
    "TTS_PITCH": "pitch",
    "TTS_API_BASE_URL": "api_base_url",
    "TTS_API_KEY": "api_key",
    "TTS_API_MODEL": "api_model",
    "TTS_API_VOICE": "api_voice",
    "TTS_API_FORMAT": "api_format",
    "TTS_API_TIMEOUT_SECONDS": "api_timeout_seconds",
}


def _find_config(config_path: str | None = None) -> Path | None:
    """Resolve the config file path via the standard precedence chain."""
    if config_path:
        p = Path(config_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Config file not found: {config_path}")

    env_path = os.environ.get("X2VIDEO_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    cwd_path = Path("x2video.toml")
    if cwd_path.exists():
        return cwd_path

    home_path = Path.home() / ".config" / "x2video" / "config.toml"
    if home_path.exists():
        return home_path

    return None


def _load_dotenv() -> dict[str, str]:
    """Load `.env` from the repo root if present.

    Only uses dotenv for secrets (API keys, tokens).
    Structure/tunables belong in the TOML file.
    """
    for anchor in (Path.cwd(), Path(__file__).resolve().parent.parent.parent):
        env_file = anchor / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break
    return {}


def _ensure_section(result: dict, section: str) -> dict:
    current = result.get(section)
    if not isinstance(current, dict):
        current = {}
        result[section] = current
    return current


def _apply_tts_aliases(result: dict) -> None:
    """Honor unprefixed TTS_* names from docs/tts-config.md."""
    tts = _ensure_section(result, "tts")
    for env_key, field in _TTS_ALIASES.items():
        if env_key in os.environ:
            tts[field] = os.environ[env_key]


def _env_override(base: dict, prefix: str = "X2VIDEO_") -> dict:
    """Apply env var overrides to the nested config dict.

    Maps:
        X2VIDEO_LLM_API_KEY          -> llm.api_key
        X2VIDEO_HARD_FILTER_MIN_LIKES -> hard_filter.min_likes
        X2VIDEO_WORK_DIR             -> work_dir
        TTS_PROVIDER                 -> tts.provider (alias)
    """
    result = dict(base)
    _apply_tts_aliases(result)
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        config_key = key[len(prefix):].lower()
        if config_key in _TOP_LEVEL:
            if config_key == "domain_keywords":
                result[config_key] = [s.strip() for s in value.split(",") if s.strip()]
            else:
                result[config_key] = value
            continue
        matched = False
        for section in sorted(_SECTIONS, key=len, reverse=True):
            token = section + "_"
            if config_key.startswith(token):
                field = config_key[len(token):]
                _ensure_section(result, section)[field] = value
                matched = True
                break
        if not matched:
            result[config_key] = value
    return result


def _toml_to_nested(raw: dict) -> dict:
    """Convert a flat-ish TOML dict into the nested structure X2VideoConfig expects.

    Top-level keys like hard_filter, curation, llm, tts become nested dicts.
    """
    nested: dict = {}
    sub_tables: dict[str, dict] = {
        "hard_filter": {},
        "curation": {},
        "llm": {},
        "tts": {},
        "source": {},
    }
    for key, value in raw.items():
        if key in sub_tables:
            sub_tables[key] = value if isinstance(value, dict) else {}
        else:
            nested[key] = value
    for name, table in sub_tables.items():
        if table:
            nested[name] = table
    return nested


def load_config(config_path: str | None = None) -> X2VideoConfig:
    """Load and return the fully resolved X2VideoConfig.

    Args:
        config_path: Explicit path to a TOML config file. When None, the
            standard discovery chain is used.

    Returns:
        A validated X2VideoConfig instance with TOML values and env overrides.

    Raises:
        FileNotFoundError: If an explicit config_path does not exist.
        ValueError: If the config file exists but fails Pydantic validation.
    """
    path = _find_config(config_path)
    raw: dict = {}

    if path is not None:
        data = path.read_bytes()
        raw = tomllib.loads(data.decode("utf-8"))

    _load_dotenv()
    raw = _env_override(raw)

    merged = _toml_to_nested(raw)

    try:
        cfg = X2VideoConfig(**merged)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    # Ensure work/ and final/ directories exist
    Path(cfg.work_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.final_dir).mkdir(parents=True, exist_ok=True)

    return cfg
