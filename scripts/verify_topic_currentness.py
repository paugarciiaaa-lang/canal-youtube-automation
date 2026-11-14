#!/usr/bin/env python3
"""Recomprueba la pista de actualidad antes de programar el documental."""
import json, sys, urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from daily_topic_factory import gdelt_items

path=Path("selected_topic.json")
if not path.exists():
    raise SystemExit("Falta selected_topic.json; no se puede comprobar la actualidad.")
item=json.loads(path.read_text(encoding="utf-8"))
kind=item.get("timeliness_type","evergreen")
if kind!="recent_update":
    print("Tema evergreen/manual: no depende de una noticia reciente.")
    sys.exit(0)
today=datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
links={x["url"] for x in gdelt_items()}
candidates=set(item.get("source_urls",[]))
valid=bool(links.intersection(candidates))
if valid:
    url=next(iter(links.intersection(candidates)))
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"CaspitasEditorialBot/1.0"})
        with urllib.request.urlopen(req,timeout=20) as response:
            valid=200 <= response.status < 400
    except Exception as exc:
        print(f"No se pudo reabrir la noticia: {exc}")
        valid=False
if not valid:
    item["timeliness_type"]="evergreen"
    item["timeliness_reason"]="La noticia ya no supera la comprobación previa a programación; se retira el enfoque de actualidad."
    item["checked_on"]=today
    path.write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("AVISO: se ha retirado la etiqueta de actualidad. El guion debe tratar el caso como evergreen y verificar el estado con fuentes primarias.")
else:
    item["last_currentness_check"]=today
    path.write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("La pista de actualidad sigue apareciendo en el feed y el enlace responde. Esto NO sustituye la verificación de fuentes primarias.")
