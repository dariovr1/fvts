"""Human/agent-readable manifest describing a capture run."""

from __future__ import annotations

from pathlib import Path

from ._time import fmt_ts, fmt_ts_short

TITLE = "VIDEO-TO-SKILL - video analysis package for a multimodal agent"


def _chapters_block(chapters: list[dict]) -> list[str]:
    lines = ["", "CHAPTERS (author-provided)", "-" * 70]
    for chapter in chapters:
        title = chapter.get("title") or ""
        lines.append(f"{fmt_ts_short(chapter.get('start_time') or 0)}  {title}".rstrip())
    return lines


def _heatmap_block(heatmap: list[dict]) -> list[str]:
    top = sorted((h for h in heatmap if h.get("value")), key=lambda h: h["value"], reverse=True)[:5]
    if not top:
        return []
    vmax = max(h["value"] for h in top)
    scale = 100.0 if vmax <= 1.0001 else 1.0
    lines = ["", "MOST REPLAYED MOMENTS (YouTube heatmap, top 5)", "-" * 70]
    for h in sorted(top, key=lambda h: h.get("start_time") or 0):
        start = fmt_ts_short(h.get("start_time") or 0)
        end = fmt_ts_short(h.get("end_time") or 0)
        lines.append(f"{start}-{end}  ({h['value'] * scale:.0f}%)")
    return lines


def _frames_block(frames: list[dict], grid_files: list[str]) -> list[str]:
    return [
        f"- frames/           {len(frames)} representative frames (deduplicated) as frame_NNN.jpg",
        "- frames.json       frame list with timestamp_sec/timestamp",
        f"- grids/            {len(grid_files)} contact sheets with a timestamp on every cell",
        "",
        "HOW TO 'WATCH' THE VIDEO (instructions for the agent)",
        "-" * 70,
        "1. Read transcript.txt for the spoken track.",
        "2. Open grid_000.jpg, grid_001.jpg, ... in grids/ in order: each cell is",
        "   labelled '#index @ timestamp' and corresponds to an instant in the video.",
        "   Reading them in sequence builds a complete visual understanding.",
        "3. For a finer detail at a precise instant, open the single file in frames/",
        "   (frame_NNN.jpg, same index/timestamp as frames.json).",
        "4. Always cross-check what is said (transcript) against what is shown",
        "   (grids): the intent often lives in the contrast between the two.",
        "5. Cite the relevant timestamps when you report back (e.g. 'at 00:12 ...').",
    ]


def _audio_only_block() -> list[str]:
    return [
        "",
        "AUDIO-ONLY MODE (instructions for the agent)",
        "-" * 70,
        "No frames were extracted: this package carries no visual information,",
        "only the spoken track.",
        "1. Read transcript.txt for the spoken track.",
        "2. Answer from the audio alone, citing timestamps. If a question needs",
        "   something visual, say so and offer to re-run with --mode full/stream.",
    ]


def write_manifest(
    outdir: Path,
    info: dict,
    duration: float,
    segments: list[dict],
    frames: list[dict],
    grid_files: list[str],
    source_url: str,
    transcript_source: str,
    mode_note: str,
) -> None:
    n_words = sum(len(s["text"].split()) for s in segments)
    lines = [
        TITLE,
        "=" * 70,
        f"Title:        {info.get('title')}",
        f"Channel:      {info.get('uploader')}",
        f"Duration:     {fmt_ts(duration)}",
        f"Source URL:   {source_url}",
        f"Folder:       {outdir}",
        f"Transcript:   {transcript_source}",
        f"Mode:         {mode_note}",
        "",
        "CONTENTS",
        "-" * 70,
        "- source.mp4        original video (removed at the end of the run; absent in stream/audio mode)",
        "- audio.wav         extracted audio (16 kHz mono; absent when captions were used)",
        f"- transcript.txt    transcript with timestamps [mm:ss - mm:ss] ({n_words} words, {len(segments)} segments)",
        "- transcript.json   same transcript, structured",
    ]

    lines += _chapters_block(info.get("chapters") or [])
    lines += _heatmap_block(info.get("heatmap") or [])
    lines += _frames_block(frames, grid_files) if frames else _audio_only_block()

    (outdir / "MANIFEST.txt").write_text("\n".join(lines), encoding="utf-8")
