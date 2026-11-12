#!/usr/bin/env python3
"""Build a script-aware hybrid visual storyboard and a safe 60-second preview."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

STYLES = [
    ("ARCHIVO DOCUMENTAL", "Fotografía / material de archivo", ["foto", "fotografía", "archivo", "periódico", "imagen", "documento"]),
    ("MAPA Y RECORRIDO", "Mapa / localización", ["mapa", "kilómetro", "km", "viajó", "recorrido", "ubicación", "frontera", "país", "ciudad"]),
    ("CRONOLOGÍA", "Línea temporal", ["año", "fecha", "día", "mes", "antes", "después", "década", "cronología"]),
    ("PISTAS Y PRUEBAS", "Documentos / evidencias", ["prueba", "evidencia", "carta", "informe", "huella", "maleta", "objeto", "testimonio"]),
    ("RECONSTRUCCIÓN 2D", "Escena ilustrada", ["entró", "caminó", "habitacion", "habitación", "noche", "bosque", "montaña", "tren", "casa"]),
    ("EXPLICACIÓN VISUAL", "Whiteboard / Stickman / infografía", ["significa", "explica", "por qué", "hipótesis", "teoría", "posible", "comparar"]),
]

def parse_srt(path: Path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", raw.strip())
    cues = []
    for block in blocks:
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        timing = next((x for x in lines if "-->" in x), None)
        if not timing:
            continue
        a, b = [x.strip().split()[0] for x in timing.split("-->")]
        def seconds(t):
            h, m, s = t.replace(",", ".").split(":")
            return int(h)*3600 + int(m)*60 + float(s)
        text = re.sub(r"<[^>]+>", "", " ".join(lines[lines.index(timing)+1:]))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            cues.append({"start": seconds(a), "end": seconds(b), "text": text})
    return cues

def pick_style(text, index):
    low = text.lower()
    scores = [sum(1 for word in words if word in low) for _, _, words in STYLES]
    best = max(range(len(scores)), key=lambda i: (scores[i], -((i-index) % len(STYLES))))
    if scores[best] == 0:
        best = index % len(STYLES)
    return best

def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines[:4]

def make_overlay(path, width, height, style_index, excerpt, number):
    im = Image.new("RGBA", (width, height), (0,0,0,0))
    d = ImageDraw.Draw(im)
    margin = max(28, int(width*0.035))
    panel_w = int(width*0.48)
    panel_h = int(height*0.53)
    x, y = margin, int(height*0.20)
    d.rounded_rectangle((x,y,x+panel_w,y+panel_h), radius=24, fill=(8,14,24,218), outline=(235,190,75,255), width=3)
    accent = (235,190,75,255)
    d.rounded_rectangle((x+25,y+24,x+205,y+68), radius=12, fill=(235,190,75,255))
    d.text((x+39,y+31), f"CASPITAS  /  {number:02d}", font=load_font(max(14,int(width*.012)),True), fill=(12,18,27,255))
    title, subtitle, _ = STYLES[style_index]
    d.text((x+30,y+100), title, font=load_font(max(22,int(width*.026)),True), fill=accent)
    d.text((x+30,y+155), subtitle, font=load_font(max(16,int(width*.016)),True), fill=(245,247,250,255))
    lines = wrap(d, excerpt, load_font(max(17,int(width*.017))), panel_w-65)
    for i,line in enumerate(lines):
        d.text((x+30,y+215+i*int(height*.045)), line, font=load_font(max(17,int(width*.017))), fill=(225,231,239,255))
    # Distinct simple motif for each visual language.
    cx, cy = x+panel_w-95, y+panel_h-82
    if style_index == 1:  # map route
        pts=[(cx-70,cy+20),(cx-28,cy-22),(cx+8,cy+8),(cx+62,cy-35)]
        d.line(pts, fill=accent, width=7)
        for px,py in pts: d.ellipse((px-8,py-8,px+8,py+8),fill=(250,250,245,255))
    elif style_index == 2:
        d.line((cx-70,cy,cx+70,cy),fill=accent,width=6)
        for px in (cx-60,cx,cx+60): d.ellipse((px-10,cy-10,px+10,cy+10),fill=accent)
    elif style_index == 3:
        d.rectangle((cx-55,cy-48,cx+55,cy+45),outline=accent,width=5)
        for yy in (cy-20,cy,cy+20): d.line((cx-35,yy,cx+35,yy),fill=(240,240,240,255),width=4)
    elif style_index == 4:
        d.ellipse((cx-42,cy-48,cx+42,cy+36),outline=accent,width=6)
        d.line((cx,cy+36,cx,cy+75),fill=accent,width=7)
        d.line((cx-38,cy+75,cx+38,cy+75),fill=accent,width=7)
    else:
        d.ellipse((cx-43,cy-43,cx+43,cy+43),outline=accent,width=6)
        d.line((cx-22,cy,cx-5,cy+20,cx+28,cy-22),fill=accent,width=7)
    im.save(path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--output-dir", default="output/hybrid")
    ap.add_argument("--preview-seconds", type=int, default=60)
    args=ap.parse_args()
    video, srt = Path(args.video), Path(args.srt)
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    if not video.exists() or not srt.exists():
        raise SystemExit("Falta el MP4 o el SRT para analizar el storyboard.")
    cues=parse_srt(srt)
    if not cues: raise SystemExit("No se encontraron subtítulos SRT válidos.")
    probe=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",str(video)],text=True)
    stream=json.loads(probe)["streams"][0]; width=int(stream["width"]); height=int(stream["height"])
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(video)],text=True).strip())
    preview=min(args.preview_seconds,duration)
    # Six varied treatments across the opening minute; choose a relevant subtitle near each beat.
    beats=min(6,max(1,int(preview//8)))
    scenes=[]
    for i in range(beats):
        start=preview*i/beats
        end=preview*(i+1)/beats
        cue=min(cues,key=lambda c:abs(c["start"]-(start+end)/2))
        style=pick_style(cue["text"],i)
        excerpt=cue["text"][:145]
        png=out/f"overlay_{i+1:02d}.png"
        make_overlay(png,width,height,style,excerpt,i+1)
        scenes.append({"scene":i+1,"start_seconds":round(start,2),"end_seconds":round(end,2),"visual_style":STYLES[style][0],"treatment":STYLES[style][1],"subtitle_excerpt":excerpt,"overlay":str(png)})
    storyboard={"project":"Caspitas","mode":"hybrid_documentary_preview","source_video":str(video),"preview_seconds":round(preview,2),"full_video_seconds":round(duration,2),"scenes":scenes,"notes":["Las tarjetas son tratamientos gráficos originales de prueba, no fotografías históricas verificadas.","Los mapas de esta prueba son esquemáticos; no representan geografía real.","La selección de recursos de archivo y sus licencias requieren revisión humana."]}
    (out/"storyboard.json").write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Keep original footage and audio; add short, restrained graphic overlays. Never replace the master.
    cmd=["ffmpeg","-y","-i",str(video),"-t",str(preview)]
    for scene in scenes:
        cmd += ["-loop","1","-framerate","1","-i",scene["overlay"]]
    filters=[]
    last="[0:v]"
    for idx,scene in enumerate(scenes, start=1):
        label=f"[v{idx}]"
        filters.append(f"{last}[{idx}:v]overlay=0:0:enable='between(t,{scene['start_seconds']},{scene['end_seconds']})'{label}")
        last=label
    cmd += ["-filter_complex",";".join(filters),"-map",last,"-map","0:a?","-t",str(preview),"-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",str(out/"hybrid-preview.mp4")]
    subprocess.run(cmd,check=True)
    (out/"README.txt").write_text("Vista previa híbrida de Caspitas. El vídeo original no se modifica. Revisa storyboard.json y hybrid-preview.mp4. Las tarjetas son gráficos ilustrativos, no pruebas ni mapas documentales reales.\n",encoding="utf-8")
    print(f"Storyboard: {len(scenes)} escenas | vista previa: {preview:.1f}s | resolución: {width}x{height}")

if __name__=="__main__": main()
