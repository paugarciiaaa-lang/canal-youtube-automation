#!/usr/bin/env python3
"""Create Caspitas YouTube metadata and a topic-specific whiteboard thumbnail."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

topic = Path("topic_subject.txt").read_text(encoding="utf-8").strip()
if not topic:
    raise SystemExit("No se ha encontrado el tema del vídeo.")

def clean(s: str) -> str:
    return re.sub(r"\\s+", " ", s).strip()

topic = clean(topic)
title = f"{topic}: el misterio que sigue sin resolverse"
if len(title) > 95:
    title = f"El misterio de {topic}"
description = (
    f"¿Qué ocurrió realmente en {topic}? En este documental de Caspitas repasamos "
    "el contexto del caso, los hechos conocidos, las pistas y las principales "
    "explicaciones que se han planteado.\n\n"
    "Separamos los datos contrastados de las hipótesis y de aquello que todavía "
    "no se ha podido demostrar.\n\n"
    "¿Qué explicación te parece más convincente? Déjala en los comentarios.\n\n"
    "#Caspitas #Misterios #Documental"
)
tags = ["Caspitas", "misterios", "documental", "casos sin resolver", "investigación", topic]
Path("output").mkdir(exist_ok=True)
Path("output/metadata.json").write_text(
    json.dumps({"title": title, "description": description, "tags": tags},
               ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

W, H = 1280, 720
im = Image.new("RGB", (W, H), (250, 249, 245))
d = ImageDraw.Draw(im)
font_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
font_path = next((p for p in font_paths if Path(p).exists()), None)
def font(size):
    return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

# Hand-drawn-style frame and underline
d.rounded_rectangle((28, 28, W-28, H-28), radius=22, outline=(35,35,35), width=5)
d.line([(90, 135), (W-90, 135)], fill=(40,40,40), width=4)
# Text occupies the left two-thirds; wrap safely.
words = title.upper().split()
lines, current = [], ""
f = font(62)
for word in words:
    trial = (current + " " + word).strip()
    if d.textbbox((0,0), trial, font=f)[2] > 760 and current:
        lines.append(current); current = word
    else:
        current = trial
if current: lines.append(current)
if len(lines) > 4:
    lines = lines[:3] + [" ".join(lines[3:])]
y = 190
for line in lines:
    d.text((92, y), line, font=f, fill=(25,25,25), stroke_width=1)
    y += 82
# Simple marker-style stick figure and magnifying glass on the right.
cx, cy = 1010, 330
d.ellipse((cx-45, cy-45, cx+45, cy+45), outline=(25,25,25), width=8)
d.line([(cx,cy+45),(cx,cy+205)], fill=(25,25,25), width=9)
d.line([(cx,cy+95),(cx-85,cy+145)], fill=(25,25,25), width=9)
d.line([(cx,cy+95),(cx+85,cy+145)], fill=(25,25,25), width=9)
d.line([(cx,cy+205),(cx-65,cy+285)], fill=(25,25,25), width=9)
d.line([(cx,cy+205),(cx+65,cy+285)], fill=(25,25,25), width=9)
# Question mark bubble
d.ellipse((1080, 185, 1190, 295), outline=(25,25,25), width=7)
qf = font(76)
d.text((1104, 190), "?", font=qf, fill=(25,25,25))
# Hand-drawn underline accents
d.line([(92, 555), (690, 555), (710, 548)], fill=(25,25,25), width=7)
d.text((94, 590), "CASPITAS  •  DOCUMENTAL", font=font(25), fill=(80,80,80))
Path("output/thumbnail.png").parent.mkdir(exist_ok=True)
im.save("output/thumbnail.png", quality=95)
print("Metadatos y miniatura whiteboard generados.")
