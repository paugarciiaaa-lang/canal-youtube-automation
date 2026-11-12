#!/usr/bin/env python3
"""Semantic storyboard planner for Caspitas 2.0 using the configured OpenRouter key."""
import argparse, json, os, re, urllib.request
from pathlib import Path

def read_srt(path):
    raw=path.read_text(encoding="utf-8-sig",errors="replace").replace("\r\n","\n")
    cues=[]
    def sec(v):
        h,m,tail=v.replace(",",".").split(":")
        return int(h)*3600+int(m)*60+float(tail)
    for block in re.split(r"\n\s*\n",raw.strip()):
        lines=[x.strip() for x in block.splitlines() if x.strip()]
        timing=next((x for x in lines if "-->" in x),None)
        if not timing: continue
        a,b=[x.strip().split()[0] for x in timing.split("-->",1)]
        body=" ".join(lines[lines.index(timing)+1:]).strip()
        if body: cues.append({"start":sec(a),"end":sec(b),"text":body})
    return cues

def extract_json(value):
    value=value.strip()
    ticks=chr(96)*3
    if value.startswith(ticks):
        value=value[3:]
        if value.lower().startswith("json"): value=value[4:]
        if ticks in value: value=value.rsplit(ticks,1)[0]
        value=value.strip()
    try: return json.loads(value)
    except json.JSONDecodeError:
        match=re.search(r"\{.*\}",value,re.S)
        if match: return json.loads(match.group(0))
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--srt",required=True,type=Path)
    p.add_argument("--topic",required=True)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--api-key",default=os.getenv("OPENROUTER_API_KEY",""))
    p.add_argument("--model",default="nvidia/nemotron-3-ultra-550b-a55b:free")
    p.add_argument("--benchmark",type=Path,default=None)
    a=p.parse_args()
    if not a.api_key: raise SystemExit("Falta OPENROUTER_API_KEY para el storyboard semántico.")
    cues=read_srt(a.srt)
    duration=cues[-1]["end"]
    windows=[]
    cursor=0.0
    while cursor<duration:
        group=[c for c in cues if c["end"]>cursor and c["start"]<cursor+48]
        txt=" ".join(c["text"] for c in group)
        if txt: windows.append({"start":round(cursor,2),"end":round(min(duration,cursor+48),2),"transcript":txt[:5200]})
        cursor+=48
    benchmark={}
    if a.benchmark and a.benchmark.is_file():
        try:
            raw_benchmark=json.loads(a.benchmark.read_text(encoding="utf-8"))
            benchmark={"status":raw_benchmark.get("status"),"videos":[
                {"title":x.get("title"),"channel":x.get("channel"),"views":x.get("views"),
                 "duration_seconds":x.get("duration_seconds"),"url":x.get("url")}
                for x in raw_benchmark.get("videos",[])[:8]]}
        except Exception: benchmark={"status":"unavailable"}
    brief={"topic":a.topic,"windows":windows,"public_competitor_benchmark":benchmark,
      "instructions":"Crea un storyboard documental semántico. Devuelve SOLO JSON con scenes. Cada escena: start,duration,type,label,excerpt,purpose,focus,years,location_query,document_search,visual_search,confidence,factual_basis. Tipos permitidos: photo,map,document,reconstruction,stickman,timeline,motion_graphic,parallax. Una escena útil por ventana como máximo. Usa el benchmark público solo para detectar enfoques de títulos, duración y presentación que merezcan diferenciarse; no copies títulos, miniaturas ni escenas. No deduzcas CTR ni retención. Usa únicamente datos explícitos de la transcripción. No inventes lugares, fechas, personas, citas, documentos, estadísticas, rutas ni fuentes. location_query solo si un lugar real aparece literalmente en el texto. document_search solo como consulta para buscar material; no afirmes que existe ni que es auténtico. factual_basis debe ser una frase textual de la transcripción. excerpt máximo 220 caracteres. Duración 4-6 segundos y dentro de la ventana. Alterna tipos visuales y evita Stickman constante. Devuelve JSON estricto."}
    prompt="Eres director documental e investigador visual. Diseña el storyboard solo con la transcripción proporcionada. "+json.dumps(brief,ensure_ascii=False)
    body=json.dumps({"model":a.model,"temperature":0.15,"max_tokens":6500,
      "messages":[{"role":"system","content":"Devuelve JSON estricto. No inventes hechos. Si no hay evidencia, deja campos vacíos."},
                  {"role":"user","content":prompt}]}).encode()
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=body,
      headers={"Authorization":"Bearer "+a.api_key,"Content-Type":"application/json",
      "HTTP-Referer":"https://github.com/paugarciiaaa-lang/canal-youtube-automation","X-Title":"Caspitas semantic storyboard"})
    with urllib.request.urlopen(req,timeout=150) as r: response=json.loads(r.read())
    parsed=extract_json(response["choices"][0]["message"]["content"])
    allowed={"photo","map","document","reconstruction","stickman","timeline","motion_graphic","parallax"}
    transcript_norm=re.sub(r"\s+"," "," ".join(c["text"] for c in cues)).casefold()
    scenes=[]
    for item in parsed.get("scenes",[]):
      try:
        typ=item.get("type","motion_graphic")
        if typ not in allowed: continue
        start=max(0,float(item.get("start",0)))
        window=next((w for w in windows if w["start"]<=start<w["end"]),None)
        if not window: continue
        length=min(6.0,max(4.0,float(item.get("duration",4.5))))
        length=min(length,window["end"]-start)
        excerpt=str(item.get("excerpt","")).strip()[:220]
        basis=str(item.get("factual_basis","")).strip()[:220]
        basis_norm=re.sub(r"\s+"," ",basis).casefold()
        if not basis_norm or basis_norm not in transcript_norm: continue
        excerpt_norm=re.sub(r"\s+"," ",excerpt).casefold()
        if not excerpt_norm or excerpt_norm not in transcript_norm: excerpt=basis
        location=str(item.get("location_query","")).strip()[:160]
        location_core=location.split(",")[0].strip()
        if location_core and location_core.casefold() not in transcript_norm: location=""
        confidence=max(0,min(1,float(item.get("confidence",0.5))))
        if length<3.5 or not excerpt or not basis or confidence<0.55: continue
        years=[str(x) for x in item.get("years",[])[:4] if re.fullmatch(r"(18|19|20)\d{2}",str(x))]
        scenes.append({"index":len(scenes)+1,"start":round(start,3),"duration":round(length,3),
          "type":typ,"label":str(item.get("label","Contexto"))[:60],"excerpt":excerpt,
          "purpose":str(item.get("purpose",""))[:240],"focus":str(item.get("focus",""))[:32],
          "years":[year for year in years if year in transcript_norm],"location_query":location,
          "document_search":str(item.get("document_search",""))[:180],
          "visual_search":str(item.get("visual_search",""))[:180],"confidence":confidence,
          "factual_basis":basis,"planner":"openrouter_semantic"})
      except (ValueError,TypeError): continue
    scenes.sort(key=lambda x:x["start"])
    chosen=[]
    for scene in scenes:
      if chosen and scene["start"]<chosen[-1]["start"]+chosen[-1]["duration"]+12: continue
      chosen.append(scene)
    if len(chosen)<3: raise SystemExit("Storyboard semántico insuficiente: menos de 3 escenas verificables. Se detiene sin fallback silencioso.")
    result={"version":"caspitas-semantic-storyboard-v1","planner":"OpenRouter LLM","model":a.model,
      "topic":a.topic,"transcript_windows":len(windows),"scene_count":len(chosen),"scenes":chosen,
      "limitations":["Lugares y documentos son candidatos, no hechos verificados.","La verificación de mapas y licencias se hace aparte.","No se dispone de métricas privadas de retención."]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Storyboard semántico: {len(chosen)} escenas; {len(windows)} fragmentos analizados.")
if __name__=="__main__": main()
