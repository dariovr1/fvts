"""FFmpeg resolution and thin process helpers.

faster-whisper may shell out to the literal command ``ffmpeg``, while the binary
bundled by ``imageio-ffmpeg`` is named like ``ffmpeg-win-x86_64-<version>.exe``.
We create a renamed alias (``ffmpeg`` / ``ffmpeg.exe``) in a per-user cache
directory, prepend that directory to ``PATH`` and return the alias path. This
covers both our own direct calls and the ones made internally by whisper.

No user-specific paths are hard-coded; the cache directory is derived from the
environment (``VIDEO_TO_SKILL_CACHE`` > platform cache dir > ``~/.cache``).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg

_FFMPEG_CACHE: str | None = None


def cache_bin_dir() -> Path:
    """Directory used to hold the renamed ffmpeg alias."""
    override = os.environ.get("VIDEO_TO_SKILL_CACHE")
    if override:
        return Path(override) / "bin"
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / ".cache")
        return Path(base) / "video-to-skill" / "bin"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "video-to-skill" / "bin"


def _ensure_ffmpeg_on_path() -> str:
    source = Path(imageio_ffmpeg.get_ffmpeg_exe())
    bin_dir = cache_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    alias = bin_dir / ("ffmpeg.exe" if source.suffix == ".exe" else "ffmpeg")
    if not alias.exists():
        shutil.copy(source, alias)
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    return str(alias)


def get_ffmpeg() -> str:
    """Return the path to a usable ffmpeg binary (computed once per process)."""
    global _FFMPEG_CACHE
    if _FFMPEG_CACHE is None:
        _FFMPEG_CACHE = _ensure_ffmpeg_on_path()
    return _FFMPEG_CACHE


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kwargs)


def get_duration(video_source: str | Path) -> float:
    """Duration in seconds of a local file or remote stream URL (0.0 if unknown)."""
    result = run([get_ffmpeg(), "-i", str(video_source)])
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def extract_audio(video_path: Path, outdir: Path) -> Path:
    """Extract a 16 kHz mono wav track from a local video file."""
    audio_path = outdir / "audio.wav"
    cmd = [get_ffmpeg(), "-y", "-i", str(video_path), "-ar", "16000", "-ac", "1", "-vn", str(audio_path)]
    result = run(cmd)
    if result.returncode != 0 or not audio_path.exists():
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr[-2000:]}")
    return audio_path
