from PIL import Image

from video_to_skill.grids import build_grids


def test_build_grids_creates_sheets(tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frames = []
    for i in range(3):
        Image.new("RGB", (160, 90), (i * 40, 0, 0)).save(frames_dir / f"frame_{i:03d}.jpg")
        frames.append({"file": f"frame_{i:03d}.jpg", "timestamp_sec": float(i), "timestamp": f"00:0{i}.00"})

    grid_files = build_grids(frames, tmp_path, cols=2, rows=1, cell_width=100)
    assert len(grid_files) == 2
    for name in grid_files:
        assert (tmp_path / "grids" / name).exists()


def test_build_grids_empty(tmp_path):
    assert build_grids([], tmp_path, cols=2, rows=1, cell_width=100) == []
