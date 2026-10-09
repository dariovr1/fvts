from PIL import Image

from video_to_skill.frames import (
    MIN_FRAME_GAP,
    average_hash,
    gray_thumbnail,
    hamming,
    mean_abs_diff,
    sample_timestamps,
)


def test_sample_timestamps_floor_only():
    assert sample_timestamps(10.0, [], fps_floor=2.0, max_frames=100) == [0.0, 2.0, 4.0, 6.0, 8.0]


def test_sample_timestamps_respects_max_frames():
    ts = sample_timestamps(100.0, [], fps_floor=1.0, max_frames=10)
    assert len(ts) == 10


def test_sample_timestamps_merges_scene_changes():
    ts = sample_timestamps(4.0, [1.0, 3.0], fps_floor=2.0, max_frames=100)
    assert ts == [0.0, 1.0, 2.0, 3.0]


def test_sample_timestamps_enforces_min_gap():
    ts = sample_timestamps(1.0, [0.1, 0.2, 0.35], fps_floor=10.0, max_frames=100)
    for a, b in zip(ts, ts[1:], strict=False):
        assert b - a >= MIN_FRAME_GAP


def test_hamming_distance():
    assert hamming(0b1010, 0b1010) == 0
    assert hamming(0b1010, 0b0101) == 4


def test_average_hash_is_stable_for_identical_images():
    img = Image.new("RGB", (32, 32), "gray")
    assert average_hash(img) == average_hash(img)


def test_mean_abs_diff_zero_for_identical_thumbnails():
    img = Image.new("RGB", (320, 180), "white")
    thumb = gray_thumbnail(img)
    assert mean_abs_diff(thumb, thumb) == 0


def test_mean_abs_diff_detects_change():
    dark = gray_thumbnail(Image.new("RGB", (320, 180), "black"))
    light = gray_thumbnail(Image.new("RGB", (320, 180), "white"))
    assert mean_abs_diff(dark, light) == 255.0
