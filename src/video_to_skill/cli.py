"""Command-line interface: ``probe`` and ``watch``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from ._ffmpeg import get_duration, get_ffmpeg
from .download import download, download_stream_audio, resolve_stream_targets, slim_info, write_info
from .frames import sample_and_dedup_frames
from .grids import build_grids
from .manifest import write_manifest
from .radar import RADAR_MIN_DURATION, RADAR_STATIC_THRESHOLD, print_probe_report, probe_visual_dynamism
from .subtitles import find_captions, try_download_subtitles
from .transcribe import transcribe, write_transcript_files

LOG_PREFIX = "[video-to-skill]"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-to-skill",
        description="Capture a single video into an agent-readable package, then distill a reusable skill from it.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser(
        "probe",
        help="Download-free diagnosis: title, duration, radar verdict and estimated sizes.",
    )
    probe.add_argument("source", help="YouTube URL")
    probe.add_argument("--language", default=None, help="Preferred caption language code (default: en)")

    watch = sub.add_parser("watch", help="Run the full capture pipeline and build the package.")
    watch.add_argument("source", help="YouTube URL or path to a local video file")
    watch.add_argument("--outdir", default=None, help="Output folder (default: ./runs/<video_id>)")
    watch.add_argument(
        "--mode",
        choices=["auto", "stream", "full", "audio"],
        default="auto",
        help="'auto' lets the radar choose; 'stream' avoids downloading the video; 'full' always "
        "downloads it; 'audio' extracts no frames at all.",
    )
    watch.add_argument("--whisper-model", default="large-v3-turbo",
                       help="faster-whisper model, used only when captions are unavailable")
    watch.add_argument("--whisper-beam-size", type=int, default=1,
                       help="faster-whisper beam size (1 = fast preset, 5 = library default)")
    watch.add_argument("--glossary", default="",
                       help="Optional comma-separated terms/proper nouns to bias the transcriber's spelling")
    watch.add_argument("--no-captions", action="store_true",
                       help="Ignore available subtitles and force speech-to-text")
    watch.add_argument("--language", default=None, help="Language code for captions/transcription (default: auto)")
    watch.add_argument("--scene-thresh", type=float, default=0.28, help="Scene-change detection threshold")
    watch.add_argument("--fps-floor", type=float, default=2.0,
                       help="Guarantee at least one frame every N seconds")
    watch.add_argument("--max-frames", type=int, default=60, help="Maximum number of frames to keep")
    watch.add_argument("--frame-width", type=int, default=960, help="Extracted frame width in pixels")
    watch.add_argument("--frame-workers", type=int, default=6,
                       help="Parallel frame extractions (lower it if the remote source rate-limits)")
    watch.add_argument("--dedup-mad", type=float, default=1.0,
                       help="Drop a frame when its mean absolute pixel difference from the previous kept "
                            "frame is at or below this value (0 disables near-duplicate removal)")
    watch.add_argument("--grid-cols", type=int, default=4)
    watch.add_argument("--grid-rows", type=int, default=3)
    watch.add_argument("--grid-cell-width", type=int, default=400, help="Contact-sheet cell width in pixels")
    watch.add_argument("--force", action="store_true", help="Re-run even if the output folder already exists")

    return parser


def _video_id(source: str) -> str:
    import re

    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{6,})", source)
    if match:
        return match.group(1)
    return re.sub(r"[^A-Za-z0-9_-]+", "_", source)[:40]


def _resolve_radar(args, is_url: bool) -> tuple[bool, str, tuple | None]:
    """Decide the acquisition path for a URL. Returns (use_stream, mode_note, targets)."""
    if args.mode == "audio":
        print(f"{LOG_PREFIX} 0/6 audio-only mode: no frames, radar not needed...")
        targets = resolve_stream_targets(args.source, args.language, need_video=False)
        return True, "audio only (no frames, no visual understanding)", targets

    if not is_url:
        return False, "full download (local file)", None

    info, audio_format, video_format = resolve_stream_targets(args.source, args.language)
    targets = (info, audio_format, video_format)

    if args.mode == "stream":
        return True, "streaming (forced by --mode stream)", targets

    duration = info.get("duration") or 0
    if duration < RADAR_MIN_DURATION:
        return False, f"full download (video < {RADAR_MIN_DURATION // 60} min, streaming not worthwhile)", targets

    avg_diff = probe_visual_dynamism(video_format["url"], video_format.get("http_headers"), duration)
    use_stream = avg_diff <= RADAR_STATIC_THRESHOLD
    verdict = "static -> streaming" if use_stream else "dynamic -> full download"
    print(f"{LOG_PREFIX}     -> sample mean diff: {avg_diff:.1f} ({verdict})")
    return use_stream, f"{'streaming' if use_stream else 'full download'} (radar: mean diff={avg_diff:.1f}, {verdict})", targets


def run_watch(args) -> int:
    is_url = args.source.startswith("http")
    video_id = _video_id(args.source) if is_url else Path(args.source).stem
    outdir = Path(args.outdir) if args.outdir else Path.cwd() / "runs" / video_id

    print(f"{LOG_PREFIX} using ffmpeg at {get_ffmpeg()}")

    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "MANIFEST.txt").exists() and not args.force:
        print(f"{LOG_PREFIX} existing output found in {outdir} (use --force to redo). Skipping.")
        print(str(outdir))
        return 0

    if args.force:
        for stale in list(outdir.glob("source.*")) + list(outdir.glob("audio_src.*")) + [outdir / "audio.wav"]:
            if stale.exists() and stale.suffix != ".vtt":
                stale.unlink()

    need_frames = args.mode != "audio"
    use_stream, mode_note, targets = _resolve_radar(args, is_url)

    # --- acquisition -------------------------------------------------------
    if use_stream:
        info, audio_format, video_format = targets
        if args.mode != "audio":
            print(f"{LOG_PREFIX} 1/6 streaming: no video downloaded, audio only when needed...")
        video_source = video_format["url"] if video_format else args.source
        video_headers = (video_format or {}).get("http_headers")
        duration = info.get("duration") or 0.0
        write_info(outdir, slim_info(info))
        try:
            try_download_subtitles(args.source, outdir, args.language, info)
        except Exception as exc:
            print(f"{LOG_PREFIX}     (subtitles unavailable: {exc})")
        print(f"{LOG_PREFIX}     -> {info.get('title')} (video not downloaded)")
    else:
        print(f"{LOG_PREFIX} 1/6 downloading (video + subtitles if available)...")
        video_path, info = download(args.source, outdir, args.language)
        print(f"{LOG_PREFIX}     -> {video_path.name} | {info.get('title')}")
        video_source = video_path
        video_headers = None
        duration = info.get("duration") or get_duration(video_path)

    # --- transcript --------------------------------------------------------
    captions = None if args.no_captions else find_captions(outdir, args.language)
    if captions:
        segments, lang = captions
        write_transcript_files(outdir, segments)
        transcript_source = f"YouTube subtitles ({lang})"
        print(f"{LOG_PREFIX} 2/6 transcript from YouTube subtitles ({lang}), no speech-to-text needed.")
    else:
        print(f"{LOG_PREFIX} 2/6 no usable subtitles: extracting audio + running speech-to-text...")
        if use_stream:
            audio_path = download_stream_audio(args.source, audio_format, outdir)
        else:
            from ._ffmpeg import extract_audio

            audio_path = extract_audio(video_source, outdir)
        segments = transcribe(audio_path, outdir, args.whisper_model, args.language, args.glossary,
                              beam_size=args.whisper_beam_size)
        transcript_source = f"faster-whisper/{args.whisper_model}"
    print(f"{LOG_PREFIX}     -> {len(segments)} segments")

    # --- frames + grids ----------------------------------------------------
    if need_frames:
        strategy = "fixed floor, streaming" if use_stream else "scene-detect + floor"
        print(f"{LOG_PREFIX} 3/6 sampling frames ({strategy})...")
        frames = sample_and_dedup_frames(
            video_source, outdir, args.scene_thresh, args.fps_floor, args.max_frames, args.frame_width,
            duration=duration, headers=video_headers, skip_scene_detect=use_stream, workers=args.frame_workers,
            dup_threshold=args.dedup_mad,
        )
        print(f"{LOG_PREFIX}     -> {len(frames)} frames kept after dedup")
        print(f"{LOG_PREFIX} 4/6 building contact sheets...")
        grid_files = build_grids(frames, outdir, args.grid_cols, args.grid_rows, cell_width=args.grid_cell_width)
        print(f"{LOG_PREFIX}     -> {len(grid_files)} grids")
    else:
        print(f"{LOG_PREFIX} 3/6 audio-only mode: no frames to extract.")
        frames, grid_files = [], []

    print(f"{LOG_PREFIX} 5/6 manifest...")
    write_manifest(
        outdir, info, duration or 0.0, segments, frames, grid_files,
        source_url=args.source if is_url else str(Path(args.source).resolve()),
        transcript_source=transcript_source, mode_note=mode_note,
    )

    if is_url and not use_stream and isinstance(video_source, Path) and video_source.exists():
        video_source.unlink(missing_ok=True)
        print(f"{LOG_PREFIX}     (source.mp4 removed: regenerable from the URL)")

    print(f"{LOG_PREFIX} done. Output in: {outdir}")
    print(str(outdir))
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "probe":
        if not args.source.startswith("http"):
            print(f"{LOG_PREFIX} probe is only useful for URLs (a local file has nothing to fetch).")
            return 2
        print_probe_report(args.source, args.language)
        return 0

    if args.command == "watch":
        return run_watch(args)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
