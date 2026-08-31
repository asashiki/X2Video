"""Render stage: TTS + FFmpeg 1080×1920 MP4 + Publish Kit."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from x2video.config.schema import X2VideoConfig
from x2video.pipeline.card import background_style, render_cover, render_opener
from x2video.pipeline.io import load_picks, load_script, write_json
from x2video.pipeline.models import DigestScript, Pick
from x2video.pipeline.workdir import resolve_run_dir, timestamp_stamp
from x2video.tts.client import create_tts_provider
from x2video.util import (
    ensure_date_lead,
    format_md_date,
    is_same_day_digest,
    split_subtitles,
    strip_date_lead,
)


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg/ffprobe not found on PATH.")


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    value = result.stdout.strip().splitlines()[0].strip()
    return max(float(value), 0.4)


def escape_subtitles_path(path: Path) -> str:
    posix = path.resolve().as_posix()
    if len(posix) >= 2 and posix[1] == ":":
        posix = posix[0] + "\\:" + posix[2:]
    return posix.replace("'", r"\'")


def wrap_ass_text(text: str, *, width: int = 13) -> str:
    """Insert ASS line breaks. Chinese has no spaces, so WrapStyle cannot wrap."""
    clean = (text or "").replace("\n", " ").replace("\\N", " ").strip()
    if len(clean) <= width:
        return clean
    lines: list[str] = []
    buf = ""
    for ch in clean:
        buf += ch
        long_enough = len(buf) >= width
        at_break = ch in "，,、。！？!?；; "
        if long_enough and at_break:
            lines.append(buf)
            buf = ""
        elif len(buf) >= width + 3:
            lines.append(buf)
            buf = ""
    if buf:
        lines.append(buf)
    return r"\N".join(lines) or clean


def _ass_header() -> str:
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 0\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Microsoft YaHei,46,&H00FFFFFF,&H000000FF,&H80101010,"
        "&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,96,96,260,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(lines: list[str], duration: float) -> str:
    if not lines:
        lines = [" "]
    total = sum(max(len(line), 1) for line in lines)
    header = _ass_header()
    events: list[str] = []
    cursor = 0.0
    cleaned = [wrap_ass_text(line.replace("\n", " ").replace("{", "(").replace("}", ")")) for line in lines]
    for i, text in enumerate(cleaned):
        share = max(len(text), 1) / total
        length = max(duration * share, 0.8)
        start = cursor
        end = min(duration, cursor + length)
        if end <= start:
            end = start + 0.4
        if i == len(cleaned) - 1:
            end = duration
        events.append(
            f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},"
            f"Default,,0,0,0,,{text}"
        )
        cursor = end
    return header + "\n".join(events) + "\n"


def compose_segment(
    *,
    card_png: Path,
    audio: Path,
    ass_path: Path,
    output: Path,
    duration: float,
) -> Path:
    # Still frame on purpose. A 1px-per-several-frames Ken Burns pan reads as
    # stuttering crawl at 30 fps because crop x/y are integer pixels.
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "format=yuv420p,"
        "fade=t=in:st=0:d=0.05,"
        f"subtitles='{escape_subtitles_path(ass_path)}'"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
        "-i",
        str(card_png),
        "-i",
        str(audio),
        "-t",
        f"{duration:.3f}",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")
    return output


def concat_files(parts: list[Path], output: Path, *, copy: bool = True) -> Path:
    if len(parts) == 1:
        shutil.copyfile(parts[0], output)
        return output
    listing = output.parent / f"{output.stem}.concat.txt"
    listing.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing)]
    if copy:
        cmd += ["-c", "copy"]
    else:
        cmd += ["-c:a", "libmp3lame", "-q:a", "4"]
    cmd.append(str(output))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr[-2000:]}")
    return output


def concat_videos(parts: list[Path], output: Path) -> Path:
    return concat_files(parts, output, copy=True)


def build_ass_cues(cues: list[tuple[str, float, float]]) -> str:
    header = _ass_header()
    events: list[str] = []
    for text, start, end in cues:
        clean = wrap_ass_text(text.replace("\n", " ").replace("{", "(").replace("}", ")"))
        if end <= start:
            end = start + 0.3
        events.append(
            f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},"
            f"Default,,0,0,0,,{clean}"
        )
    return header + "\n".join(events) + "\n"


async def synthesize_aligned(
    tts: Any,
    text: str,
    folder: Path,
    stem: str,
) -> tuple[Path, list[tuple[str, float, float]], float]:
    """TTS each subtitle line separately so on-screen text matches the voice."""
    folder.mkdir(parents=True, exist_ok=True)
    lines = [ln for ln in split_subtitles(text) if ln.strip("。！？!?；;，,、. ")]
    if not lines:
        lines = [text.strip() or " "]
    parts: list[Path] = []
    cues: list[tuple[str, float, float]] = []
    cursor = 0.0
    for i, line in enumerate(lines):
        part = folder / f"{stem}_l{i:02d}.mp3"
        await tts.synthesize(line, part)
        duration = probe_duration(part)
        cues.append((line, cursor, cursor + duration))
        cursor += duration
        parts.append(part)
    audio = folder / f"{stem}.mp3"
    concat_files(parts, audio, copy=False)
    return audio, cues, cursor


def mix_bgm(video: Path, bgm: Path, output: Path, *, duration: float) -> Path:
    """Lay a quiet looping bed under the TTS mix."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-stream_loop",
        "-1",
        "-i",
        str(bgm),
        "-filter_complex",
        f"[1:a]volume=0.10,atrim=0:{duration:.3f},asetpts=PTS-STARTPTS[bg];"
        "[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]",
        "-map",
        "0:v",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"BGM mix failed:\n{result.stderr[-1500:]}")
    return output


