"""Environment / dependency checks."""

from __future__ import annotations

import shutil

import typer

from x2video.auth.oauth import get_status
from x2video.config.loader import load_config
from x2video.util import discover_browser_executable

app = typer.Typer(help="Check local setup (auth, ffmpeg, Playwright, config)")


def _ok(label: str, detail: str) -> None:
    typer.secho(f"  OK   {label}: {detail}", fg=typer.colors.GREEN)


def _bad(label: str, detail: str) -> None:
    typer.secho(f"  FAIL {label}: {detail}", fg=typer.colors.RED)


@app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
) -> None:
    """Print a setup checklist. Exit 1 if anything required is missing."""
    failed = False
    typer.echo("x2video doctor")

    try:
        cfg = load_config()
        _ok("config", f"source={cfg.source.provider} tts={cfg.tts.provider} llm={cfg.llm.provider}")
    except Exception as exc:
        _bad("config", str(exc))
        failed = True
        cfg = None

    status = get_status()
    if status["logged_in"]:
        extra = "expired, will refresh" if status.get("expired") else "valid"
        _ok("auth", f"{status['path']} ({extra})")
    else:
        _bad("auth", "not logged in — run `x2video auth login` for provider=grok")
        if cfg is not None and cfg.source.provider == "grok":
            failed = True

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        _ok("ffmpeg", ffmpeg)
    else:
        _bad("ffmpeg", "ffmpeg/ffprobe not on PATH")
        failed = True

    exe = discover_browser_executable()
    if exe is not None:
        _ok("playwright", str(exe))
    else:
        _bad("playwright", "chromium missing — run `playwright install chromium`")
        failed = True

    try:
        import edge_tts  # noqa: F401

        _ok("tts", "edge-tts import ok")
    except Exception as exc:
        _bad("tts", str(exc))
        failed = True

    if failed:
        raise typer.Exit(code=1)
    typer.secho("All checks passed.", fg=typer.colors.GREEN)
