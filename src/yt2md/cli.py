"""yt2md command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__
from .fetch import get_captions, get_info


def cmd_get(args: argparse.Namespace) -> int:
    info = get_info(args.url, args.cookies_from_browser)
    video_id = info["id"]
    outdir = Path(args.output) / video_id
    outdir.mkdir(parents=True, exist_ok=True)

    segments, source = None, None
    if not args.force_whisper:
        with tempfile.TemporaryDirectory(prefix="yt2md-") as tmp:
            captions = get_captions(
                args.url, info, Path(tmp),
                lang=args.lang, cookies_from_browser=args.cookies_from_browser,
            )
        if captions:
            segments, source = captions.segments, captions.source
            print(f"transcript source: {source}", file=sys.stderr)

    if segments is None:
        from .fetch import download_audio
        from .transcribe import transcribe

        print(f"no captions available — transcribing locally (whisper:{args.model})",
              file=sys.stderr)
        with tempfile.TemporaryDirectory(prefix="yt2md-") as tmp:
            audio = download_audio(args.url, Path(tmp),
                                   cookies_from_browser=args.cookies_from_browser)
            segments = transcribe(audio, model=args.model, lang=args.lang)
        source = f"whisper:{args.model}"

    if not segments:
        print("error: no transcript could be produced (no captions, no speech detected)",
              file=sys.stderr)
        return 1

    from .render import render_markdown, segments_json

    md_path = outdir / "transcript.md"
    md_path.write_text(render_markdown(info, segments, source), encoding="utf-8", newline="\n")
    seg_path = outdir / "segments.json"
    seg_path.write_text(segments_json(info, segments, source), encoding="utf-8", newline="\n")

    if args.json:
        print(json.dumps({
            "video_id": video_id,
            "title": info.get("title"),
            "transcript_source": source,
            "transcript": str(md_path),
            "segments": str(seg_path),
        }))
    else:
        print(md_path)
    return 0


def cmd_frames(args: argparse.Namespace) -> int:
    from .frames import extract_frames, parse_timestamp

    timestamps = [parse_timestamp(t) for t in args.timestamps.split(",") if t.strip()]
    if not timestamps:
        print("error: no timestamps given", file=sys.stderr)
        return 1

    outdir = Path(args.output) if args.output else None
    if outdir is None:
        info = get_info(args.url, args.cookies_from_browser)
        outdir = Path(info["id"]) / "frames"

    written = extract_frames(
        args.url, timestamps, outdir,
        width=args.width, quality=args.quality,
        cookies_from_browser=args.cookies_from_browser,
    )
    for path in written:
        print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yt2md",
        description="Turn YouTube videos and Shorts into timestamped markdown transcripts.",
    )
    parser.add_argument("--version", action="version", version=f"yt2md {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_get = sub.add_parser("get", help="fetch/produce a transcript as markdown")
    p_get.add_argument("url", help="YouTube video or Short URL")
    p_get.add_argument("-o", "--output", default=".",
                       help="parent output directory (default: current dir)")
    p_get.add_argument("--model", default="small",
                       choices=["tiny", "base", "small", "medium", "large-v3"],
                       help="whisper model for the fallback (default: small)")
    p_get.add_argument("--lang", default=None, help="language code, e.g. en (default: auto)")
    p_get.add_argument("--force-whisper", action="store_true",
                       help="skip YouTube captions and always transcribe locally")
    p_get.add_argument("--cookies-from-browser", default=None, metavar="BROWSER",
                       help="pass browser cookies to yt-dlp (chrome, firefox, edge, …)")
    p_get.add_argument("--json", action="store_true",
                       help="print result as JSON (for programmatic callers)")
    p_get.set_defaults(func=cmd_get)

    p_frames = sub.add_parser("frames", help="extract frames at exact timestamps")
    p_frames.add_argument("url", help="YouTube video or Short URL")
    p_frames.add_argument("-t", "--timestamps", required=True,
                          help="comma-separated: 42,1:15,01:02:03")
    p_frames.add_argument("-o", "--output", default=None,
                          help="output directory (default: <video-id>/frames)")
    p_frames.add_argument("--width", type=int, default=1280,
                          help="max frame width in px (default: 1280)")
    p_frames.add_argument("--quality", type=int, default=3,
                          help="JPEG quality, 2 best – 31 worst (default: 3)")
    p_frames.add_argument("--cookies-from-browser", default=None, metavar="BROWSER")
    p_frames.set_defaults(func=cmd_frames)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # surface a clean one-liner, not a stack trace
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
