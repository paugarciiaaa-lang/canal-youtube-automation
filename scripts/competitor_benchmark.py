#!/usr/bin/env python3
"""Public YouTube packaging benchmark. Does not claim private CTR or retention data."""
import argparse,json,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument("--topic",required=True); p.add_argument("--output",required=True,type=Path)
    a=p.parse_args(); query=f"ytsearch8:{a.topic} documentary mystery"
    try:
      raw=subprocess.check_output(["yt-dlp","--skip-download","--no-warnings","--dump-single-json",query],
                                   text=True,stderr=subprocess.STDOUT,timeout=150)
      data=json.loads(raw); entries=data.get("entries") or []
    except Exception as exc:
      report={"status":"unavailable","reason":f"{type(exc).__name__}: {str(exc)[:300]}",
              "limitations":["No se inventan resultados cuando YouTube no responde."]}
      a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
      print("Benchmark público no disponible; se continúa sin inventar datos."); return
    rows=[]
    for x in entries:
      if not x: continue
      rows.append({"title":x.get("title"),"channel":x.get("channel") or x.get("uploader"),
        "views":x.get("view_count"),"duration_seconds":x.get("duration"),
        "upload_date":x.get("upload_date"),"url":x.get("webpage_url") or x.get("url")})
    rows.sort(key=lambda x:x.get("views") or 0,reverse=True)
    counts=[x["views"] for x in rows if x.get("views") is not None]
    median=sorted(counts)[len(counts)//2] if counts else None
    report={"status":"ok" if rows else "no_results","query":query,"videos":rows[:8],
      "insights":{"sample_size":len(rows),"median_public_views":median,
      "note":"Solo metadatos públicos: títulos, canales, visualizaciones, duración y fecha. No se dispone de CTR, retención ni datos privados de vidIQ."},
      "limitations":["Los resultados dependen del idioma, fecha y ranking de búsqueda de YouTube.",
      "Las visualizaciones públicas no permiten deducir retención ni CTR.","El benchmark orienta el packaging; no copia guiones, miniaturas ni escenas."]}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(f"Benchmark público: {len(rows)} vídeos; sin datos privados de retención.")
if __name__=="__main__": main()
