#!/usr/bin/env python3
"""Selecciona temas de Caspitas con contexto de actualidad y una cola persistente.

La actualidad se obtiene de GDELT (fuente de descubrimiento, nunca prueba). Un LLM
propone temas y explica la conexión temporal. Si falla la búsqueda o el modelo,
se usa la cola evergreen ya verificada, sin inventar noticias.
"""
import json, os, re, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ROOT / "data/topics.json"
HISTORY = ROOT / "data/topic_history.json"
QUEUE = ROOT / "data/topic_queue.json"
OUT = ROOT / "topic_subject.txt"
ID_OUT = ROOT / "selected_topic_id.txt"
LOCAL = datetime.now(ZoneInfo("Europe/Madrid"))
TODAY = LOCAL.date().isoformat()

def http_json(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode("utf-8"))

def gdelt_items():
    queries = ['mystery disappearance investigation discovered remains identified',
               'archaeology discovery unexplained historical mystery expedition']
    found, seen = [], set()
    for q in queries:
        params = urllib.parse.urlencode({"query": q, "mode":"ArtList", "format":"json",
            "maxrecords":"30", "sort":"DateDesc", "timespan":"7d"})
        try:
            payload = http_json("https://api.gdeltproject.org/api/v2/doc/doc?"+params)
            for a in payload.get("articles", []):
                url = a.get("url","")
                title = (a.get("title") or "").strip()
                if title and url and url not in seen:
                    seen.add(url)
                    found.append({"title":title[:300], "url":url,
                        "source":a.get("domain",""), "date":a.get("seendate","")})
        except Exception as e:
            print(f"GDELT discovery unavailable: {e}", file=sys.stderr)
    return found[:45]

def ask_model(prompt):
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        body = {"model": os.getenv("TOPIC_MODEL","openai/gpt-4o-mini"),
                "temperature":0.35, "messages":[{"role":"user","content":prompt}]}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(body).encode(), headers={"Authorization":"Bearer "+key,
            "Content-Type":"application/json","HTTP-Referer":"https://github.com",
            "X-Title":"Caspitas Topic Factory"})
        obj = http_json(req.full_url, dict(req.header_items()), req.data)
        return obj["choices"][0]["message"]["content"]
    key = os.getenv("GEMINI_API_KEY")
    if key:
        model = os.getenv("TOPIC_GEMINI_MODEL","gemini-2.5-flash")
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        obj=http_json(url, {"Content-Type":"application/json"},
            json.dumps({"contents":[{"parts":[{"text":prompt}]}],
                        "generationConfig":{"temperature":0.35,"responseMimeType":"application/json"}}).encode())
        return obj["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("No hay clave para generar temas nuevos")

def clean_json(raw):
    raw=re.sub(r"^\s*\x60\x60\x60(?:json)?|\x60\x60\x60\s*$","",raw.strip(),flags=re.I)
    return json.loads(raw)

def norm(s):
    return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()

def similar(a,b):
    aa,bb=norm(a),norm(b)
    if not aa or not bb: return False
    return SequenceMatcher(None,aa,bb).ratio() >= .76 or aa in bb or bb in aa

def main():
    topics=json.loads(TOPICS.read_text(encoding="utf-8"))
    history=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"used_ids":[]}
    queue=json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else {"items":[]}
    used=set(history.get("used_ids",[]))
    known={x["id"] for x in topics}
    pending=[x for x in queue.get("items",[]) if x.get("id") not in used and x.get("status","queued")=="queued"]
    news=gdelt_items()
    print(f"Fecha local: {TODAY}; noticias candidatas descubiertas: {len(news)}")
    # Revalida un tema de actualidad al día de la publicación: debe tener novedad reciente
    # y fuente de descubrimiento; el editor debe comprobar las fuentes primarias.
    fresh=[x for x in pending if x.get("timeliness_type")!="recent_update" or
           x.get("checked_on")==TODAY]
    if len(fresh)<15:
        prompt=f"""Eres editor documental de Caspitas, canal español sobre misterios reales, desapariciones,
enigmas históricos, arqueología, expediciones y sucesos documentados.
Fecha de publicación local: {TODAY} (Europe/Madrid).
Crea 20 ideas NUEVAS y no repetidas. Prioriza una noticia reciente o efeméride SOLO si los titulares
aportados permiten una conexión temporal real. GDELT es únicamente descubrimiento: no es prueba.
No afirmes que un caso está resuelto/abierto ni detalles que no aparezcan en fuentes. Si no hay
novedad sólida, usa temas evergreen y marca timeliness_type=evergreen. Nada de rumores virales,
conspiraciones como hechos ni especulación sobre personas vivas.
Ideas ya existentes/usadas: {json.dumps([x.get('video_subject') for x in topics],ensure_ascii=False)}
Temas pendientes: {json.dumps([x.get('title') for x in fresh],ensure_ascii=False)}
Titulares recientes para descubrir posibles líneas (no los trates como hechos verificados):
{json.dumps(news[:35],ensure_ascii=False)}
Devuelve SOLO JSON válido: {{"items":[{{"id":"slug_unico","video_subject":"Título documental claro",
"timeliness_type":"recent_update|anniversary|evergreen","timeliness_reason":"por qué encaja con la fecha; vacío si evergreen",
"research_leads":["consulta concreta 1","consulta concreta 2"],"source_urls":["URL exacta de noticia si procede"],
"checked_on":"{TODAY}","status":"queued"}}]}}.
No reutilices casos de la lista. Para actualidad, fecha y URL deben proceder de los titulares suministrados."""
        try:
            obj=clean_json(ask_model(prompt))
            for x in obj.get("items",[]):
                if not all(x.get(k) for k in ("id","video_subject")): continue
                if x["id"] in known or x["id"] in used: continue
                if any(similar(x["video_subject"], y["video_subject"]) for y in topics+fresh): continue
                x["status"]="queued"
                fresh.append(x); known.add(x["id"])
        except Exception as e:
            print(f"Generación de nuevas ideas no disponible; se usa cola existente: {e}",file=sys.stderr)
    if not fresh:
        # Evita reiniciar ciegamente el ciclo y repetir un tema; fallo seguro.
        raise SystemExit("No quedan temas válidos. La fábrica necesita nuevas ideas verificables.")
    # Actualidad tiene prioridad solo si se ha revisado hoy; el resto rota por cola.
    fresh.sort(key=lambda x:(0 if x.get("timeliness_type") in ("recent_update","anniversary") and x.get("checked_on")==TODAY else 1))
    selected=fresh[0]
    selected["status"]="selected"
    selected["selected_for_date"]=TODAY
    queue["items"]=fresh[1:]+[x for x in queue.get("items",[]) if x.get("id") not in {y.get("id") for y in fresh}]
    QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT.write_text(selected["video_subject"],encoding="utf-8")
    ID_OUT.write_text(selected["id"],encoding="utf-8")
    Path("selected_topic.json").write_text(json.dumps(selected,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Tema elegido:",selected["video_subject"])
    print("Tipo temporal:",selected.get("timeliness_type","evergreen"))
    print("Motivo:",selected.get("timeliness_reason",""))
    print("Ideas en reserva:",len(queue["items"]))

if __name__=="__main__": main()
