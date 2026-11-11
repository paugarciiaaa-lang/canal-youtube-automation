#!/usr/bin/env python3
"""Render a short whiteboard-animation style preview for Caspitas.

This is a visual proof of concept only. It does not alter the production
documentary workflow or publish anything to YouTube.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720
FPS = 18
SCENE_SECONDS = 5
SCENES = 3
PAPER = (250, 249, 245)
INK = (28, 28, 28)
GREY = (110, 110, 105)


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def reveal_line(draw: ImageDraw.ImageDraw, points, progress: float, width=6):
    if progress <= 0:
        return
    lengths = []
    total = 0.0
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        lengths.append(length)
        total += length
    remaining = total * min(1.0, progress)
    visible = [points[0]]
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if remaining <= 0:
            break
        fraction = min(1.0, remaining / length)
        visible.append((int(a[0] + (b[0] - a[0]) * fraction),
                        int(a[1] + (b[1] - a[1]) * fraction)))
        remaining -= length
        if fraction < 1:
            break
    if len(visible) > 1:
        draw.line(visible, fill=INK, width=width, joint="curve")


def reveal_circle(draw, box, progress, width=6, start=-90, end=270):
    if progress <= 0:
        return
    draw.arc(box, start=start, end=start + (end - start) * min(progress, 1),
             fill=INK, width=width)


def centered_text(draw, text, y, size, progress=1.0, bold=True):
    f = font(size, bold)
    bbox = draw.textbbox((0, 0), text, font=f)
    x = (WIDTH - (bbox[2] - bbox[0])) // 2
    if progress > 0:
        draw.text((x, y), text, fill=INK, font=f)


def stick_figure(draw, x, y, p):
    # x,y is the head centre; each limb is progressively drawn.
    reveal_circle(draw, (x-34, y-34, x+34, y+34), p, 6)
    reveal_line(draw, [(x, y+34), (x, y+145)], p, 7)
    reveal_line(draw, [(x, y+68), (x-62, y+112)], p, 7)
    reveal_line(draw, [(x, y+68), (x+66, y+96)], p, 7)
    reveal_line(draw, [(x, y+145), (x-52, y+220)], p, 7)
    reveal_line(draw, [(x, y+145), (x+58, y+215)], p, 7)
    if p > .7:
        draw.ellipse((x-10, y-5, x-3, y+2), fill=INK)
        draw.ellipse((x+6, y-5, x+13, y+2), fill=INK)
        draw.arc((x-12, y+2, x+13, y+22), 10, 170, fill=INK, width=3)


def scene_one(draw, p):
    centered_text(draw, "UN MISTERIO POR RESOLVER", 65, 42, p)
    reveal_line(draw, [(300, 145), (980, 145)], p, 4)
    stick_figure(draw, 640, 220, p)
    # notebook / clue card
    reveal_line(draw, [(820, 390), (1060, 390), (1060, 570), (820, 570), (820, 390)], p, 5)
    reveal_line(draw, [(860, 435), (1010, 435)], p, 4)
    reveal_line(draw, [(860, 475), (990, 475)], p, 4)
    reveal_line(draw, [(860, 515), (1020, 515)], p, 4)
    if p > .65:
        draw.text((150, 470), "¿QUÉ OCURRIÓ?", fill=INK, font=font(34, True))


def scene_two(draw, p):
    centered_text(draw, "SIGUE LAS PISTAS", 65, 44, p)
    # map route
    reveal_line(draw, [(190, 260), (370, 205), (520, 290), (700, 225), (880, 310), (1080, 230)], p, 6)
    for cx, cy in [(190,260), (370,205), (520,290), (700,225), (880,310), (1080,230)]:
        if p > .18:
            r = int(15 * min(1, (p-.18)*5))
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=INK, width=5)
    # magnifying glass
    reveal_circle(draw, (485, 365, 655, 535), p, 9)
    reveal_line(draw, [(625, 505), (735, 615)], p, 13)
    if p > .7:
        draw.text((790, 470), "PISTA", fill=INK, font=font(38, True))
        reveal_line(draw, [(785, 525), (980, 525)], p, 4)


def scene_three(draw, p):
    centered_text(draw, "CONECTA LAS PRUEBAS", 65, 42, p)
    cards = [(120, 230, 360, 445), (520, 230, 760, 445), (920, 230, 1160, 445)]
    labels = ["FECHAS", "TESTIMONIOS", "DOCUMENTOS"]
    for (x1, y1, x2, y2), label in zip(cards, labels):
        reveal_line(draw, [(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)], p, 5)
        if p > .35:
            f = font(25, True)
            draw.text((x1+20, y1+82), label, fill=INK, font=f)
            reveal_line(draw, [(x1+22,y1+132),(x2-22,y1+132)], p, 3)
            reveal_line(draw, [(x1+22,y1+162),(x2-52,y1+162)], p, 3)
    reveal_line(draw, [(360,335),(520,335)], p, 5)
    reveal_line(draw, [(760,335),(920,335)], p, 5)
    # arrow heads
    if p > .6:
        for x in (520, 920):
            draw.polygon([(x,335),(x-18,323),(x-18,347)], fill=INK)
    if p > .82:
        centered_text(draw, "LA HISTORIA TOMA FORMA", 535, 32, p)


RENDERERS = [scene_one, scene_two, scene_three]


def render(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    total_frames = FPS * SCENE_SECONDS * SCENES
    for frame in range(total_frames):
        scene_index = min(frame // (FPS * SCENE_SECONDS), SCENES - 1)
        frame_in_scene = frame % (FPS * SCENE_SECONDS)
        progress = min(1.0, frame_in_scene / (FPS * 3.4))
        # Small breathing zoom is added later in the production renderer.
        image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
        draw = ImageDraw.Draw(image)
        RENDERERS[scene_index](draw, progress)
        # Subtle paper grain / border keeps the board from looking sterile.
        draw.rectangle((24, 24, WIDTH-24, HEIGHT-24), outline=(225, 223, 216), width=2)
        image.save(output_dir / f"frame_{frame:05d}.png", optimize=False)
    return total_frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="whiteboard_frames")
    args = parser.parse_args()
    count = render(Path(args.output_dir))
    print(f"Rendered {count} frames at {FPS} fps ({count/FPS:.1f} seconds).")


if __name__ == "__main__":
    main()
