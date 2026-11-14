#!/usr/bin/env python3
"""Caspitas 2.0: subtitle-led hybrid documentary visual pass.

Creates a storyboard and overlays short, clearly-labelled 2D explanatory scenes
onto the existing documentary. Original footage, narration and subtitle timing are preserved.
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
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode:
        raise SystemExit(proc.stderr[-6000:] or f"Comando fallido: {cmd[0]}")

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
    from PIL import ImageFont
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

def base_frame(index: int, total: int):
    from PIL import Image, ImageDraw
    # Transparent documentary overlay: preserve the original footage as the visual base.
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Compact editorial identifier only; do not cover the documentary frame with a giant card.
    d.rounded_rectangle((54, 48, 690, 126), radius=22,
                        fill=(5, 12, 22, 185), outline=(115, 142, 166, 220), width=2)
    d.rectangle((54, 48, 66, 126), fill=AMBER)
    d.text((92, 73), "CASPITAS  /  DOCUMENTAL", font=font(25, True), fill=INK)
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

def paste_layered_asset(im, scene, t, box):
    from PIL import Image, ImageOps, ImageFilter, ImageDraw
    path=scene.get("asset_path")
    if not path or not Path(path).is_file(): return False
    source=Image.open(path).convert("RGB")
    x0,y0,x1,y1=box; w,h=x1-x0,y1-y0
    background=ImageOps.fit(source,(w,h),method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(13))
    dx=int(math.sin(t*math.tau)*9)
    im.alpha_composite(background.convert("RGBA"),(x0+dx,y0))
    foreground=ImageOps.contain(source,(int(w*.82),int(h*.82)),method=Image.Resampling.LANCZOS)
    px=x0+(w-foreground.width)//2+int(math.sin(t*math.tau)*15)
    py=y0+(h-foreground.height)//2+int(math.sin(t*math.tau+.7)*7)
    shade=Image.new("RGBA",(foreground.width+26,foreground.height+26),(0,0,0,0))
    sd=ImageDraw.Draw(shade); sd.rounded_rectangle((8,8,foreground.width+18,foreground.height+18),radius=14,fill=(0,0,0,150))
    im.alpha_composite(shade,(px-13,py-13))
    im.alpha_composite(foreground.convert("RGBA"),(px,py))
    return True

def render_scene(scene: dict, folder: Path, seconds: float) -> Path:
    from PIL import Image, ImageDraw
    folder.mkdir(parents=True, exist_ok=True)
    total = FPS
    kind, excerpt = scene["type"], scene["excerpt"]
    for i in range(total):
        t=i/max(1,total-1)
        im=base_frame(i,total)
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((120,205,760,275),radius=18,fill=(35,51,69,255),outline=(72,93,115,255),width=2)
        d.text((150,222),scene["label"].upper(),font=font(28,True),fill=AMBER)
        attribution=(scene.get("asset") or {}).get("attribution") or (scene.get("asset") or {}).get("license") or ""
        if kind in ("stickman","reconstruction"):
            # Cinematic environmental reconstruction: no stick figures or generic mascot.
            d.text((135, 175), "RECREACIÓN ILUSTRATIVA", font=font(25,True), fill=AMBER)
            d.rounded_rectangle((120,235,1800,850), radius=28,
                                fill=(7,14,25,210), outline=(88,111,135,230), width=3)
            # Layered mountain / terrain silhouettes, built as scenery rather than a character card.
            d.polygon([(120,690),(360,455),(560,620),(820,365),(1080,650),(1330,430),(1600,665),(1800,520),(1800,850),(120,850)],
                      fill=(29,48,66,255))
            d.polygon([(120,760),(420,610),(680,735),(980,555),(1240,740),(1510,590),(1800,730),(1800,850),(120,850)],
                      fill=(14,31,47,255))
            # Small environmental props provide scale and a narrative clue.
            d.line((260,790,520,710,730,735,960,640,1180,675), fill=(190,157,105,255), width=10)
            d.polygon([(1330,690),(1435,565),(1540,690)], fill=(18,27,37,255), outline=AMBER)
            d.polygon([(1375,690),(1435,610),(1495,690)], fill=(38,55,68,255))
            d.rectangle((1390,690,1480,785), fill=(10,19,29,255), outline=(125,139,148,255), width=5)
            d.ellipse((1510,715,1560,765), fill=(255,190,86,90))
            d.ellipse((1522,727,1548,753), fill=AMBER)
            text_block(d,(170,285),excerpt,34,INK,66,12)
            d.text((170,800),"ESCENA RECONSTRUIDA · NO ES MATERIAL DE ARCHIVO",
                   font=font(20,True),fill=AMBER)
        elif kind=="map":
            # Full-frame sourced map treatment: avoid presenting a map as a small slide.
            has_asset=paste_layered_asset(im,scene,t,(0,0,W,H))
            d=ImageDraw.Draw(im)
            d.rectangle((0,0,W,190),fill=(4,10,18,205))
            d.rectangle((0,900,W,H),fill=(4,10,18,185))
            d.text((125,205),"LOCALIZACIÓN · CARTOGRAFÍA ATRIBUIDA",font=font(28,True),fill=CYAN)
            if has_asset:
                d.text((125,875),("FUENTE: "+attribution)[:130],font=font(18,True),fill=INK)
            else:
                d.rounded_rectangle((280,390,1640,730),radius=28,fill=(9,20,32,220),outline=RED,width=4)
                d.text((365,465),"MAPA NO VERIFICADO",font=font(48,True),fill=RED)
                text_block(d,(365,565),"No se dibuja una ubicación ni una ruta sin fuente confirmada.",34,INK,60,12)
        elif kind=="timeline":
            d.text((145,355),"CRONOLOGÍA · FECHAS DEL RELATO",font=font(32,True),fill=CYAN)
            d.line((230,590,1660,590),fill=(101,125,148,255),width=8)
            years=scene.get("years",[]) or ["FECHA NO INDICADA"]
            count=min(4,len(years))
            for j,year in enumerate(years[:count]):
                px=280+j*(1320//max(1,count-1)) if count>1 else 940
                pulse=int(20*abs(math.sin(t*math.tau+j)))
                d.ellipse((px-28-pulse//4,562-pulse//4,px+28+pulse//4,618+pulse//4),fill=AMBER,outline=INK,width=4)
                d.text((px-90,485),year,font=font(34,True),fill=INK)
            text_block(d,(220,720),excerpt,32,INK,70,10)
        elif kind=="evidence":
            has_asset=paste_layered_asset(im,scene,t,(0,0,W,H))
            d=ImageDraw.Draw(im)
            d.rectangle((0,0,W,190),fill=(4,10,18,210))
            d.rectangle((0,900,W,H),fill=(4,10,18,190))
            d.text((125,205),"DOCUMENTO / PISTA",font=font(30,True),fill=CYAN)
            if has_asset:
                d.text((125,875),("FUENTE: "+attribution)[:130],font=font(18,True),fill=INK)
                d.text((125,925),"Autenticidad y contexto pendientes de revisión editorial.",font=font(18,True),fill=AMBER)
            else:
                d.rounded_rectangle((300,330,1620,790),radius=12,fill=(225,222,209,255),outline=(75,70,62,255),width=5)
                d.rectangle((335,365,1585,425),fill=(44,53,63,255))
                d.text((370,382),"RECREACIÓN GRÁFICA · NO ES ORIGINAL",font=font(24,True),fill=(244,240,226))
                text_block(d,(390,500),excerpt,42,(37,43,49),48,18)
                d.text((390,720),"ILUSTRACIÓN DEL CONTENIDO NARRADO",font=font(21,True),fill=(142,55,48))
        elif kind in ("photo","parallax"):
            has_asset=paste_layered_asset(im,scene,t,(0,0,W,H))
            d=ImageDraw.Draw(im)
            d.rectangle((0,0,W,190),fill=(4,10,18,205))
            d.rectangle((0,900,W,H),fill=(4,10,18,190))
            d.text((125,205),"IMAGEN DOCUMENTAL",font=font(30,True),fill=CYAN)
            if has_asset:
                d.text((125,875),("FUENTE: "+attribution)[:130],font=font(18,True),fill=INK)
                d.text((125,925),"Movimiento 2.5D sutil por capas; no altera el contenido del recurso.",font=font(18),fill=AMBER)
            else:
                d.text((220,500),"RECURSO VISUAL NO ENCONTRADO",font=font(40,True),fill=RED)
                text_block(d,(220,600),excerpt,32,INK,70,10)
        else:
            d.text((145,350),"DATO / IDEA DE LA NARRACIÓN",font=font(30,True),fill=CYAN)
            focus=scene.get("focus","DETALLE")[:18] or "DETALLE"
            scale=1+.045*math.sin(t*math.tau)
            fnt=font(int(112*scale),True)
            box=d.textbbox((0,0),focus,font=fnt)
            d.text(((W-(box[2]-box[0]))//2,460),focus,font=fnt,fill=AMBER)
            text_block(d,(250,700),excerpt,34,INK,68,10)
        im.resize((W//2,H//2),Image.Resampling.LANCZOS).save(folder/f"frame_{i:05d}.png")
    clip=folder.with_suffix(".mov")
    run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(folder/"frame_%05d.png"),
         "-c:v","qtrle","-pix_fmt","argb","-an","-video_track_timescale","12288",str(clip)])
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
    return ("photo" if index % 2 == 0 else "motion"), ("Contexto visual" if index % 2 == 0 else "Detalle clave")

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



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--srt", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--storyboard", required=True, type=Path)
    ap.add_argument("--interval", type=float, default=55.0)
    ap.add_argument("--scene-seconds", type=float, default=4.5)
    ap.add_argument("--plan", type=Path, default=None)
    args = ap.parse_args()
    source, srt = args.video.resolve(), args.srt.resolve()
    if not source.is_file() or not srt.is_file():
        raise SystemExit("Falta el MP4 o el SRT de entrada.")
    meta = ffprobe(source)
    duration = float(meta["format"]["duration"])
    if not any(s.get("codec_type")=="audio" for s in meta.get("streams",[])):
        raise SystemExit("El vídeo original no contiene audio.")
    cues = read_srt(srt)
    if args.plan and args.plan.is_file():
        semantic=json.loads(args.plan.read_text(encoding="utf-8"))
        type_map={"photo":"photo","map":"map","document":"evidence","reconstruction":"reconstruction",
                  "stickman":"reconstruction","timeline":"timeline","motion_graphic":"motion","parallax":"parallax"}
        scenes=[]
        for item in semantic.get("scenes",[]):
            kind=type_map.get(item.get("type"))
            if not kind: continue
            start=max(0.0,float(item.get("start",0)))
            length=min(float(item.get("duration",args.scene_seconds)),args.scene_seconds+1)
            if start+length>=duration-3: continue
            scenes.append({**item,"type":kind,"start":round(start,3),"duration":round(length,3),
                           "label":item.get("label") or "Contexto",
                           "excerpt":item.get("excerpt") or "Fragmento del relato",
                           "years":item.get("years",[]),"focus":item.get("focus","")})
        scenes.sort(key=lambda x:x["start"])
        # Avoid visual overlays colliding with each other.
        spaced=[]
        for scene in scenes:
            if spaced and scene["start"] < spaced[-1]["start"]+spaced[-1]["duration"]+2: continue
            spaced.append(scene)
        scenes=spaced
        planner="semantic"
    else:
        scenes=plan(cues,duration,args.interval,args.scene_seconds)
        planner="heuristic_fallback"
    if len(scenes) < 3:
        raise SystemExit("No hay suficientes escenas/subtítulos para crear una prueba híbrida fiable.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.storyboard.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="caspitas_hybrid_") as tmp:
        tmpdir = Path(tmp)
        clips = []
        for scene in scenes:
            folder = tmpdir / f"scene_{scene['index']:03d}"
            clips.append(render_scene(scene, folder, args.scene_seconds))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source)]
        for clip in clips:
            cmd.extend(["-stream_loop", "-1", "-i", str(clip)])
        filters = []
        previous = "0:v"
        for i, scene in enumerate(scenes):
            start = scene["start"]
            end = start + scene["duration"]
            filters.append(
                f"[{i+1}:v]trim=duration={scene['duration']:.3f},"
                f"setpts=PTS-STARTPTS+{start:.3f}/TB,scale={W}:{H}:flags=lanczos,"
                f"format=rgba[ov{i}]"
            )
            filters.append(
                f"[{previous}][ov{i}]overlay=0:0:format=auto:eof_action=pass:repeatlast=0:"
                f"enable='between(t,{start:.3f},{end:.3f})'[v{i}]"
            )
            previous = f"v{i}"
        cmd.extend([
            "-filter_complex", ";".join(filters),
            "-map", f"[{previous}]", "-map", "0:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest",
            "-movflags", "+faststart", str(args.output)
        ])
        run(cmd)
    final_meta = ffprobe(args.output)
    final_duration = float(final_meta["format"]["duration"])
    drift = abs(final_duration-duration)
    if drift > 1.0:
        raise SystemExit(f"El montaje híbrido alteró la duración ({drift:.2f}s).")
    storyboard = {
        "version":"caspitas-hybrid-mvp-3",
        "planner":planner,
        "source_video":source.name,
        "duration_seconds":round(duration,3),
        "final_duration_seconds":round(final_duration,3),
        "audio_preserved":True,
        "subtitle_timing_preserved":True,
        "scene_count":len(scenes),
        "inserted_visual_seconds":round(sum(s["duration"] for s in scenes),3),
        "visual_mix_note":"El documental original permanece como base. El storyboard semántico selecciona escenas por contexto; mapas y archivos solo se insertan si el paso de investigación encuentra una fuente y licencia registradas. Las escenas sin recurso verificado se marcan como recreación o recurso no encontrado.",
        "parallax_note":"El efecto 2.5D de esta versión es parallax por capas (fondo difuminado y capa frontal con desplazamiento independiente); no es estimación de profundidad neuronal.",
        "scenes":scenes
    }
    args.storyboard.write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:storyboard[k] for k in ("scene_count","inserted_visual_seconds","duration_seconds","final_duration_seconds")},ensure_ascii=False))



if __name__ == "__main__":
    main()
