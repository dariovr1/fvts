"""The "radar": a quick, download-free way to tell whether a video is visually
static (a talking-head talk, a slide, a fixed webcam) or dynamic (frequent cuts).

A handful of low-resolution frames are grabbed via remote seek (a few KB each)
and compared with average-hash Hamming distance. This lets the CLI recommend the
lightweight streaming mode instead of downloading a whole video that would look
almost identical frame to frame.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from ._time import fmt_ts
from .download import estimate_size_mb as _estimate_size_mb  # re-exported for callers
from .download import resolve_stream_targets
from .frames import average_hash, extract_frame, hamming

RADAR_STATIC_THRESHOLD = 6
RADAR_MIN_DURATION = 300
PROBE_FRACTIONS = (0.12, 0.30, 0.50, 0.70, 0.88)
PROBE_WIDTH = 160


def probe_visual_dynamism(video_url: str, headers: dict | None, duration: float) -> float:
    """Mean Hamming distance between consecutive sampled frames.

    Near 0 means the frame barely changes (static); a high value means a visually
    dynamic video. Returns 999.0 when it cannot sample enough frames.
    """
    if duration <= 0:
        return 999.0

    hashes: list[int] = []
    with tempfile.TemporaryDirectory(prefix="video_to_skill_probe_") as tmp:
        tmp_dir = Path(tmp)
        for i, fraction in enumerate(PROBE_FRACTIONS):
            out = tmp_dir / f"probe_{i}.jpg"
            if extract_frame(video_url, duration * fraction, out, width=PROBE_WIDTH, headers=headers):
                img = Image.open(out)
                try:
                    hashes.append(average_hash(img))
                finally:
                    img.close()

    if len(hashes) < 2:
        return 999.0
    diffs = [hamming(hashes[i], hashes[i + 1]) for i in range(len(hashes) - 1)]
    return sum(diffs) / len(diffs)


def estimate_size_mb(fmt: dict, duration: float) -> float | None:
    return _estimate_size_mb(fmt, duration)


def print_probe_report(url: str, language: str | None) -> None:
    """Print title/duration, the radar verdict and estimated sizes, then return."""
    info, audio_format, video_format = resolve_stream_targets(url, language)
    duration = info.get("duration") or 0

    video_mb = estimate_size_mb(video_format, duration) if video_format else None
    audio_mb = estimate_size_mb(audio_format, duration)

    if duration < RADAR_MIN_DURATION:
        avg_diff, verdict = None, f"n/a (video < {RADAR_MIN_DURATION // 60} min: streaming is not worth it)"
    else:
        avg_diff = probe_visual_dynamism(video_format["url"], video_format.get("http_headers"), duration)
        verdict = (
            "static -> streaming recommended"
            if avg_diff <= RADAR_STATIC_THRESHOLD
            else "dynamic -> full download recommended"
        )

    has_subs = bool(info.get("subtitles") or info.get("automatic_captions"))

    print("[video-to-skill] RADAR REPORT")
    print(f"  Title:          {info.get('title')}")
    print(f"  Channel:        {info.get('uploader')}")
    print(f"  Duration:       {fmt_ts(duration)}")
    subs = "available (whisper likely not needed)" if has_subs else "absent (whisper likely needed)"
    print(f"  Subtitles:      {subs}")
    if video_mb:
        print(f"  Video (<=720p): ~{video_mb:.0f} MB")
    else:
        print("  Video (<=720p): unknown")
    print(f"  Audio only:     ~{audio_mb:.0f} MB" if audio_mb else "  Audio only:     unknown")
    print(f"  Radar verdict:  {verdict}" + (f" (mean diff={avg_diff:.1f})" if avg_diff is not None else ""))