def resolve_bgm(cfg: X2VideoConfig) -> Path | None:
    candidates = []
    if cfg.bgm_path:
        candidates.append(Path(cfg.bgm_path))
    candidates.append(Path("assets") / "bgm.mp3")
    for path in candidates:
        if path.exists() and path.stat().st_size > 1000:
            return path
    return None


def write_publish_md(
    path: Path,
    *,
    script: DigestScript,
    video: Path,
    cover: Path,
    picks: list[Pick] | None = None,
    qc: dict[str, Any] | None = None,
) -> Path:
    titles = script.title_suggestions or ["今日 AI 热帖速览"]
    while len(titles) < 3:
        titles.append(titles[0])
    tags = " ".join(f"#{t.lstrip('#')}" for t in (script.tags or ["AI", "科技", "热帖"]))
    body = script.description or "外网 AI/科技热帖速览，卡片解说。"
    lines = [
        "# Publish Kit",
        "",
        f"成片日期: {format_md_date()}",
        "",
        "## 标题（选一）",
        *[f"{i}. {t}" for i, t in enumerate(titles[:3], start=1)],
        "",
        "## 简介",
        "",
        body,
        "",
        "## 标签",
        "",
        tags,
        "",
        "## 条目",
        "",
    ]
    for i, pick in enumerate(picks or [], start=1):
        lines.append(
            f"{i}. {format_md_date(pick.created_at)} @{pick.author_username}  {pick.url}"
        )
    lines += [
        "",
        "## 文件",
        "",
        f"- 视频 9:16: `{video.name}`",
        f"- 封面 3:4: `{cover.name}`（抖音信息流用这张，底 25% 已被预留）",
        "",
        "## Gate 2 审片",
        "",
        "- [ ] 日期是今天/昨天/本周",
        "- [ ] 口播和字幕对齐",
        "- [ ] 封面缩略图能读出标题",
        "- [ ] 没有过期或跑题条目",
        "",
        "上传由人工完成。",
        "",
    ]
    if qc:
        if qc.get("warnings"):
            lines += ["## QC 警告", ""]
            lines += [f"- {w}" for w in qc["warnings"]]
            lines.append("")
        if qc.get("errors"):
            lines += ["## QC 错误", ""]
            lines += [f"- {e}" for e in qc["errors"]]
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _cover_headline(script: DigestScript, first: Pick | None) -> str:
    """Short Chinese line for the 3:4 feed cover. Prefer 译文, never a chopped English title."""
    import re

    source = ""
    if first and first.translation:
        source = first.translation
    elif script.title_suggestions:
        source = script.title_suggestions[0]
    clauses = [p.strip() for p in re.split(r"[，。！？]", source or "") if p.strip()]
    for clause in clauses:
        cjk = sum(1 for ch in clause if "\u4e00" <= ch <= "\u9fff")
        if cjk >= 6:
            return clause[:14]
    if clauses:
        return clauses[0][:14]
    return "外网热帖"


def _card_for_pick(cards_dir: Path, pick: Pick) -> Path:
    direct = cards_dir / f"card_{pick.id}.png"
    if direct.exists():
        return direct
    pngs = sorted(cards_dir.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"No card PNGs in {cards_dir}")
    return pngs[0]


