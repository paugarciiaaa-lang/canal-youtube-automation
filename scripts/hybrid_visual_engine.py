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
    # Transparent canvas: the source documentary footage remains visible behind
    # the explanatory card, and the lower subtitle-safe area stays unobstructed.
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((58, 58, W-58, 900), radius=34,
                        fill=(11, 18, 29, 185), outline=(82, 103, 126, 245), width=4)
    d.rectangle((58, 58, 78, 900), fill=AMBER)
    d.text((112, 90), "CASPITAS  /  DOCUMENTAL", font=font(24, True), fill=MUTED)
    d.line((112, 138, W-112, 138), fill=(72, 91, 112), width=2)
    # Animated accent sweep inside the card.
    x = int(140 + (W-280) * ((index / max(1,total-1)) * .65 + .15))
    d.ellipse((x-180, 170, x+180, 530), fill=(18, 34, 48, 205))
    return im

def draw_stickman(d, t: float, x=1450, y=440, scale=1.0, pose="investigate"):
    """Draw Caspitas' recurring 2D comic explorer (not a line stickman)."""
    s = scale
    def pt(px, py):
        return (int(x + px*s), int(y + py*s))
    ink=(12,17,24); skin=(225,190,157); coat=(42,57,72)
    coat_light=(75,91,105); pants=(46,61,78); pack=(91,76,54)
    bob=math.sin(t*math.tau)*7*s
    y0=y+bob
    x=int(x)
    # Ground shadow.
    d.ellipse((x-155*s,y0+430*s,x+155*s,y0+475*s),fill=(5,10,17))
    stride=math.sin(t*math.tau)*34*s
    # Boots and bent running legs.
    d.line((pt(-35,285),pt(-78+stride,405),pt(-120+stride,430)),fill=ink,width=max(5,int(35*s)),joint="curve")
    d.line((pt(35,285),pt(82-stride,390),pt(132-stride,412)),fill=ink,width=max(5,int(35*s)),joint="curve")
    d.line((pt(-120+stride,430),pt(-158+stride,430)),fill=(28,35,43),width=max(5,int(22*s)))
    d.line((pt(132-stride,412),pt(170-stride,416)),fill=(28,35,43),width=max(5,int(22*s)))
    # Backpack behind the shoulder, with visible straps and flap.
    d.rounded_rectangle((x+45*s,y0+88*s,x+170*s,y0+270*s),radius=int(28*s),fill=pack,outline=ink,width=max(4,int(8*s)))
    d.rounded_rectangle((x+58*s,y0+105*s,x+155*s,y0+160*s),radius=int(16*s),fill=(119,99,68),outline=ink,width=max(3,int(5*s)))
    d.line((pt(58,120),pt(15,180),pt(55,270)),fill=(20,28,37),width=max(4,int(15*s)))
    # Jacket torso with collar, pockets and zipper.
    d.polygon([pt(-78,112),pt(-48,82),pt(48,82),pt(86,125),pt(75,300),pt(-78,300),pt(-92,145)],fill=coat,outline=ink)
    d.line((pt(-78,112),pt(-48,82),pt(0,125),pt(48,82),pt(86,125)),fill=(126,137,142),width=max(3,int(7*s)))
    d.line((pt(0,126),pt(0,286)),fill=(15,23,31),width=max(2,int(5*s)))
    for px in (-52,32):
        d.rounded_rectangle((x+(px-22)*s,y0+188*s,x+(px+22)*s,y0+244*s),radius=int(8*s),fill=coat_light,outline=ink,width=max(2,int(4*s)))
    d.ellipse((x-8*s,y0+150*s,x+8*s,y0+166*s),fill=(225,181,80),outline=ink,width=max(1,int(2*s)))
    # Head, ears and expressive face.
    d.ellipse((x-78*s,y0-68*s,x+78*s,y0+105*s),fill=skin,outline=ink,width=max(4,int(8*s)))
    d.ellipse((x-91*s,y0+8*s,x-65*s,y0+48*s),fill=skin,outline=ink,width=max(2,int(5*s)))
    d.ellipse((x+65*s,y0+8*s,x+91*s,y0+48*s),fill=skin,outline=ink,width=max(2,int(5*s)))
    d.pieslice((x-88*s,y0-94*s,x+88*s,y0+55*s),180,360,fill=(36,39,41),outline=ink,width=max(3,int(6*s)))
    d.ellipse((x-98*s,y0+22*s,x+98*s,y0+44*s),fill=(45,48,48),outline=ink,width=max(3,int(6*s)))
    d.rounded_rectangle((x-49*s,y0-116*s,x+50*s,y0-79*s),radius=int(12*s),fill=(39,43,45),outline=ink,width=max(3,int(5*s)))
    # Eyes, eyebrows and mouth convey alert determination.
    d.ellipse((x-39*s,y0+12*s,x-17*s,y0+39*s),fill=(247,241,224),outline=ink,width=max(2,int(3*s)))
    d.ellipse((x+17*s,y0+12*s,x+39*s,y0+39*s),fill=(247,241,224),outline=ink,width=max(2,int(3*s)))
    d.ellipse((x-29*s,y0+19*s,x-18*s,y0+34*s),fill=ink)
    d.ellipse((x+18*s,y0+19*s,x+29*s,y0+34*s),fill=ink)
    d.line((pt(-43,7),pt(-15,1)),fill=ink,width=max(2,int(6*s)))
    d.line((pt(15,1),pt(43,7)),fill=ink,width=max(2,int(6*s)))
    d.arc((x-22*s,y0+42*s,x+22*s,y0+78*s),5,165,fill=(94,48,43),width=max(2,int(5*s)))
    # Arms: a running swing or an investigator pointing at a clue.
    if pose=="walk":
        a1=pt(-112,160+stride*.25); h1=pt(-154,238+stride*.25)
        a2=pt(112,155-stride*.25); h2=pt(158,225-stride*.25)
    else:
        a1=pt(-120,155); h1=pt(-160,248)
        a2=pt(118,145); h2=pt(205,65+18*math.sin(t*math.tau))
    d.line((pt(-65,125),a1,h1),fill=ink,width=max(5,int(34*s)),joint="curve")
    d.line((pt(-65,125),a1,h1),fill=coat,width=max(4,int(25*s)),joint="curve")
    d.line((pt(65,125),a2,h2),fill=ink,width=max(5,int(34*s)),joint="curve")
    d.line((pt(65,125),a2,h2),fill=coat,width=max(4,int(25*s)),joint="curve")
    for hx,hy in (h1,h2):
        d.ellipse((hx[0]-16*s,hy[1]-16*s,hx[0]+16*s,hy[1]+16*s),fill=skin,outline=ink,width=max(2,int(4*s)))

