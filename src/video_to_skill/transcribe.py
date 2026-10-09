"""Transcript writing and speech-to-text fallback via faster-whisper."""

from __future__ import annotations

import json
from pathlib import Path

from ._time import fmt_ts


def write_transcript_files(outdir: Path, segments: list[dict]) -> None:
    (outdir / "transcript.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [f"[{fmt_ts(s['start'])} - {fmt_ts(s['end'])}] {s['text']}" for s in segments]
    (outdir / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")


def transcribe(
    audio_path: Path,
    outdir: Path,
    model_size: str,
    language: str | None,
    glossary: str,
    beam_size: int = 1,
) -> list[dict]:
    """Transcribe locally. ``glossary`` is an optional initial prompt that biases
    the model towards the spelling of domain-specific terms and proper nouns."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "Transcription needs faster-whisper. Install the optional extra:\n"
            '    pip install "video-to-skill[whisper]"'
        ) from exc

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, _info = model.transcribe(
        str(audio_path),
        language=language,
        initial_prompt=glossary or None,
        vad_filter=True,
        beam_size=beam_size,
        condition_on_previous_text=False,
    )
    segments = [
        {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments_iter
    ]
    write_transcript_files(outdir, segments)
    return segments
