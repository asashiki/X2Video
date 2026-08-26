"""Load living prompt documents from ./prompts or the packaged copies."""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    """Load a prompt markdown file.

    Search order:
    1. ``./prompts/<filename>`` (repo living docs, overridable)
    2. packaged ``x2video/prompts/<filename>``
    """
    candidates = (
        Path.cwd() / "prompts" / filename,
        _PACKAGE_DIR / filename,
    )
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    names = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Prompt '{filename}' not found. Looked in: {names}")