def paste_layered_asset(im, scene, t, box):
    from PIL import Image, ImageOps, ImageFilter, ImageDraw
    path=scene.get("asset_path")
    if not path or not Path(path).is_file(): return False
    source=Image.open(path).convert("RGB")
    x0,y0,x1,y1=box; w,h=x1-x0,y1-y0
    # Two independent planes with a slow camera push: blurred environment and crisp foreground.
    zoom_bg=1.035+0.018*math.sin(t*math.pi)
    bw,bh=int(w*zoom_bg),int(h*zoom_bg)
    background=ImageOps.fit(source,(bw,bh),method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(13))
    bx=(background.width-w)//2+int(math.sin(t*math.tau)*7)
    by=(background.height-h)//2+int(math.cos(t*math.tau)*5)
    background=background.crop((bx,by,bx+w,by+h))
    im.alpha_composite(background.convert("RGBA"),(x0,y0))
    zoom_fg=1.0+0.045*t
    foreground=ImageOps.contain(source,(int(w*.82*zoom_fg),int(h*.82*zoom_fg)),method=Image.Resampling.LANCZOS)
    px=x0+(w-foreground.width)//2+int(math.sin(t*math.tau)*18)
    py=y0+(h-foreground.height)//2+int(math.sin(t*math.tau+.7)*9)
    shade=Image.new("RGBA",(foreground.width+26,foreground.height+26),(0,0,0,0))
    sd=ImageDraw.Draw(shade); sd.rounded_rectangle((8,8,foreground.width+18,foreground.height+18),radius=14,fill=(0,0,0,150))
    im.alpha_composite(shade,(px-13,py-13))
    im.alpha_composite(foreground.convert("RGBA"),(px,py))
    return True

