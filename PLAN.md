# yt2md — Planning Document

*Status: v0.1 in development · 2026-07-11*

## 1. Problem

Ideas arrive as YouTube videos and Shorts. Getting them into a text-based
knowledge system (an Obsidian vault, a notes inbox, a research pipeline) is
painful because:

- Many videos — especially Shorts — have **no caption track**, so there is
  nothing to copy out.
- Even when captions exist, turning them into a clean, readable, *linkable*
  markdown note is manual work.
- Text alone loses critical visual information. Exercise form, physical
  technique, diagrams shown on screen — a transcript can't carry these. The
  reader needs to *see* the moment, either as an inline image or by jumping
  to the exact second in the video.

[obra/Youtube2Webpage](https://github.com/obra/Youtube2Webpage) proved the
value of pairing captions with screenshots, but it only works when YouTube
captions already exist, outputs a standalone HTML page rather than markdown,
and grabs frames blindly rather than where they add meaning.

## 2. What yt2md does

A free, local, open-source CLI that turns any YouTube video or Short into a
markdown note:

1. **Caption-first transcription.** If YouTube has a caption track (manual
   preferred, auto-generated accepted), fetch it — seconds, no download.
2. **Whisper fallback.** If no captions exist, download the audio only and
   transcribe locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
   (CPU, free, ~1–2 min for a 10-minute video with the `small` model).
3. **Timestamped markdown.** The transcript is grouped into readable
   paragraphs, each anchored by a clickable timestamp link
   (`https://youtu.be/ID?t=83`) that jumps to that exact moment in the video.
4. **On-demand frame extraction.** A separate command extracts video frames
   at caller-specified timestamps as compressed JPEGs. The tool does **not**
   decide which moments matter — see §3.

### Non-goals

- No HTML page generation (markdown is the product).
- No video archiving — the video/audio download is a temp file, deleted after use.
- No built-in AI frame selection or summarization (deliberate — see §3).
- Outputs are for personal/private use; the tool is open source, the
  transcripts and frames it produces are not yours to republish.

## 3. Architecture: deterministic tool, intelligent caller

The key design decision. Frame selection is a judgment call ("these 7 moments
show exercise form; that Short needs 0 frames") that varies per video. Baking
an LLM into the tool would add API keys, cost, and opinions. Instead:

```
┌─────────────────────────────────────────────────────┐
│ Intelligent caller (LLM agent, or a human)          │
│  1. yt2md get URL          → transcript.md          │
│  2. read transcript, judge which moments (0–15)     │
│     genuinely benefit from a visual                 │
│  3. yt2md frames URL -t 0:42,1:15,…  → JPEGs        │
│  4. weave images + timestamp links into final note  │
└─────────────────────────────────────────────────────┘
            │ calls                    │ calls
            ▼                          ▼
   ┌─────────────────┐        ┌─────────────────┐
   │  yt2md get      │        │  yt2md frames   │
   │  captions →     │        │  yt-dlp temp DL │
   │  else whisper   │        │  → ffmpeg seek  │
   └─────────────────┘        └─────────────────┘
```

The tool is fully usable standalone (transcript only, or hand-picked
timestamps). Paired with an agent like Claude Code, the agent reads the
transcript and decides how many frames a video deserves — two instances for
one video, fifteen for another, zero for a talking-head clip.

## 4. CLI surface

```
yt2md get <url> [-o DIR] [--model tiny|base|small|medium] [--lang xx]
        [--force-whisper] [--cookies-from-browser BROWSER] [--json]
```
Writes `DIR/<video-id>/transcript.md` and `segments.json` (raw timing data
for programmatic callers). Caption preference: manual subs → auto subs →
whisper. `--force-whisper` skips captions (useful when auto-captions are
garbage). `--cookies-from-browser chrome` passes through to yt-dlp for
bot-check fallback.

```
yt2md frames <url> -t <ts,ts,…> [-o DIR] [--width 1280] [--quality 3]
```
Timestamps accept `SS`, `MM:SS`, or `HH:MM:SS`. Downloads the video once to a
temp file (≤720p — reliable, avoids stream-URL 403s), extracts one JPEG per
timestamp named `frame-MM-SS.jpg`, deletes the temp video.

## 5. Implementation

- **Language:** Python ≥3.10, packaged with `pyproject.toml`, entry point
  `yt2md`. `pip install yt2md` (or `pipx install`) is the whole setup.
- **Dependencies (all pip, no system installs):**
  - `yt-dlp` — metadata, captions, audio/video download
  - `faster-whisper` — local CTranslate2 Whisper, VAD-filtered to suppress
    hallucination on silence/music; models auto-download on first use
  - `imageio-ffmpeg` — bundles an ffmpeg binary for frame extraction, so
    users never install ffmpeg themselves
- **Modules:** `cli.py` (argparse), `fetch.py` (yt-dlp wrapper: metadata,
  captions, media download), `transcribe.py` (faster-whisper), `render.py`
  (segments → markdown), `frames.py` (ffmpeg extraction).
- **Paragraphing:** merge caption/whisper segments into blocks broken on
  speech gaps > 2.5 s or block length > ~75 s, each block prefixed with a
  linked timestamp.
- **Markdown frontmatter:** title, channel, url, video id, upload date,
  duration, transcript source (`captions:manual` / `captions:auto` /
  `whisper:<model>`), generation date.

## 6. Known limitations & mitigations

| Risk | Mitigation |
|---|---|
| YouTube bot-detection blocks yt-dlp | Runs on residential IP; `--cookies-from-browser` escape hatch; keep yt-dlp updated |
| Whisper hallucinates on music/silence | VAD filter on by default; caption-first means whisper only runs when needed |
| Frames at a timestamp miss the exact demo moment | Every paragraph keeps a timestamped link — the frame gets you close, the link gets you exact |
| Images bloat a git-tracked vault | Selection keeps it to 0–15 compressed frames per video; revisit (store outside git / git-lfs) if repo growth becomes a problem |
| Long videos are slow to whisper on CPU | Caption-first covers most long videos (they usually have auto-captions); whisper mostly handles Shorts, which are… short |

## 7. Roadmap

- **v0.1 (now):** `get` + `frames`, tested on a captioned video and a
  caption-less Short, published to GitHub.
- **v0.2:** LifeOS integration layer (private, in the vault repo — not part
  of this repo): an ingest skill where the agent runs `get`, selects
  moments, runs `frames`, and files the note + images into the vault inbox.
- **Later, if wanted:** heuristic frame mode (scene detection) for non-agent
  users; playlist/batch mode; PyPI release.
