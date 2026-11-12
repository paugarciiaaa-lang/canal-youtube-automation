#!/usr/bin/env python3
"""Caspitas 2.0: subtitle-led hybrid documentary visual pass.

Creates a storyboard and inserts short, clearly-labelled 2D explanatory cutaways
into an existing documentary. The original narration/audio track is preserved.
No historical facts, maps, documents or statistics are invented.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 24
BG = (13, 20, 31)
PANEL = (22, 33, 48)
INK = (238, 241, 245)
MUTED = (160, 174, 190)
AMBER = (235, 174, 74)
CYAN = (74, 190, 205)
RED = (214, 82, 76)
GREEN = (105, 177, 133)

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def ffprobe(path: Path) -> dict:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path)
    ], text=True)
    return json.loads(raw)

def stamp(value: str) -> float:
    h, m, rest = value.strip().replace(",", ".").split(":")
    s, ms = (rest.split(".") + ["0"])[:2]
    return int(h) * 3600 + int(m) * 60 + int(s) + float("0." + ms)

def read_srt(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        timing = next((x for x in lines if "-->" in x), None)
        if not timing:
            continue
        a, b = [x.strip().split()[0] for x in timing.split("-->", 1)]
        text = " ".join(lines[lines.index(timing)+1:]).strip()
        if text:
            cues.append({"start": stamp(a), "end": stamp(b), "text": text})
    if not cues:
        raise SystemExit("No se han podido leer subtítulos SRT.")
    return cues

def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(text: str, max_chars: int = 52) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:3]

def text_block(draw, xy, text, size=42, color=INK, max_chars=52, spacing=12):
    x, y = xy
    for line in wrap(text, max_chars):
        draw.text((x, y), line, font=font(size, True), fill=color)
        y += size + spacing
    return y

def base_frame(index: int, total: int) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # Cinematic gradient and subtle geometric texture.
    for y in range(H):
        k = y / H
        col = (int(10 + 9*k), int(17 + 14*k), int(28 + 18*k))
        d.line((0, y, W, y), fill=col)
    d.rectangle((58, 58, W-58, H-58), outline=(53, 69, 87), width=2)
    d.rectangle((58, 58, 78, H-58), fill=AMBER)
    d.text((112, 90), "CASPITAS  /  DOCUMENTAL", font=font(24, True), fill=MUTED)
    d.line((112, 138, W-112, 138), fill=(61, 78, 96), width=2)
    # Slow animated light sweep.
    x = int(120 + (W-240) * ((index / max(1,total-1)) * .65 + .15))
    d.ellipse((x-180, 170, x+180, 530), fill=(18, 34, 48))
    return im

def draw_stickman(d, t: float, x=1450, y=440, scale=1.0, pose="investigate"):
    bob = math.sin(t * math.tau) * 8
    x, y = int(x), int(y+bob)
    # Character shadow and legs.
    d.ellipse((x-130, y+430, x+150, y+480), fill=(7, 12, 19))
    stride = math.sin(t * math.tau) * 38
    d.line((x-28, y+285, x-75+stride, y+425), fill=(30, 39, 53), width=34)
    d.line((x+28, y+285, x+78-stride, y+425), fill=(30, 39, 53), width=34)
    d.line((x-75+stride, y+425, x-118+stride, y+438), fill=INK, width=20)
    d.line((x+78-stride, y+425, x+125-stride, y+438), fill=INK, width=20)
    # Coat torso, shirt and tie.
    d.rounded_rectangle((x-92, y+112, x+92, y+310), radius=42, fill=(47, 68, 91), outline=INK, width=7)
    d.polygon([(x-35,y+120),(x,y+168),(x+35,y+120),(x+20,y+285),(x-20,y+285)], fill=(220,226,231))
    d.polygon([(x-12,y+158),(x+12,y+158),(x+18,y+250),(x,y+275),(x-18,y+250)], fill=AMBER)
    # Head and hair.
    d.ellipse((x-82,y-55,x+82,y+110), fill=(211,164,127), outline=INK, width=8)
    d.pieslice((x-88,y-72,x+88,y+82), 180, 355, fill=(35,33,34), outline=INK, width=5)
    d.ellipse((x-35,y+18,x-19,y+34), fill=(25,29,34))
    d.ellipse((x+19,y+18,x+35,y+34), fill=(25,29,34))
    d.arc((x-24,y+35,x+24,y+72), 15, 160, fill=(92,45,42), width=5)
    # Animated arms; investigator points to the clue.
    if pose == "walk":
        arm1, arm2 = (x-135,y+185+int(stride*.4)), (x+135,y+185-int(stride*.4))
        hand1, hand2 = (x-178,y+270+int(stride*.4)), (x+178,y+260-int(stride*.4))
    else:
        arm1, arm2 = (x-135,y+190), (x+135,y+165)
        hand1, hand2 = (x-175,y+300), (x+220,y+75+int(18*math.sin(t*math.tau)))
    d.line((x-75,y+145,arm1[0],arm1[1],hand1[0],hand1[1]), fill=(211,164,127), width=27, joint="curve")
    d.line((x+75,y+145,arm2[0],arm2[1],hand2[0],hand2[1]), fill=(211,164,127), width=27, joint="curve")
    d.ellipse((hand1[0]-18,hand1[1]-18,hand1[0]+18,hand1[1]+18), fill=(211,164,127))
    d.ellipse((hand2[0]-18,hand2[1]-18,hand2[0]+18,hand2[1]+18), fill=(211,164,127))

def render_scene(scene: dict, folder: Path, seconds: float) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    total = int(FPS * seconds)
    kind, excerpt = scene["type"], scene["excerpt"]
    for i in range(total):
        t = i / max(1, total-1)
        im = base_frame(i, total)
        d = ImageDraw.Draw(im)
        # Scene heading and visual tag.
        d.rounded_rectangle((120, 205, 760, 275), radius=18, fill=(35, 51, 69), outline=(72, 93, 115), width=2)
        d.text((150, 222), scene["label"].upper(), font=font(28, True), fill=AMBER)
        if kind in ("stickman", "reconstruction"):
            d.text((135, 340), "RECREACIÓN 2D", font=font(25, True), fill=CYAN)
            d.text((135, 405), "Una representación visual,", font=font(34), fill=INK)
            d.text((135, 455), "no una imagen de archivo.", font=font(34), fill=INK)
            # Corridor / doorway environment.
            d.polygon([(1120,300),(1700,300),(1830,820),(990,820)], fill=(27,43,60), outline=(79,101,124))
            d.rectangle((1320,390,1600,820), fill=(15,26,39), outline=(117,137,154), width=8)
            d.ellipse((1535,590,1560,615), fill=AMBER)
            draw_stickman(d, t, x=1110+int(22*math.sin(t*math.tau)), y=365, scale=1, pose="walk" if kind=="reconstruction" else "investigate")
            if kind == "reconstruction":
                d.text((1370, 340), "SECUENCIA ILUSTRADA", font=font(24, True), fill=RED)
        elif kind == "map":
            d.text((140, 340), "ESQUEMA DE LOCALIZACIÓN", font=font(30, True), fill=CYAN)
            # Deliberately schematic: no invented borders or coordinates.
            d.rounded_rectangle((150, 410, 1710, 790), radius=34, fill=(20,37,54), outline=(76,103,128), width=4)
            for k in range(8):
                yy = 455 + k*42
                d.line((220, yy, 1630, yy), fill=(42,65,85), width=2)
            for k in range(11):
                xx = 250 + k*125
                d.line((xx, 440, xx-80, 760), fill=(42,65,85), width=2)
            px = int(520 + 700*t)
            py = int(590 + 22*math.sin(t*math.tau))
            d.line((420,650,px,py), fill=AMBER, width=12)
            d.ellipse((px-30,py-30,px+30,py+30), fill=RED, outline=INK, width=5)
            d.ellipse((px-12,py-12,px+12,py+12), fill=INK)
            text_block(d, (220, 835), excerpt, 30, INK, 72, 8)
            d.text((220, 965), "DIAGRAMA ORIENTATIVO · NO A ESCALA", font=font(22, True), fill=MUTED)
        elif kind == "timeline":
            d.text((145, 355), "CRONOLOGÍA", font=font(32, True), fill=CYAN)
            d.line((230, 590, 1660, 590), fill=(101,125,148), width=8)
            years = scene.get("years", [])
            if not years:
                years = ["ANTES", "DESPUÉS"]
            count = min(4, len(years))
            for j, year in enumerate(years[:count]):
                px = 280 + j * (1320 // max(1,count-1)) if count > 1 else 940
                pulse = int(20*abs(math.sin(t*math.tau+j)))
                d.ellipse((px-28-pulse//4,562-pulse//4,px+28+pulse//4,618+pulse//4), fill=AMBER, outline=INK, width=4)
                d.text((px-90, 485), year, font=font(34, True), fill=INK)
            text_block(d, (220, 720), excerpt, 32, INK, 70, 10)
        elif kind == "evidence":
            d.text((145, 350), "PISTA / CONTEXTO", font=font(30, True), fill=CYAN)
            d.rounded_rectangle((250, 420, 1640, 825), radius=12, fill=(225,222,209), outline=(75,70,62), width=5)
            d.rectangle((285,455,1605,505), fill=(44,53,63))
            d.text((320,466), "CASO · NOTA VISUAL", font=font(24, True), fill=(244,240,226))
            text_block(d, (330, 565), excerpt, 42, (37,43,49), 48, 18)
            d.text((330, 755), "RECREACIÓN GRÁFICA · NO ES UN DOCUMENTO ORIGINAL", font=font(21, True), fill=(142,55,48))
            d.line((1430, 535, 1550, 655), fill=RED, width=10)
            d.line((1550, 535, 1430, 655), fill=RED, width=10)
        else:  # motion graphics
            d.text((145, 350), "DATO DE LA NARRACIÓN", font=font(30, True), fill=CYAN)
            focus = scene.get("focus", "DETALLE")
            scale = 1 + .045*math.sin(t*math.tau)
            f = font(int(112*scale), True)
            box = d.textbbox((0,0), focus, font=f)
            d.text(((W-(box[2]-box[0]))//2, 460), focus, font=f, fill=AMBER)
            text_block(d, (250, 700), excerpt, 34, INK, 68, 10)
        # Captured narration excerpt is displayed verbatim, not presented as an external quote.
        d.rounded_rectangle((120, 900, W-120, 1010), radius=18, fill=(7,13,22), outline=(65,82,101), width=2)
        short = excerpt[:150] + ("…" if len(excerpt)>150 else "")
        text_block(d, (155, 925), short, 25, INK, 110, 5)
        im.save(folder / f"frame_{i:05d}.png")
    clip = folder.with_suffix(".mp4")
    run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(folder/"frame_%05d.png"),
         "-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",
         "-r",str(FPS),"-g",str(FPS*2),"-video_track_timescale","12288",str(clip)])
    return clip

def classify(text: str, index: int) -> tuple[str,str]:
    low = text.lower()
    if re.search(r"\b(19|20)\d{2}\b", text):
        return "timeline", "Cronología"
    if any(k in low for k in ("mapa","frontera","isla","montaña","bosque","estación","ciudad","pueblo","río","mar","carretera","país","kilómetros","kilómetro")):
        return "map", "Localización"
    if any(k in low for k in ("documento","carta","expediente","informe","prueba","huella","fotografía","evidencia","registro","archivo")):
        return "evidence", "Pista documental"
    if any(k in low for k in ("desapare","entró","salió","caminó","llegó","encontró","viajó","huyó","corría","condujo")):
        return "reconstruction", "Reconstrucción"
    if any(k in low for k in ("millones","por ciento","kilómetros","horas","días","metros","número","cifra")):
        return "motion", "Dato destacado"
    return ("stickman" if index % 2 == 0 else "motion"), ("Investigación" if index % 2 == 0 else "Detalle clave")

def plan(cues: list[dict], duration: float, interval: float, scene_seconds: float) -> list[dict]:
    scenes, cursor, index = [], max(18.0, interval*.65), 0
    while cursor + scene_seconds < duration - 8:
        nearby = [c for c in cues if c["end"] >= cursor and c["start"] <= cursor+scene_seconds+8]
        excerpt = " ".join(c["text"] for c in nearby)
        excerpt = re.sub(r"\s+", " ", excerpt).strip()
        if len(excerpt) > 260:
            excerpt = excerpt[:257].rsplit(" ",1)[0] + "…"
        if not excerpt:
            cursor += interval
            continue
        kind, label = classify(excerpt, index)
        years = list(dict.fromkeys(re.findall(r"\b(?:18|19|20)\d{2}\b", excerpt)))[:4]
        numbers = re.findall(r"\b\d+(?:[.,]\d+)?\s?(?:%|por ciento|km|kilómetros|horas|días|metros)?\b", excerpt, re.I)
        focus = (numbers[0].strip() if numbers else (years[0] if years else "CLAVE"))
        scenes.append({
            "index": index+1, "start": round(cursor,3), "duration": scene_seconds,
            "type": kind, "label": label, "excerpt": excerpt or "Fragmento de la narración",
            "years": years, "focus": focus,
            "reason": "Clasificación heurística a partir de palabras y fechas presentes en los subtítulos; revisar antes de usar como material factual."
        })
        cursor += interval
        index += 1
    return scenes

def encode_segment(source: Path, start: float, length: float, target: Path) -> None:
    if length <= 0.08:
        return
    run(["ffmpeg","-y","-loglevel","error","-ss",f"{start:.3f}","-i",str(source),"-t",f"{length:.3f}",
         "-an","-vf",f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
         "-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",
         "-g",str(FPS*2),"-video_track_timescale","12288",str(target)])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--srt", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--storyboard", required=True, type=Path)
    ap.add_argument("--interval", type=float, default=55.0)
    ap.add_argument("--scene-seconds", type=float, default=4.5)
    args = ap.parse_args()
    source, srt = args.video.resolve(), args.srt.resolve()
    if not source.is_file() or not srt.is_file():
        raise SystemExit("Falta el MP4 o el SRT de entrada.")
    meta = ffprobe(source)
    duration = float(meta["format"]["duration"])
    if not any(s.get("codec_type")=="audio" for s in meta.get("streams",[])):
        raise SystemExit("El vídeo original no contiene audio.")
    cues = read_srt(srt)
    scenes = plan(cues, duration, args.interval, args.scene_seconds)
    if len(scenes) < 3:
        raise SystemExit("No hay suficientes escenas/subtítulos para crear una prueba híbrida fiable.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.storyboard.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="caspitas_hybrid_") as tmp:
        tmpdir = Path(tmp)
        segments, cursor = [], 0.0
        for scene in scenes:
            start = scene["start"]
            if start > cursor:
                part = tmpdir / f"base_{len(segments):03d}.mp4"
                encode_segment(source, cursor, start-cursor, part)
                segments.append(part)
            folder = tmpdir / f"scene_{scene['index']:03d}"
            clip = render_scene(scene, folder, args.scene_seconds)
            segments.append(clip)
            cursor = start + args.scene_seconds
        if cursor < duration:
            part = tmpdir / f"base_{len(segments):03d}.mp4"
            encode_segment(source, cursor, duration-cursor, part)
            segments.append(part)
        listing = tmpdir / "concat.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
        silent = tmpdir / "hybrid_video_only.mp4"
        run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(listing),
             "-c","copy","-movflags","+faststart",str(silent)])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg","-y","-loglevel","error","-i",str(silent),"-i",str(source),
             "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","copy","-shortest",
             "-movflags","+faststart",str(args.output)])
    final_meta = ffprobe(args.output)
    final_duration = float(final_meta["format"]["duration"])
    drift = abs(final_duration-duration)
    if drift > 1.0:
        raise SystemExit(f"El montaje híbrido alteró la duración ({drift:.2f}s).")
    storyboard = {
        "version":"caspitas-hybrid-mvp-1",
        "source_video":source.name,
        "duration_seconds":round(duration,3),
        "final_duration_seconds":round(final_duration,3),
        "audio_preserved":True,
        "scene_count":len(scenes),
        "inserted_visual_seconds":round(sum(s["duration"] for s in scenes),3),
        "visual_mix_note":"El vídeo documental original conserva sus imágenes y vídeos de archivo entre las inserciones. Los mapas son esquemáticos y los documentos/reconstrucciones se rotulan como recreaciones.",
        "scenes":scenes
    }
    args.storyboard.write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:storyboard[k] for k in ("scene_count","inserted_visual_seconds","duration_seconds","final_duration_seconds")},ensure_ascii=False))

if __name__ == "__main__":
    main()
