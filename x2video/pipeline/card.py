"""Tweet Card rendering: HTML template → 1080×1920 PNG via headless Chromium."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from x2video.config.schema import X2VideoConfig
from x2video.pipeline.io import load_picks
from x2video.pipeline.models import Pick
from x2video.pipeline.workdir import resolve_run_dir
from x2video.util import format_count, format_tweet_time

_TEMPLATE_PATH = Path(__file__).with_name("card_template.html")
CARD_WIDTH = 1080
CARD_HEIGHT = 1920


def is_image_url(url: str) -> bool:
    u = url.lower().split("?")[0]
    if any(tok in u for tok in ("/amplify_video/", "/ext_tw_video/", "/tweet_video/")):
        return False
    if u.endswith((".mp4", ".m3u8", ".webm", ".mov", ".gif")):
        return False
    return bool(url.strip())


def _initials(name: str) -> str:
    text = (name or "?").strip() or "?"
    return html.escape(text[:1].upper())


def build_card_html(pick: Pick) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    images = [u for u in pick.media_urls if is_image_url(u)]
    media_html = ""
    if images:
        src = html.escape(images[0], quote=True)
        media_html = f'<div class="media"><img src="{src}" alt="" /></div>'

    verified = '<span class="verified" title="verified">✔</span>' if pick.author_verified else ""
    avatar = pick.author_avatar_url.strip()
    if avatar:
        avatar_html = (
            f'<img class="avatar-img" src="{html.escape(avatar, quote=True)}" alt="" />'
        )
    else:
        avatar_html = f'<div class="avatar-fallback">{_initials(pick.author_name)}</div>'

    body = "<br>".join(html.escape(line) for line in (pick.text or "").splitlines()) or "&nbsp;"
    translation = (
        "<br>".join(html.escape(line) for line in (pick.translation or "").splitlines())
        or "（暂无翻译）"
    )

    mapping = {
        "{{AUTHOR_NAME}}": html.escape(pick.author_name or pick.author_username or "Unknown"),
        "{{HANDLE}}": html.escape(pick.author_username or ""),
        "{{VERIFIED}}": verified,
        "{{TIME}}": html.escape(format_tweet_time(pick.created_at)),
        "{{AVATAR}}": avatar_html,
        "{{BODY}}": body,
        "{{TRANSLATION}}": translation,
        "{{MEDIA}}": media_html,
        "{{LIKES}}": format_count(pick.likes),
        "{{RETWEETS}}": format_count(pick.retweets),
        "{{REPLIES}}": format_count(pick.replies),
        "{{VIEWS}}": format_count(pick.views),
        "{{URL}}": html.escape(pick.url or ""),
    }
    out = template
    for key, value in mapping.items():
        out = out.replace(key, value)
    return out


def screenshot_html(html_doc: str, output: Path) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Card rendering requires Playwright. Install with: "
            'pip install playwright && playwright install chromium'
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:
            raise RuntimeError(
                "Chromium is not installed for Playwright. Run: playwright install chromium"
            ) from exc
        page = browser.new_page(
            viewport={"width": CARD_WIDTH, "height": CARD_HEIGHT},
            device_scale_factor=2,
        )
        page.set_content(html_doc, wait_until="domcontentloaded", timeout=20000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            page.wait_for_timeout(1200)
        page.screenshot(path=str(output), full_page=False, type="png")
        browser.close()
    return output


def render_pick_card(pick: Pick, output: Path) -> Path:
    return screenshot_html(build_card_html(pick), output)


def run_card(
    cfg: X2VideoConfig,
    *,
    date: str | None = None,
    input_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    run_dir = resolve_run_dir(cfg.work_dir, date)
    src = input_path or (run_dir / "picks.json")
    if not src.exists():
        raise FileNotFoundError(f"Picks file not found: {src}. Run `x2video curate` first.")
    _meta, picks = load_picks(src)
    dest = output_dir or (run_dir / "cards")
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pick in picks:
        path = dest / f"card_{pick.id}.png"
        html_path = dest / f"card_{pick.id}.html"
        doc = build_card_html(pick)
        html_path.write_text(doc, encoding="utf-8")
        screenshot_html(doc, path)
        written.append(path)
    return {"input": src, "output_dir": dest, "cards": written, "count": len(written)}
