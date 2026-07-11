"""Render transcript segments as timestamped markdown."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from .fetch import Segment

# Start a new paragraph on a speech gap longer than this (seconds)…
GAP_BREAK = 2.5
# …or once the current paragraph spans this much time.
MAX_BLOCK = 75.0


@dataclass
class Block:
    start: float
    text: str


def group_segments(segments: list[Segment]) -> list[Block]:
    blocks: list[Block] = []
    cur_start: float | None = None
    cur_end = 0.0
    cur_parts: list[str] = []
    for seg in segments:
        if cur_start is not None and (
            seg.start - cur_end > GAP_BREAK or seg.end - cur_start > MAX_BLOCK
        ):
            blocks.append(Block(start=cur_start, text=" ".join(cur_parts)))
            cur_start, cur_parts = None, []
        if cur_start is None:
            cur_start = seg.start
        cur_parts.append(seg.text)
        cur_end = seg.end
    if cur_start is not None and cur_parts:
        blocks.append(Block(start=cur_start, text=" ".join(cur_parts)))
    return blocks


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def ts_link(video_id: str, seconds: float) -> str:
    return f"https://youtu.be/{video_id}?t={int(seconds)}"


def _fmt_upload_date(raw: str | None) -> str | None:
    if raw and len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def render_markdown(info: dict, segments: list[Segment], source: str) -> str:
    video_id = info["id"]
    url = info.get("webpage_url") or f"https://youtu.be/{video_id}"
    duration = fmt_ts(info.get("duration") or 0)
    title = info.get("title") or video_id
    channel = info.get("channel") or info.get("uploader") or "unknown"

    front = [
        "---",
        f"title: {json.dumps(title)}",
        f"channel: {json.dumps(channel)}",
        f"url: {url}",
        f"video_id: {video_id}",
        f"upload_date: {_fmt_upload_date(info.get('upload_date'))}",
        f"duration: {duration}",
        f"transcript_source: {source}",
        f"generated: {date.today().isoformat()}",
        "tool: yt2md",
        "---",
    ]

    lines = front + [
        "",
        f"# {title}",
        "",
        f"> [Watch on YouTube]({url}) · {channel} · {duration}",
        "",
        "## Transcript",
        "",
    ]
    for block in group_segments(segments):
        link = ts_link(video_id, block.start)
        lines.append(f"**[{fmt_ts(block.start)}]({link})** {block.text}")
        lines.append("")
    return "\n".join(lines)


def segments_json(info: dict, segments: list[Segment], source: str) -> str:
    """Raw timing data for programmatic callers (e.g. LLM frame selection)."""
    return json.dumps(
        {
            "video_id": info["id"],
            "url": info.get("webpage_url") or f"https://youtu.be/{info['id']}",
            "title": info.get("title"),
            "transcript_source": source,
            "segments": [
                {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text}
                for s in segments
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
