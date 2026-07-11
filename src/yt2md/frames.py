"""Extract frames at exact timestamps using the bundled ffmpeg."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .fetch import download_video


def parse_timestamp(ts: str) -> float:
    """Accept SS, MM:SS, or HH:MM:SS (fractions allowed in the last part)."""
    parts = ts.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"bad timestamp: {ts!r}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_frames(
    url: str,
    timestamps: list[float],
    outdir: Path,
    width: int = 1280,
    quality: int = 3,
    cookies_from_browser: str | None = None,
) -> list[Path]:
    """Download the video once (temp, video-only, ≤720p) and grab one JPEG per timestamp."""
    outdir.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_exe()
    written: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="yt2md-") as tmp:
        video = download_video(url, Path(tmp), cookies_from_browser=cookies_from_browser)
        for ts in timestamps:
            h, rem = divmod(int(ts), 3600)
            m, s = divmod(rem, 60)
            name = f"frame-{h:02d}-{m:02d}-{s:02d}.jpg" if h else f"frame-{m:02d}-{s:02d}.jpg"
            out = outdir / name
            cmd = [
                ffmpeg, "-y", "-loglevel", "error",
                "-ss", f"{ts:.3f}", "-i", str(video),
                "-frames:v", "1",
                "-vf", f"scale='min({width},iw)':-2",
                "-q:v", str(quality),
                str(out),
            ]
            subprocess.run(cmd, check=True)
            written.append(out)
    return written
