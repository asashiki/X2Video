import subprocess
from pathlib import Path

from x2video.tools.content import _demo_fonts, _probe_media_checks


def test_demo_fonts_resolve_on_this_machine() -> None:
    regular, bold = _demo_fonts()
    assert "fontfile" not in regular
    assert regular.startswith("'")
    assert bold.startswith("'")
    assert ":" not in regular.replace(r"\:", "")


def test_ffmpeg_detects_black_frame_and_silence(tmp_path: Path) -> None:
    video = tmp_path / "black-silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:s=320x480:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ],
        check=True,
        capture_output=True,
    )

    checks = _probe_media_checks(video)

    assert checks["black_segments"]
    assert checks["silence_segments"]


def test_ffmpeg_reports_loud_audio(tmp_path: Path) -> None:
    video = tmp_path / "loud.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=blue:s=320x480:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=1",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ],
        check=True,
        capture_output=True,
    )

    checks = _probe_media_checks(video)

    assert checks["mean_volume_db"] > -30
