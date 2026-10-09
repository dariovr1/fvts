"""Frame sampling, extraction and perceptual deduplication."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from ._ffmpeg import get_duration, get_ffmpeg, run
from ._time import fmt_ts, frange

MIN_FRAME_GAP = 0.4
THUMB_SIZE = (160, 90)
DEFAULT_DUP_MAD = 1.0


def headers_to_ffmpeg_arg(headers: dict | None) -> str:
    if not headers:
        return ""
    return "".join(f"{key}: {value}\r\n" for key, value in headers.items())


def scene_change_timestamps(video_source: str | Path, threshold: float) -> list[float]:
    cmd = [
        get_ffmpeg(),
        "-i",
        str(video_source),
        "-vf",
        f"select='gt(scene,{threshold})',showinfo",
        "-f",
        "null",
        "-",
    ]
    result = run(cmd)
    return [float(m) for m in re.findall(r"pts_time:(\d+\.?\d*)", result.stderr)]


def sample_timestamps(duration: float, scene_ts: list[float], fps_floor: float, max_frames: int) -> list[float]:
    """Merge scene-change timestamps with a fixed-interval floor, then thin out."""
    floor_ts = [round(t, 2) for t in frange(0.0, duration, fps_floor)]
    merged = sorted({round(t, 2) for t in scene_ts} | set(floor_ts))

    deduped: list[float] = []
    for t in merged:
        if not deduped or t - deduped[-1] >= MIN_FRAME_GAP:
            deduped.append(t)

    if len(deduped) > max_frames:
        idx = [round(i * (len(deduped) - 1) / (max_frames - 1)) for i in range(max_frames)]
        deduped = sorted({deduped[i] for i in idx})

    return deduped


def extract_frame(
    video_source: str | Path, timestamp: float, out_path: Path, width: int, headers: dict | None = None
) -> bool:
    """Extract a single frame. ``video_source`` may be a local path or a direct
    streaming URL (ffmpeg then seeks via HTTP range requests, fetching only the
    bytes needed for that frame)."""
    cmd = [get_ffmpeg()]
    header_arg = headers_to_ffmpeg_arg(headers)
    if header_arg:
        cmd += ["-headers", header_arg]
    cmd += [
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video_source),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-1",
        "-q:v",
        "3",
        str(out_path),
    ]
    result = run(cmd)
    return result.returncode == 0 and out_path.exists()


def average_hash(img: Image.Image, hash_size: int = 8) -> int:
    small = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
    try:
        pixels = list(small.get_flattened_data())
    except AttributeError:  # Pillow < 11
        pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel >= avg else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def gray_thumbnail(img: Image.Image, size: tuple[int, int] = THUMB_SIZE) -> bytes:
    """Downscaled grayscale bytes, used as a content fingerprint for dedup.

    A perceptual hash is too coarse for screen recordings: different terminal
    states or slides hash identically because most of the frame is unchanged. A
    small grayscale thumbnail compared by mean absolute difference keeps those
    content changes visible while still merging truly static stretches.
    """
    return img.convert("L").resize(size, Image.LANCZOS).tobytes()


def mean_abs_diff(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b, strict=False)) / len(a)


def sample_and_dedup_frames(
    video_source: str | Path,
    outdir: Path,
    scene_thresh: float,
    fps_floor: float,
    max_frames: int,
    width: int,
    duration: float | None = None,
    headers: dict | None = None,
    skip_scene_detect: bool = False,
    workers: int = 6,
    dup_threshold: float = DEFAULT_DUP_MAD,
) -> list[dict]:
    """Extract candidate frames concurrently, then dedupe in temporal order."""
    frames_dir = outdir / "frames"
    frames_dir.mkdir(exist_ok=True)
    for old in frames_dir.glob("*.jpg"):
        old.unlink()

    if duration is None:
        duration = get_duration(video_source)
    scene_ts = [] if skip_scene_detect else scene_change_timestamps(video_source, scene_thresh)
    timestamps = sample_timestamps(duration, scene_ts, fps_floor, max_frames)

    temp_paths: dict[int, Path] = {}
    n_workers = max(1, min(workers, len(timestamps))) if timestamps else 1
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(
                extract_frame, video_source, t, frames_dir / f"_cand_{i:04d}.jpg", width, headers
            ): i
            for i, t in enumerate(timestamps)
        }
        for future in as_completed(futures):
            index = futures[future]
            tmp_path = frames_dir / f"_cand_{index:04d}.jpg"
            try:
                ok = future.result()
            except Exception:
                ok = False
            if ok and tmp_path.exists():
                temp_paths[index] = tmp_path

    kept: list[dict] = []
    last_thumb: bytes | None = None
    for index, t in enumerate(timestamps):
        tmp_path = temp_paths.get(index)
        if tmp_path is None:
            continue
        img = Image.open(tmp_path)
        try:
            thumb = gray_thumbnail(img)
        finally:
            img.close()
        if last_thumb is not None and mean_abs_diff(thumb, last_thumb) <= dup_threshold:
            tmp_path.unlink(missing_ok=True)
            continue
        final_path = frames_dir / f"frame_{len(kept):03d}.jpg"
        tmp_path.replace(final_path)
        kept.append({"file": final_path.name, "timestamp_sec": round(t, 2), "timestamp": fmt_ts(t)})
        last_thumb = thumb

    (outdir / "frames.json").write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    return kept
