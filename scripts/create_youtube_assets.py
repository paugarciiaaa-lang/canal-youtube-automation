#!/usr/bin/env python3
"""Generate Caspitas YouTube metadata and a clean whiteboard thumbnail."""
from __future__ import annotations
import json
import os
import re
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

topic = Path("topic_subject.txt").read_text(encoding="utf-8").strip()
source_path = Path("output/script_source.txt")
source = source_path.read_text(encoding="utf-8", errors="ignore") if source_path.exists() else ""
source = re.sub(r"\[\d{2}:\d{2}(?::\d{2})?[,.]\d+\]", " ", source)
source = re.sub(r"<[^>]+>", " ", source)
source = re.sub(r"\s+", " ", source).strip()[:14000]

def fallback():
    return {
        "title": f"{topic}: el misterio que sigue sin resolverse"[:95],
        "description": (
            f"¿Qué ocurrió realmente en {topic}? En este documental de Caspitas "
            "repasamos el contexto, los hechos conocidos, las pistas y las principales "
            "explicaciones. Distinguimos los datos contrastados de las hipótesis y de "
            "aquello que todavía no se ha podido demostrar.\n\n"
            "¿Qué explicación te parece más convincente? Déjala en los comentarios.\n\n"
            "#Caspitas #Misterios #Documental"
        ),
        "tags": ["Caspitas", "misterios", "documental", "casos sin resolver", "investigación"],
        "thumbnail_text": "¿QUÉ OCURRIÓ?",
    }

data = fallback()
api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if api_key and source:
    prompt = f"""
Eres el editor SEO de un canal documental de YouTube en español de España llamado Caspitas.
Usa EXCLUSIVAMENTE los datos del guion. No inventes detalles ni prometas resolver lo que sigue abierto.
Devuelve SOLO un objeto JSON válido con estas claves:
- title: título atractivo y fiel al contenido, 45-75 caracteres si es posible, sin clickbait engañoso.
- description: descripción natural de 100-160 palabras, resumen concreto del caso, qué se analiza, llamada a comentar y 3 hashtags al final.
- tags: lista de 8-12 etiquetas breves y relevantes, sin #.
- thumbnail_text: gancho de 2-5 palabras, mayúsculas, legible en miniatura.
Tema: {topic}
Guion (extracto):
{source}
"""
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + api_key
        body = {"contents":[{"parts":[{"text":prompt}]}],
                "generationConfig":{"temperature":0.45,"responseMimeType":"application/json"}}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        candidate = payload["candidates"][0]["content"]["parts"][0]["text"]
        generated = json.loads(candidate)
        if isinstance(generated.get("title"), str) and isinstance(generated.get("description"), str):
            data.update(generated)
    except Exception as exc:
        print(f"AVISO: no se pudo generar metadata con Gemini; se usa la alternativa automática: {exc}")

data["title"] = re.sub(r"\s+", " ", str(data.get("title", topic))).strip()[:100]
data["description"] = str(data.get("description", fallback()["description"])).strip()
data["tags"] = [str(x).strip() for x in data.get("tags", fallback()["tags"]) if str(x).strip()][:15]
data["thumbnail_text"] = re.sub(r"\s+", " ", str(data.get("thumbnail_text", "¿QUÉ OCURRIÓ?"))).upper()[:45]
Path("output/metadata.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Whiteboard thumbnail: warm paper, marker lettering and a hand-drawn investigator.
W, H = 1280, 720
im = Image.new("RGB", (W, H), (250, 249, 245))
d = ImageDraw.Draw(im)
font_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
font_path = next((p for p in font_paths if Path(p).exists()), None)
def font(size):
    return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

d.rounded_rectangle((28, 28, W-28, H-28), radius=22, outline=(35,35,35), width=5)
d.line([(85, 130), (W-85, 130)], fill=(40,40,40), width=4)
headline = data["thumbnail_text"]
f = font(72)
# Fit the short hook across the left half.
while d.textbbox((0,0), headline, font=f)[2] > 790 and f.size > 38:
    f = font(f.size - 4)
d.multiline_text((90, 210), headline, font=f, fill=(20,20,20), spacing=18, stroke_width=1)
# Draw a simple hand-drawn stick investigator and a magnifying glass.
cx, cy = 1000, 330
d.ellipse((cx-42,cy-42,cx+42,cy+42), outline=(25,25,25), width=8)
d.line([(cx,cy+42),(cx,cy+205)], fill=(25,25,25), width=9)
d.line([(cx,cy+92),(cx-80,cy+145)], fill=(25,25,25), width=9)
d.line([(cx,cy+92),(cx+78,cy+145)], fill=(25,25,25), width=9)
d.line([(cx,cy+205),(cx-62,cy+280)], fill=(25,25,25), width=9)
d.line([(cx,cy+205),(cx+62,cy+280)], fill=(25,25,25), width=9)
d.ellipse((1080,175,1195,290), outline=(25,25,25), width=8)
d.line([(1178,275),(1225,322)], fill=(25,25,25), width=12)
d.text((1111,177), "?", font=font(78), fill=(25,25,25))
d.line([(90, 555), (690, 555), (710, 548)], fill=(25,25,25), width=7)
d.text((94, 590), "CASPITAS  •  DOCUMENTAL", font=font(25), fill=(80,80,80))
im.save("output/thumbnail.png")
print("Título, descripción, etiquetas y miniatura whiteboard generados.")
