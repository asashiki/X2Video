"""Persistent storage for Grok OAuth credentials."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

# Public Grok CLI OAuth client — same client_id used by Grok Build / hermes / litellm.
DEFAULT_AUTH_DIR = Path.home() / ".config" / "x2video"
DEFAULT_AUTH_FILE = "grok_auth.json"


def auth_file_path(auth_dir: Path | None = None, filename: str = DEFAULT_AUTH_FILE) -> Path:
    """Return the path to the credentials file."""
    base = auth_dir if auth_dir is not None else DEFAULT_AUTH_DIR
    return base / filename


def read_auth(path: Path | None = None) -> dict[str, Any] | None:
    """Load credentials JSON, or None if missing/invalid."""
    target = path or auth_file_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None


def write_auth(data: dict[str, Any], path: Path | None = None) -> Path:
    """Atomically write credentials with restrictive permissions."""
    target = path or auth_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(target.parent, 0o700)
    except OSError:
        pass

    # Atomic replace via temp file in the same directory
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.{uuid.uuid4().hex}.",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, target)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def delete_auth(path: Path | None = None) -> bool:
    """Delete stored credentials. Returns True if a file was removed."""
    target = path or auth_file_path()
    if not target.exists():
        return False
    target.unlink()
    return True
