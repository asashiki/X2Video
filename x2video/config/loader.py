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

from x2video.config.schema import X2VideoConfig


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


def _env_override(base: dict, prefix: str = "X2VIDEO_") -> dict:
    """Apply X2VIDEO_* env var overrides to the flat config dict.

    Maps env vars to nested config keys:
        X2VIDEO_LLM_API_KEY -> llm.api_key
        X2VIDEO_TTS_API_KEY -> tts.api_key
        X2VIDEO_WORK_DIR    -> work_dir
    """
    result = dict(base)
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        # X2VIDEO_LLM_API_KEY -> llm.api_key
        config_key = key[len(prefix):].lower()
        parts = config_key.split("_", 1)
        section = parts[0]
        if len(parts) == 2:
            field = parts[1]
            if section not in result:
                result[section] = {}
            if isinstance(result[section], dict):
                result[section][field] = value
        elif len(parts) == 1:
            result[section] = value
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

    cfg = X2VideoConfig(**merged)

    # Ensure work/ and final/ directories exist
    Path(cfg.work_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.final_dir).mkdir(parents=True, exist_ok=True)

    return cfg
