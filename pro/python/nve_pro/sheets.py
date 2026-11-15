"""Sheets Claude looks at to read a reference video's style: what the tools cannot measure (font, size, colour,
glow, position, how text and graphics come in) is read from these pictures.

- overview.jpg: the whole video at a glance (one frame every few seconds, time on each)
- shots_N.jpg:  one sharp frame per shot (360 px wide, big enough to read fonts), shot number and time
- strip_N.jpg:  8 fps strips over the first 1.5 s of the hook and of the shots where most changes, to see
                entrances (pop, slide, fade, typewriter...) and their speed
"""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

BG = (18, 18, 22)
INK = (255, 225, 110)


def grab(video: Path, t: float, width: int) -> Image.Image | None:
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def _label(im: Image.Image, text: str) -> Image.Image:
    out = Image.new("RGB", (im.width, im.height + 22), BG)
    out.paste(im, (0, 0))
    ImageDraw.Draw(out).text((6, im.height + 4), text, fill=INK)
    return out


def _grid(tiles: list[Image.Image], cols: int) -> Image.Image:
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), BG)
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    return sheet


def overview(video: Path, duration: float, out: Path, most: int = 36) -> Path | None:
    step = max(1.0, duration / most)
    times = [round(k * step, 2) for k in range(int(duration / step) + 1) if k * step < duration - 0.05][:most]
    tiles = [_label(im, f"{t:.1f}s") for t in times if (im := grab(video, t, 180))]
    if not tiles:
        return None
    _grid(tiles, 9).save(out, quality=85)
    return out


def shot_sheets(video: Path, shots: list[dict], out_dir: Path, per_sheet: int = 12, most: int = 48) -> list[Path]:
    picks = shots if len(shots) <= most else [shots[round(i * (len(shots) - 1) / (most - 1))] for i in range(most)]
    tiles = []
    for s in picks:
        t = s["start"] + min(s["duration"] * 0.5, max(0.3, s["duration"] * 0.4))
        im = grab(video, t, 360)
        if im:
            tiles.append(_label(im, f"#{s['index']}  {s['start']:.1f}-{s['end']:.1f}s  {s['transition_in']}"))
    paths = []
    for k in range(0, len(tiles), per_sheet):
        p = out_dir / f"shots_{k // per_sheet + 1}.jpg"
        _grid(tiles[k:k + per_sheet], 6).save(p, quality=85)
        paths.append(p)
    return paths


def strips(video: Path, shots: list[dict], out_dir: Path, starts: list[float], fps: int = 8, seconds: float = 1.5) -> list[Path]:
    paths = []
    for k, t0 in enumerate(starts):
        frames = [im for j in range(int(fps * seconds)) if (im := grab(video, t0 + j / fps, 150))]
        if not frames:
            continue
        tiles = [_label(im, f"{t0 + j / fps:.2f}s") for j, im in enumerate(frames)]
        p = out_dir / f"strip_{k + 1}.jpg"
        _grid(tiles, len(tiles)).save(p, quality=82)
        paths.append(p)
    return paths


def strip_starts(shots: list[dict], most: int = 6) -> list[float]:
    """The hook, then the starts of the longer shots spread over the video (titles and graphics usually enter
    at a shot start)."""
    starts = [0.0]
    rest = sorted((s for s in shots[1:] if s["duration"] >= 1.0), key=lambda s: -s["duration"])[: most * 2]
    rest = sorted(rest, key=lambda s: s["start"])
    if rest:
        step = max(1, len(rest) // (most - 1))
        starts += [s["start"] for s in rest[::step]][: most - 1]
    return starts
