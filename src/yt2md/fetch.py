"""yt-dlp wrappers: metadata, caption tracks, and media downloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


@dataclass
class Segment:
    start: float  # seconds
    end: float
    text: str


@dataclass
class CaptionResult:
    segments: list[Segment]
    source: str  # "captions:manual" or "captions:auto"


def _base_opts(cookies_from_browser: str | None) -> dict:
    opts: dict = {"quiet": True, "no_warnings": True, "noprogress": True}
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    return opts


def get_info(url: str, cookies_from_browser: str | None = None) -> dict:
    """Fetch video metadata without downloading anything."""
    with yt_dlp.YoutubeDL(_base_opts(cookies_from_browser)) as ydl:
        return ydl.extract_info(url, download=False)


def _pick_lang(available: dict, preferred: str | None, video_lang: str | None) -> str | None:
    """Pick the best language key from a subtitle dict.

    Prefers, in order: explicit request, the video's own language, English.
    '-orig' variants win over translated auto-captions of the same language.
    """
    if not available:
        return None
    candidates = [c for c in (preferred, video_lang, "en") if c]
    for cand in candidates:
        for suffix in ("-orig", ""):
            exact = f"{cand}{suffix}"
            if exact in available:
                return exact
        for key in available:
            if key.startswith(cand):
                return key
    return None


def _parse_json3(path: Path) -> list[Segment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments: list[Segment] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        start = event.get("tStartMs", 0) / 1000.0
        end = start + event.get("dDurationMs", 0) / 1000.0
        segments.append(Segment(start=start, end=end, text=text))
    return segments


def get_captions(
    url: str,
    info: dict,
    workdir: Path,
    lang: str | None = None,
    cookies_from_browser: str | None = None,
) -> CaptionResult | None:
    """Download and parse a caption track, or return None if the video has none."""
    video_lang = info.get("language")
    manual_lang = _pick_lang(info.get("subtitles") or {}, lang, video_lang)
    auto_lang = None if manual_lang else _pick_lang(info.get("automatic_captions") or {}, lang, video_lang)
    chosen = manual_lang or auto_lang
    if not chosen:
        return None

    opts = _base_opts(cookies_from_browser) | {
        "skip_download": True,
        "writesubtitles": manual_lang is not None,
        "writeautomaticsub": auto_lang is not None,
        "subtitleslangs": [chosen],
        "subtitlesformat": "json3",
        "outtmpl": str(workdir / "%(id)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    sub_file = workdir / f"{info['id']}.{chosen}.json3"
    if not sub_file.exists():
        return None
    segments = _parse_json3(sub_file)
    if not segments:
        return None
    source = "captions:manual" if manual_lang else "captions:auto"
    return CaptionResult(segments=segments, source=source)


def download_audio(url: str, workdir: Path, cookies_from_browser: str | None = None) -> Path:
    """Download the smallest useful audio-only stream for transcription."""
    opts = _base_opts(cookies_from_browser) | {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(workdir / "audio.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    matches = list(workdir.glob("audio.*"))
    if not matches:
        raise RuntimeError("audio download failed: no file produced")
    return matches[0]


def download_video(url: str, workdir: Path, max_height: int = 720,
                   cookies_from_browser: str | None = None) -> Path:
    """Download a video-only stream (no merge needed) for frame extraction."""
    fmt = (
        f"bestvideo[height<={max_height}][ext=mp4]/"
        f"bestvideo[height<={max_height}]/"
        f"best[height<={max_height}]/best"
    )
    opts = _base_opts(cookies_from_browser) | {
        "format": fmt,
        "outtmpl": str(workdir / "video.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    matches = list(workdir.glob("video.*"))
    if not matches:
        raise RuntimeError("video download failed: no file produced")
    return matches[0]
