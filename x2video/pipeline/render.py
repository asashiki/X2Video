"""Render stage: TTS + FFmpeg 1080×1920 MP4 + Publish Kit."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from x2video.config.schema import X2VideoConfig
from x2video.pipeline.io import load_picks, load_script, write_json
from x2video.pipeline.models import DigestScript, Pick
from x2video.pipeline.workdir import resolve_run_dir, timestamp_stamp
from x2video.tts.client import create_tts_provider
from x2video.util import split_subtitles


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
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 2\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Microsoft YaHei,52,&H00FFFFFF,&H000000FF,&H80101010,"
        "&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,70,70,96,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events: list[str] = []
    cursor = 0.0
    cleaned = [line.replace("\n", " ").replace("{", "(").replace("}", ")") for line in lines]
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
    fade_out = max(duration - 0.35, 0.1)
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x07080c,"
        "format=yuv420p,"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.3,"
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


def concat_videos(parts: list[Path], output: Path) -> Path:
    listing = output.parent / "concat.txt"
    listing.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
        "-c",
        "copy",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr[-2000:]}")
    return output


def write_publish_md(
    path: Path,
    *,
    script: DigestScript,
    video: Path,
    cover: Path,
) -> Path:
    titles = script.title_suggestions or ["今日 AI 热帖速览"]
    while len(titles) < 3:
        titles.append(titles[0])
    tags = " ".join(f"#{t.lstrip('#')}" for t in (script.tags or ["AI", "科技", "热帖"]))
    body = script.description or "外网 AI/科技热帖速览，卡片解说。"
    text = "\n".join(
        [
            "# Publish Kit",
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
            "## 文件",
            "",
            f"- 视频: `{video.name}`",
            f"- 封面: `{cover.name}`",
            "",
            "上传由人工完成（Gate 2）。",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")
    return path


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

    audio_paths = await tts.synthesize_batch(spoken, work_audio)
    if hasattr(tts, "close"):
        close = getattr(tts, "close")
        if callable(close):
            maybe = close()
            if hasattr(maybe, "__await__"):
                await maybe

    clips: list[Path] = []
    for i, (seg, audio, spoken_text) in enumerate(zip(script.segments, audio_paths, spoken)):
        pick = pick_by_id.get(seg.pick_id) or (picks[i] if i < len(picks) else None)
        if pick is None:
            pngs = sorted(cards.glob("*.png"))
            if not pngs:
                raise FileNotFoundError(f"No cards for segment {seg.pick_id}")
            card_png = pngs[min(i, len(pngs) - 1)]
        else:
            card_png = _card_for_pick(cards, pick)
        duration = probe_duration(audio)
        lines = seg.subtitle_lines or split_subtitles(spoken_text)
        ass_path = work_clips / f"seg_{i:02d}.ass"
        ass_path.write_text(build_ass(lines, duration), encoding="utf-8-sig")
        clip = work_clips / f"seg_{i:02d}.mp4"
        compose_segment(
            card_png=card_png,
            audio=audio,
            ass_path=ass_path,
            output=clip,
            duration=duration,
        )
        clips.append(clip)

    video = kit_dir / "video.mp4"
    if len(clips) == 1:
        shutil.copyfile(clips[0], video)
    else:
        concat_videos(clips, video)

    cover = kit_dir / "cover.png"
    first_card = sorted(cards.glob("*.png"))
    if first_card:
        shutil.copyfile(first_card[0], cover)
    else:
        thumb = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video), "-frames:v", "1", str(cover)],
            capture_output=True,
            text=True,
        )
        if thumb.returncode != 0:
            raise RuntimeError("Could not write cover image.")

    publish_md = write_publish_md(
        kit_dir / "publish.md",
        script=script,
        video=video,
        cover=cover,
    )
    pointer = {
        "video": str(video),
        "cover": str(cover),
        "publish_md": str(publish_md),
        "kit_dir": str(kit_dir),
    }
    write_json(run_dir / "publish_kit.json", pointer)
    return pointer
