#!/usr/bin/env python3
"""Generate Caspitas YouTube metadata and a documentary thumbnail from the video."""
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

# Documentary thumbnail: use an actual frame from the generated episode, never a stick figure or whiteboard drawing.
from PIL import Image, ImageDraw, ImageFont, ImageOps
W, H = 1280, 720
background = Path("output/thumbnail_background.jpg")
if background.exists():
    im = ImageOps.fit(Image.open(background).convert("RGB"), (W, H), method=Image.Resampling.LANCZOS)
else:
    im = Image.new("RGB", (W, H), (18, 25, 35))
# Darken the frame so the title remains readable.
overlay = Image.new("RGBA", (W, H), (5, 10, 18, 125))
im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
d = ImageDraw.Draw(im)
font_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
font_path = next((p for p in font_paths if Path(p).exists()), None)
def font(size):
    return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
headline = data["thumbnail_text"]
f = font(76)
while d.textbbox((0, 0), headline, font=f, stroke_width=3)[2] > 1120 and f.size > 38:
    f = font(f.size - 4)
# Keep the hook compact and visually dominant; no decorative characters or illustrations.
d.rounded_rectangle((48, 475, 1232, 672), radius=18, fill=(5, 10, 18), outline=(240, 190, 65), width=4)
d.text((82, 505), headline, font=f, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
d.text((84, 625), "CASPITAS  •  DOCUMENTAL", font=font(25), fill=(240, 205, 105))
im.save("output/thumbnail.png", quality=94)
print("Título, descripción, etiquetas y miniatura documental generados desde un fotograma real.")
