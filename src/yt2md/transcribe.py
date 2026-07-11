"""Local Whisper transcription via faster-whisper (CPU, free)."""

from __future__ import annotations

from pathlib import Path

from .fetch import Segment


def transcribe(audio_path: Path, model: str = "small", lang: str | None = None) -> list[Segment]:
    """Transcribe an audio file locally. Model weights download on first use."""
    from faster_whisper import WhisperModel  # deferred: heavy import

    whisper = WhisperModel(model, device="cpu", compute_type="int8")
    segments, _info = whisper.transcribe(
        str(audio_path),
        language=lang,
        vad_filter=True,  # suppress hallucination on silence/music
        beam_size=5,
    )
    return [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments if s.text.strip()]
