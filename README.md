# yt2md

Turn YouTube videos and Shorts into clean, **timestamped markdown transcripts** —
with on-demand **frame extraction** at exact timestamps for the moments that
need to be *seen*, not just read.

Free and fully local: if YouTube has captions, they're used; if not (most
Shorts), the audio is transcribed on your CPU with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). No API keys, no
cost, no cloud.

## Why

Video is where ideas arrive; text is where they get organized. But:

- Shorts and many videos have **no captions** — there's nothing to copy out.
- Transcripts alone lose visual information. Exercise form, technique,
  on-screen diagrams — sometimes you need the *picture*, or a link to the
  exact second in the video.

yt2md gives you both: every paragraph in the transcript is anchored to a
clickable timestamp (`https://youtu.be/ID?t=83`), and any timestamp can be
turned into a JPEG frame.

Inspired by [obra/Youtube2Webpage](https://github.com/obra/Youtube2Webpage),
which pairs captions with screenshots — yt2md adds the transcription fallback
for caption-less videos and outputs markdown for note systems (Obsidian,
Logseq, plain files) instead of a webpage.

## Install

```sh
pip install git+https://github.com/rishi222k/yt2md
```

Python ≥ 3.10. Everything else (yt-dlp, faster-whisper, a bundled ffmpeg) is
installed automatically — no system packages needed. The Whisper model
(~460 MB for `small`) downloads on first fallback use.

## Usage

### Get a transcript

```sh
yt2md get https://www.youtube.com/watch?v=VIDEO_ID
yt2md get https://www.youtube.com/shorts/SHORT_ID -o notes/
```

Writes `<video-id>/transcript.md` — YAML frontmatter (title, channel, URL,
date, duration, transcript source) plus the transcript in readable paragraphs,
each with a timestamp link:

```markdown
**[01:23](https://youtu.be/VIDEO_ID?t=83)** Keep your elbows tucked at
roughly forty-five degrees as you lower the bar…
```

Also writes `segments.json` with raw per-segment timing for programmatic use.

Options: `--model tiny|base|small|medium|large-v3` (whisper fallback model,
default `small`) · `--lang en` · `--force-whisper` (skip captions — useful
when auto-captions are garbage) · `--cookies-from-browser chrome` (if YouTube
bot-checks you) · `--json` (machine-readable result).

### Extract frames at exact timestamps

```sh
yt2md frames https://www.youtube.com/watch?v=VIDEO_ID -t 42,1:15,2:03
```

Downloads the video once to a temp file (deleted afterwards), writes one
compressed JPEG per timestamp (`frames/frame-01-15.jpg`, max width 1280 by
default).

### The intended workflow (agent- or human-driven)

yt2md deliberately does **not** decide which moments deserve a picture — that
judgment belongs to whoever (or whatever) reads the transcript:

1. `yt2md get URL` → read the transcript.
2. Judge which paragraphs genuinely benefit from a visual — an exercise demo,
   a diagram, a before/after. Could be zero moments, could be fifteen.
3. `yt2md frames URL -t <those timestamps>` → embed the images next to those
   paragraphs in your note.

This works beautifully driven by an LLM agent (e.g. Claude Code): the agent
reads `transcript.md`, picks the timestamps, runs `frames`, and assembles the
final note — with each image placed exactly where the text needs it, and a
timestamp link for everything else.

## Notes & limitations

- **Content stays yours.** The tool is open source; the transcripts and
  frames it produces are derived from other people's videos — keep them in
  your private notes, don't republish them.
- **Caption preference:** manual subtitles → auto-generated captions → local
  Whisper. Whisper output on music-heavy or heavily-edited clips can be
  imperfect (VAD filtering is on by default to reduce hallucination).
- **YouTube rate limiting:** occasionally YouTube challenges downloads
  ("confirm you're not a bot"), more so on datacenter IPs. Running locally on
  a residential connection is usually fine; `--cookies-from-browser` handles
  the stubborn cases.
- Frame extraction fetches a video-only stream at ≤720p for reliability; the
  temp file is deleted after the frames are written.

## License

MIT
