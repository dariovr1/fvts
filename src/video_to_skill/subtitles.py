"""YouTube subtitle (.vtt) handling.

Fetching subtitles first is a big win: when a usable track exists the transcript
is instant and no speech-to-text model is needed. It is always best-effort — any
failure here falls back to whisper.
"""

from __future__ import annotations

import html
import re
import urllib.request
from pathlib import Path

_VTT_TAG_RE = re.compile(r"<[^>]+>")
_VTT_TIME_RE = re.compile(
    r"(\d{2}:)?(\d{2}):(\d{2}\.\d{3})\s*-->\s*(\d{2}:)?(\d{2}):(\d{2}\.\d{3})"
)
_DEFAULT_LANGS = ("en",)


def _vtt_time_to_sec(hours: str | None, minutes: str, seconds: str) -> float:
    return (int(hours[:-1]) * 3600 if hours else 0) + int(minutes) * 60 + float(seconds)


def _preferred_languages(language: str | None) -> list[str]:
    return [language] if language else list(_DEFAULT_LANGS)


def parse_vtt(vtt_path: Path) -> list[dict]:
    """Parse a .vtt file (manual or auto-generated) into timestamped segments.

    Auto-generated YouTube captions display a sliding window: every cue repeats
    the tail of the previous one plus new words. A naive parse yields a
    transcript full of repetitions, so we deduplicate at the word level and then
    re-segment the clean word stream into citable blocks.
    """
    raw = vtt_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", raw)

    cues: list[dict] = []
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        time_line_idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if time_line_idx is None:
            continue
        match = _VTT_TIME_RE.search(lines[time_line_idx])
        if not match:
            continue
        start = _vtt_time_to_sec(match.group(1), match.group(2), match.group(3))
        end = _vtt_time_to_sec(match.group(4), match.group(5), match.group(6))
        text = " ".join(lines[time_line_idx + 1:]).strip()
        text = _VTT_TAG_RE.sub("", text).strip()
        text = html.unescape(text)
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        cues.append({"start": start, "end": end, "text": text})

    max_overlap_words = 30
    word_stream: list[tuple[str, float]] = []
    for cue in cues:
        current = cue["text"].split()
        if not word_stream:
            word_stream.extend((word, cue["start"]) for word in current)
            continue
        tail = [word for word, _ in word_stream[-max_overlap_words:]]
        best_k = 0
        for k in range(min(len(tail), len(current)), 0, -1):
            if tail[-k:] == current[:k]:
                best_k = k
                break
        new_words = current[best_k:] if best_k > 0 else (current if current != tail else [])
        word_stream.extend((word, cue["start"]) for word in new_words)

    if not word_stream:
        return []

    segments: list[dict] = []
    current_words: list[str] = []
    seg_start = word_stream[0][1]
    last_t = seg_start
    for word, t in word_stream:
        if not current_words:
            seg_start = t
        current_words.append(word)
        last_t = t
        ends_sentence = bool(word) and word[-1:] in ".!?"
        too_long = len(current_words) >= 22 or (last_t - seg_start) >= 9.0
        if ends_sentence or too_long:
            segments.append({"start": seg_start, "end": last_t, "text": " ".join(current_words)})
            current_words = []
    if current_words:
        segments.append({"start": seg_start, "end": last_t, "text": " ".join(current_words)})

    return [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"]} for s in segments]


def choose_track(manual: dict, automatic: dict, language: str | None) -> tuple[str | None, dict | None]:
    """Pick (language, .vtt track), preferring manual captions over automatic."""
    for meta in (manual, automatic):
        for lang in _preferred_languages(language):
            tracks = meta.get(lang) or []
            vtt = next((track for track in tracks if track.get("ext") == "vtt"), None)
            if vtt:
                return lang, vtt
    return None, None


def choose_language(available: dict, language: str | None) -> str | None:
    for lang in _preferred_languages(language):
        if lang in available:
            return lang
    return None


def try_download_subtitles(source_url: str, outdir: Path, language: str | None, info: dict) -> None:
    """Download a single .vtt track, best-effort.

    First tries the direct URL already present in ``info`` (no extra yt-dlp
    extraction); falls back to yt-dlp for the cases the direct fetch cannot
    handle. Errors propagate to the caller, which logs and falls back to whisper.
    """
    manual = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}
    lang, track = choose_track(manual, automatic, language)

    if lang and track:
        url = track.get("url") or ""
        # Only fetch plain web URLs. The caption URL normally comes from the
        # platform's metadata, but validating the scheme keeps a tampered or
        # unexpected value from pointing the request at a local resource.
        if url.startswith(("http://", "https://")):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(request, timeout=30).read().decode("utf-8", "replace")
                if data.strip():
                    (outdir / f"source.{lang}.vtt").write_text(data, encoding="utf-8")
                    return
            except Exception:
                pass

    if not (manual or automatic):
        return

    import yt_dlp

    chosen_lang = lang or choose_language(manual, language) or choose_language(automatic, language)
    if not chosen_lang:
        return

    options = {
        "outtmpl": str(outdir / "source.%(ext)s"),
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [chosen_lang],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([source_url])


def find_captions(outdir: Path, language: str | None) -> tuple[list[dict], str] | None:
    """Return (segments, language_code) from a downloaded .vtt, or None."""
    vtt_files = sorted(outdir.glob("source.*.vtt"))
    if not vtt_files:
        return None

    chosen = None
    for lang in _preferred_languages(language):
        chosen = next((f for f in vtt_files if f.name == f"source.{lang}.vtt"), None)
        if chosen:
            break
    if chosen is None:
        chosen = vtt_files[0]

    segments = parse_vtt(chosen)
    if not segments:
        return None
    return segments, chosen.stem.rsplit(".", 1)[-1]
