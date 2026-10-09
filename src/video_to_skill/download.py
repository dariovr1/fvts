"""Download and stream-target resolution.

Two acquisition paths are supported:

* ``full`` — download the whole video with yt-dlp (plus best-effort subtitles);
* ``stream`` / ``audio`` — resolve direct formats, download only the audio when
  speech-to-text is needed, and (for ``stream``) extract frames by seeking on the
  remote URL so the whole video is never stored locally.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._ffmpeg import get_ffmpeg, run
from .subtitles import try_download_subtitles

VIDEO_MAX_HEIGHT = 720
DECENT_AUDIO_ABR = 64


def slim_info(info: dict) -> dict:
    """Keep only the metadata that is useful downstream and small on disk."""
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "duration": info.get("duration"),
        "webpage_url": info.get("webpage_url"),
        "upload_date": info.get("upload_date"),
        "language": info.get("language"),
        "description": (info.get("description") or "")[:2000],
        "chapters": info.get("chapters") or [],
        "heatmap": info.get("heatmap") or [],
    }


def write_info(outdir: Path, info: dict) -> None:
    (outdir / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def download(source: str, outdir: Path, language: str | None) -> tuple[Path, dict]:
    """Download a video (or copy a local file) and write ``info.json``."""
    video_path = outdir / "source.mp4"

    if Path(source).exists():
        import shutil

        shutil.copy(source, video_path)
        info = {"title": Path(source).stem, "duration": None, "webpage_url": str(source)}
        write_info(outdir, info)
        return video_path, info

    import yt_dlp

    options = {
        "format": f"bv*[height<={VIDEO_MAX_HEIGHT}]+ba/b[height<={VIDEO_MAX_HEIGHT}]/best",
        "outtmpl": str(outdir / "source.%(ext)s"),
        "merge_output_format": "mp4",
        "ffmpeg_location": get_ffmpeg(),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        raw_info = ydl.extract_info(source, download=True)

    if not video_path.exists():
        candidates = [c for c in outdir.glob("source.*") if c.suffix not in (".json", ".vtt")]
        if not candidates:
            raise RuntimeError("Download succeeded but source.mp4 was not found.")
        video_path = candidates[0]

    info = slim_info(raw_info)
    write_info(outdir, info)

    try:
        try_download_subtitles(source, outdir, language, raw_info)
    except Exception as exc:
        print(f"[video-to-skill]     (subtitles unavailable: {exc})")

    return video_path, info


def resolve_stream_targets(
    source: str, language: str | None, need_video: bool = True
) -> tuple[dict, dict, dict | None]:
    """Resolve formats for the lightweight path (audio + remote frame seeking)."""
    import yt_dlp

    del language  # kept for interface symmetry; format choice is language-agnostic
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(source, download=False)

    formats = info.get("formats") or []
    audio_formats = [
        f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
    ]
    video_formats = [
        f for f in formats if f.get("vcodec") not in (None, "none") and (f.get("height") or 9999) <= VIDEO_MAX_HEIGHT
    ]

    if not audio_formats or (need_video and not video_formats):
        raise RuntimeError(
            "No separate audio/video formats available for streaming mode "
            "(some sites or live streams do not expose them): retry with --mode full."
        )

    decent_audio = [f for f in audio_formats if (f.get("abr") or 0) >= DECENT_AUDIO_ABR]
    audio_format = (
        min(decent_audio, key=lambda f: f.get("abr") or 0)
        if decent_audio
        else max(audio_formats, key=lambda f: f.get("abr") or 0)
    )

    video_format = None
    if need_video:
        video_format = max(
            video_formats,
            key=lambda f: (
                bool(f.get("filesize") or f.get("filesize_approx")),
                f.get("height") or 0,
                f.get("ext") == "mp4",
            ),
        )

    return info, audio_format, video_format


def estimate_size_mb(fmt: dict, duration: float) -> float | None:
    """Estimate a format's download size in MB (declared size, else bitrate*duration)."""
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        return size / (1024 * 1024)
    bitrate_kbps = fmt.get("tbr") or fmt.get("vbr") or fmt.get("abr")
    if bitrate_kbps and duration:
        return (bitrate_kbps * 1000 / 8 * duration) / (1024 * 1024)
    return None


def download_stream_audio(source: str, audio_format: dict, outdir: Path) -> Path:
    """Download only the audio track (a few MB even for long videos) to a wav."""
    import yt_dlp

    options = {
        "format": audio_format["format_id"],
        "outtmpl": str(outdir / "audio_src.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([source])

    candidates = [c for c in outdir.glob("audio_src.*") if c.suffix != ".json"]
    if not candidates:
        raise RuntimeError("Audio download (streaming mode) failed.")
    audio_source = candidates[0]

    audio_path = outdir / "audio.wav"
    cmd = [get_ffmpeg(), "-y", "-i", str(audio_source), "-ar", "16000", "-ac", "1", audio_path.as_posix()]
    result = run(cmd)
    if result.returncode != 0 or not audio_path.exists():
        raise RuntimeError(f"Audio conversion failed:\n{result.stderr[-2000:]}")
    return audio_path
