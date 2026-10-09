from video_to_skill.manifest import write_manifest


def _info():
    return {
        "title": "Example",
        "uploader": "A Channel",
        "chapters": [{"start_time": 0, "title": "Intro"}, {"start_time": 65, "title": "Main"}],
        "heatmap": [{"start_time": 60, "end_time": 90, "value": 0.8}],
    }


def test_write_manifest_with_frames(tmp_path):
    segments = [{"start": 0.0, "end": 1.0, "text": "hello world"}]
    frames = [{"file": "frame_000.jpg", "timestamp_sec": 0.0, "timestamp": "00:00.00"}]
    write_manifest(tmp_path, _info(), 120.0, segments, frames, ["grid_000.jpg"], "http://x", "subtitles (en)", "full download")
    text = (tmp_path / "MANIFEST.txt").read_text(encoding="utf-8")
    assert "HOW TO 'WATCH' THE VIDEO" in text
    assert "CHAPTERS" in text
    assert "MOST REPLAYED" in text
    assert "Example" in text


def test_write_manifest_audio_only(tmp_path):
    segments = [{"start": 0.0, "end": 1.0, "text": "hello"}]
    write_manifest(tmp_path, _info(), 120.0, segments, [], [], "http://x", "faster-whisper/x", "audio only")
    text = (tmp_path / "MANIFEST.txt").read_text(encoding="utf-8")
    assert "AUDIO-ONLY MODE" in text
    assert "HOW TO 'WATCH' THE VIDEO" not in text
