"""Timestamp formatting and iteration helpers (no dependencies)."""

from __future__ import annotations

from collections.abc import Iterator


def fmt_ts(seconds: float) -> str:
    """Full timestamp with centiseconds, e.g. ``07:05.25`` or ``1:02:03.00``."""
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
    return f"{minutes:02d}:{secs:05.2f}"


def fmt_ts_short(seconds: float) -> str:
    """Short timestamp for chapters/heatmaps, e.g. ``07:05`` or ``1:02:03``."""
    seconds = int(max(0.0, seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def frange(start: float, stop: float, step: float) -> Iterator[float]:
    """Float range, half-open ``[start, stop)``."""
    value = start
    while value < stop:
        yield value
        value += step