def render_scene(scene: dict, folder: Path, seconds: float) -> Path:
    from PIL import Image, ImageDraw
    folder.mkdir(parents=True, exist_ok=True)
    # Render the full scene duration. The old one-second loop made every 4.5s scene visibly reset.
    total = max(2, int(math.ceil(seconds * FPS)))
    kind, excerpt = scene["type"], scene["excerpt"]
    for i in range(total):
        t=i/max(1,total-1)
        im=base_frame(i,total)
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((120,205,760,275),radius=18,fill=(35,51,69,255),outline=(72,93,115,255),width=2)
        d.text((150,222),scene["label"].upper(),font=font(28,True),fill=AMBER)
        attribution=(scene.get("asset") or {}).get("attribution") or (scene.get("asset") or {}).get("license") or ""
        if kind in ("stickman","reconstruction"):
            d.text((135,340),"RECREACIÓN 2D",font=font(25,True),fill=CYAN)
            d.text((135,405),"Representación visual,",font=font(34),fill=INK)
            d.text((135,455),"no imagen de archivo.",font=font(34),fill=INK)
            d.polygon([(1120,300),(1700,300),(1830,820),(990,820)],fill=(27,43,60,255),outline=(79,101,124,255))
            d.rectangle((1320,390,1600,820),fill=(15,26,39,255),outline=(117,137,154,255),width=8)
            d.ellipse((1535,590,1560,615),fill=AMBER)
            draw_stickman(d,t,x=1110+int(22*math.sin(t*math.tau)),y=365,scale=1,pose="walk" if kind=="reconstruction" else "investigate")
            if kind=="reconstruction": d.text((1370,340),"SECUENCIA ILUSTRADA",font=font(24,True),fill=RED)
            text_block(d,(140,650),excerpt,30,INK,48,8)
        elif kind=="map":
            d.text((140,340),"LOCALIZACIÓN CON FUENTE CARTOGRÁFICA",font=font(30,True),fill=CYAN)
            if paste_layered_asset(im,scene,t,(175,390,1745,805)):
                d=ImageDraw.Draw(im)
                # The geocoded point is supplied by the OSM research step; animate only
                # that verified point. No route is drawn unless the research data contains one.
                asset=scene.get("asset") or {}
                marker=asset.get("marker_xy")
                map_size=asset.get("map_size") or [768,768]
                if marker and len(marker)==2:
                    box=(175,390,1745,805)
                    mw,mh=box[2]-box[0],box[3]-box[1]
                    scale=min(mw/map_size[0],mh/map_size[1])
                    fw,fh=int(map_size[0]*scale),int(map_size[1]*scale)
                    ox=box[0]+(mw-fw)//2; oy=box[1]+(mh-fh)//2
                    mx=ox+int(marker[0]*scale); my=oy+int(marker[1]*scale)
                    pulse=1+0.22*(0.5+0.5*math.sin(t*math.tau))
                    radius=int(18*pulse)
                    d.ellipse((mx-radius,my-radius,mx+radius,my+radius),outline=AMBER,width=7)
                    d.ellipse((mx-7,my-7,mx+7,my+7),fill=RED,outline=INK,width=3)
                d.text((190,825),attribution[:115] or "Fuente cartográfica registrada en el manifiesto",font=font(18,True),fill=INK)
            else:
                d.rounded_rectangle((170,420,1745,790),radius=24,fill=(20,37,54,255),outline=RED,width=4)
                d.text((235,520),"MAPA NO VERIFICADO",font=font(42,True),fill=RED)
                d.text((235,600),"No se dibuja una ubicación inventada.",font=font(32),fill=INK)
                text_block(d,(235,680),excerpt,26,INK,75,8)
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
            d.text((145,350),"DOCUMENTO / PISTA",font=font(30,True),fill=CYAN)
            if paste_layered_asset(im,scene,t,(220,410,1660,820)):
                d=ImageDraw.Draw(im)
                d.text((225,835),("FUENTE: "+attribution)[:115],font=font(17,True),fill=INK)
                d.text((225,865),"Candidato de archivo; autenticidad pendiente de revisión editorial.",font=font(18,True),fill=AMBER)
            else:
                d.rounded_rectangle((250,420,1640,825),radius=12,fill=(225,222,209,255),outline=(75,70,62,255),width=5)
                d.rectangle((285,455,1605,505),fill=(44,53,63,255))
                d.text((320,466),"RECREACIÓN GRÁFICA · NO ES ORIGINAL",font=font(24,True),fill=(244,240,226))
                text_block(d,(330,565),excerpt,42,(37,43,49),48,18)
                d.text((330,755),"ILUSTRACIÓN DEL CONTENIDO NARRADO",font=font(21,True),fill=(142,55,48))
        elif kind in ("photo","parallax"):
            d.text((145,350),"IMAGEN DOCUMENTAL · MOVIMIENTO POR CAPAS",font=font(29,True),fill=CYAN)
            if paste_layered_asset(im,scene,t,(190,390,1720,815)):
                d=ImageDraw.Draw(im)
                d.text((195,830),("FUENTE: "+attribution)[:115],font=font(17,True),fill=INK)
                d.text((195,860),"Parallax 2.5D aproximado: fondo difuminado + capa frontal independiente.",font=font(18),fill=AMBER)
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
                  "stickman":"stickman","timeline":"timeline","motion_graphic":"motion","parallax":"parallax"}
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
        "parallax_note":"Parallax 2.5D por dos planos, zoom lento y desplazamientos independientes; no se presenta como profundidad neuronal.",
        "continuity_policy":{"recurring_character":"Caspitas explorer","character_design":"chaqueta azul gris, mochila marrón, gorro oscuro, rostro expresivo; proporciones y vestuario constantes","variation":"solo pose, encuadre y movimiento; sin rediseño entre escenas","scene_character_ids":[s.get("character_id") for s in scenes if s.get("type") in ("stickman","reconstruction")]},
        "scenes":scenes
    }
    args.storyboard.write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:storyboard[k] for k in ("scene_count","inserted_visual_seconds","duration_seconds","final_duration_seconds")},ensure_ascii=False))



if __name__ == "__main__":
    main()
