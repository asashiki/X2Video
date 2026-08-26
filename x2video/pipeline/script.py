"""Script stage: N-item digest narration (N=1 is a single-tweet video)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from x2video.config.schema import X2VideoConfig
from x2video.llm.client import create_llm_provider
from x2video.pipeline.io import load_picks, write_script
from x2video.pipeline.models import DigestScript, ScriptSegment
from x2video.pipeline.prompts import load_prompt
from x2video.pipeline.workdir import resolve_run_dir
from x2video.util import parse_json_payload, split_subtitles

SCRIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "outro": {"type": "string"},
        "title_suggestions": {"type": "array", "items": {"type": "string"}},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pick_id": {"type": "string"},
                    "narration": {"type": "string"},
                    "subtitle_lines": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["pick_id", "narration"],
            },
        },
    },
    "required": ["segments"],
}


def script_to_markdown(script: DigestScript) -> str:
    lines = ["# Digest script", ""]
    if script.title_suggestions:
        lines.append("## 标题备选")
        for t in script.title_suggestions:
            lines.append(f"- {t}")
        lines.append("")
    if script.hook:
        lines.extend(["## Hook", "", script.hook, ""])
    for i, seg in enumerate(script.segments, start=1):
        lines.extend(
            [
                f"## Segment {i} (`{seg.pick_id}`)",
                "",
                seg.narration,
                "",
            ]
        )
        if seg.subtitle_lines:
            lines.append("字幕:")
            for s in seg.subtitle_lines:
                lines.append(f"- {s}")
            lines.append("")
    if script.outro:
        lines.extend(["## Outro", "", script.outro, ""])
    if script.description:
        lines.extend(["## 简介", "", script.description, ""])
    if script.tags:
        lines.extend(["## 标签", "", " ".join(f"#{t.lstrip('#')}" for t in script.tags), ""])
    return "\n".join(lines).rstrip() + "\n"


def _coerce_script(raw: Any, pick_ids: list[str]) -> DigestScript:
    if isinstance(raw, list):
        raw = {"segments": raw}
    if not isinstance(raw, dict):
        raise ValueError("Script model did not return a JSON object.")
    segs_raw = raw.get("segments") or []
    if not isinstance(segs_raw, list) or not segs_raw:
        raise ValueError("Script model returned no segments.")
    segments: list[ScriptSegment] = []
    for i, item in enumerate(segs_raw):
        if not isinstance(item, dict):
            continue
        pid = str(item.get("pick_id") or (pick_ids[i] if i < len(pick_ids) else "")).strip()
        narration = str(item.get("narration") or item.get("text") or "").strip()
        if not narration:
            continue
        subs = item.get("subtitle_lines") or []
        if not isinstance(subs, list) or not subs:
            subs = split_subtitles(narration)
        else:
            subs = [str(s).strip() for s in subs if str(s).strip()]
        segments.append(ScriptSegment(pick_id=pid, narration=narration, subtitle_lines=subs))
    if not segments:
        raise ValueError("Script model returned empty narration.")
    titles = raw.get("title_suggestions") or raw.get("titles") or []
    tags = raw.get("tags") or []
    return DigestScript(
        hook=str(raw.get("hook") or "").strip(),
        outro=str(raw.get("outro") or "").strip(),
        segments=segments,
        title_suggestions=[str(t).strip() for t in titles if str(t).strip()][:3],
        description=str(raw.get("description") or "").strip(),
        tags=[str(t).lstrip("#").strip() for t in tags if str(t).strip()],
    )


async def run_script(
    cfg: X2VideoConfig,
    *,
    date: str | None = None,
    input_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    run_dir = resolve_run_dir(cfg.work_dir, date)
    src = input_path or (run_dir / "picks.json")
    if not src.exists():
        raise FileNotFoundError(f"Picks file not found: {src}. Run `x2video curate` first.")
    _meta, picks = load_picks(src)
    if not picks:
        raise ValueError("No picks to write a script for.")

    system = load_prompt("script-prompt.md")
    payload = {
        "n": len(picks),
        "picks": [
            {
                "id": p.id,
                "author_name": p.author_name,
                "author_username": p.author_username,
                "text": p.text,
                "translation": p.translation,
                "likes": p.likes,
                "url": p.url,
                "reason": p.reason,
            }
            for p in picks
        ],
    }
    import json

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Write a Chinese narration digest for N={len(picks)} pick(s). "
                "Return JSON only.\n\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
            ),
        },
    ]
    llm = create_llm_provider(cfg.llm)
    try:
        try:
            parsed = await llm.complete_structured(messages, SCRIPT_SCHEMA)
        except Exception:
            text = await llm.complete(messages)
            parsed = parse_json_payload(text)
    finally:
        await llm.close()

    script = _coerce_script(parsed, [p.id for p in picks])
    dest = output_path or (run_dir / "script.json")
    write_script(dest, script)
    md_path = dest.with_suffix(".md")
    md_path.write_text(script_to_markdown(script), encoding="utf-8")
    return {"input": src, "output": dest, "markdown": md_path, "script": script, "n": len(script.segments)}