async def run_render(
    cfg: X2VideoConfig,
    *,
    date: str | None = None,
    script_path: Path | None = None,
    cards_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    ensure_ffmpeg()
    run_dir = resolve_run_dir(cfg.work_dir, date)
    src = script_path or (run_dir / "script.json")
    if not src.exists():
        raise FileNotFoundError(f"Script not found: {src}. Run `x2video script` first.")
    cards = cards_dir or (run_dir / "cards")
    script = load_script(src)
    _meta, picks = load_picks(run_dir / "picks.json") if (run_dir / "picks.json").exists() else ({}, [])
    pick_by_id = {p.id: p for p in picks}

    kit_dir = output_dir or (Path(cfg.final_dir) / timestamp_stamp())
    kit_dir.mkdir(parents=True, exist_ok=True)
    work_audio = run_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)
    work_clips = run_dir / "clips"
    work_clips.mkdir(parents=True, exist_ok=True)

    tts = create_tts_provider(cfg.tts)
    spoken = script.spoken_texts()
    if not spoken:
        raise ValueError("Script has no spoken text.")

    clips: list[Path] = []
    try:
        opener = script.opener_text()
        same_day = is_same_day_digest(picks)
        opener_date = (
            format_md_date(picks[0].created_at) if same_day and picks else "近几日"
        )
        if opener:
            opener_png = cards / "opener.png"
            opener_spoken = strip_date_lead(opener)
            await asyncio.to_thread(
                render_opener,
                opener_spoken,
                opener_png,
                count=len(script.segments),
                date_label=opener_date,
            )
            audio, cues, duration = await synthesize_aligned(
                tts, opener_spoken, work_audio, "opener"
            )
            ass_path = work_clips / "opener.ass"
            ass_path.write_text(build_ass_cues(cues), encoding="utf-8-sig")
            opener_clip = work_clips / "opener.mp4"
            compose_segment(
                card_png=opener_png,
                audio=audio,
                ass_path=ass_path,
                output=opener_clip,
                duration=duration,
            )
            clips.append(opener_clip)

        for i, (seg, spoken_text) in enumerate(zip(script.segments, spoken)):
            pick = pick_by_id.get(seg.pick_id) or (picks[i] if i < len(picks) else None)
            if pick is None:
                pngs = sorted(cards.glob("*.png"))
                if not pngs:
                    raise FileNotFoundError(f"No cards for segment {seg.pick_id}")
                card_png = pngs[min(i, len(pngs) - 1)]
            else:
                card_png = _card_for_pick(cards, pick)
            spoken_text = strip_date_lead(spoken_text)
            if not same_day:
                item_date = format_md_date(pick.created_at if pick else "")
                spoken_text = ensure_date_lead(spoken_text, item_date)
            audio, cues, duration = await synthesize_aligned(
                tts, spoken_text, work_audio, f"seg_{i:02d}"
            )
            ass_path = work_clips / f"seg_{i:02d}.ass"
            ass_path.write_text(build_ass_cues(cues), encoding="utf-8-sig")
            clip = work_clips / f"seg_{i:02d}.mp4"
            compose_segment(
                card_png=card_png,
                audio=audio,
                ass_path=ass_path,
                output=clip,
                duration=duration,
            )
            clips.append(clip)
    finally:
        if hasattr(tts, "close"):
            close = getattr(tts, "close")
            if callable(close):
                maybe = close()
                if hasattr(maybe, "__await__"):
                    await maybe

    video = kit_dir / "video.mp4"
    if len(clips) == 1:
        shutil.copyfile(clips[0], video)
    else:
        concat_videos(clips, video)

    bgm = resolve_bgm(cfg)
    if bgm is not None:
        mixed = kit_dir / "video.bgm.mp4"
        mix_bgm(video, bgm, mixed, duration=probe_duration(video))
        video.unlink(missing_ok=True)
        shutil.move(str(mixed), str(video))

    cover = kit_dir / "cover.png"
    first = picks[0] if picks else None
    title = _cover_headline(script, first)
    sub = f"{len(picks)} 条热帖" if picks else "热帖速览"
    bg_style = background_style(first) if first else "background:#0b0d10"
    await asyncio.to_thread(
        render_cover,
        cover,
        title=title,
        date_label=(
            format_md_date(picks[0].created_at)
            if is_same_day_digest(picks) and picks
            else "近几日"
        ),
        sub=sub,
        bg_style=bg_style,
    )

    from x2video.pipeline.qc import inspect_kit

    qc = inspect_kit(video=video, cover=cover, pick_count=len(picks))
    write_json(kit_dir / "qc.json", qc)
    publish_md = write_publish_md(
        kit_dir / "publish.md",
        script=script,
        video=video,
        cover=cover,
        picks=picks,
        qc=qc,
    )
    pointer = {
        "video": str(video),
        "cover": str(cover),
        "publish_md": str(publish_md),
        "kit_dir": str(kit_dir),
        "qc": qc,
    }
    write_json(run_dir / "publish_kit.json", pointer)
    if not qc["ok"]:
        raise RuntimeError("QC failed: " + "; ".join(qc["errors"]))
    return pointer
