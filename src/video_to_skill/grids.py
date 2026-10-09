"""Labelled contact sheets ("grids") built from the extracted frames."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABEL_HEIGHT = 22
LABEL_FONT_SIZE = 16


def _load_font() -> ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, LABEL_FONT_SIZE)
        except Exception:
            continue
    return ImageFont.load_default()


def build_grids(frames: list[dict], outdir: Path, cols: int, rows: int, cell_width: int) -> list[str]:
    """Render contact sheets with ``#index @ timestamp`` labels on each cell."""
    frames_dir = outdir / "frames"
    grids_dir = outdir / "grids"
    grids_dir.mkdir(exist_ok=True)
    for old in grids_dir.glob("*.jpg"):
        old.unlink()

    if not frames:
        return []

    per_sheet = cols * rows
    font = _load_font()
    grid_files: list[str] = []

    for sheet_index in range(0, len(frames), per_sheet):
        chunk = frames[sheet_index:sheet_index + per_sheet]
        first_img = Image.open(frames_dir / chunk[0]["file"])
        try:
            cell_height = int(first_img.height * (cell_width / first_img.width))
        finally:
            first_img.close()

        sheet_width = cols * cell_width
        sheet_height = rows * (cell_height + LABEL_HEIGHT)
        sheet = Image.new("RGB", (sheet_width, sheet_height), "black")
        draw = ImageDraw.Draw(sheet)

        for i, frame in enumerate(chunk):
            row, col = divmod(i, cols)
            frame_img = Image.open(frames_dir / frame["file"]).resize((cell_width, cell_height))
            try:
                x, y = col * cell_width, row * (cell_height + LABEL_HEIGHT)
                sheet.paste(frame_img, (x, y + LABEL_HEIGHT))
            finally:
                frame_img.close()
            label = f"#{sheet_index + i} @ {frame['timestamp']}"
            draw.rectangle([x, y, x + cell_width, y + LABEL_HEIGHT], fill=(20, 20, 20))
            draw.text((x + 4, y + 3), label, fill="white", font=font)

        grid_name = f"grid_{sheet_index // per_sheet:03d}.jpg"
        sheet.save(grids_dir / grid_name, quality=85)
        grid_files.append(grid_name)

    return grid_files
