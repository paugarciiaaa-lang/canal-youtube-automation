#!/usr/bin/env python3
"""Semantic storyboard planner for Caspitas 2.0 using the configured OpenRouter key."""
import argparse, json, os, re, time, urllib.request
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
    if not isinstance(value,str) or not value.strip():
        raise ValueError("El proveedor devolvió message.content vacío o nulo.")
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

def normalize_evidence(value):
    import unicodedata
    value=unicodedata.normalize("NFKD",value.casefold())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+"," ",value).strip()

def transcript_grounded_scenes(cues, windows, existing):
    """Auditable fallback: scenes are built only from literal subtitle passages."""
    fallback=[]
    occupied=[(x["start"],x["start"]+x["duration"]) for x in existing]
    for window in windows:
        candidates=[x for x in cues if window["start"] <= x["start"] < window["end"]]
        if not candidates:
            continue
        midpoint=(window["start"]+window["end"])/2
        anchor=min(candidates,key=lambda x:abs(x["start"]-midpoint))
        start_index=cues.index(anchor)
        selected=[x for x in cues[start_index:] if x["start"] < min(window["end"],anchor["start"]+12)]
        excerpt=" ".join(x["text"] for x in selected).strip()
        if len(excerpt)<28:
            selected=[x for x in cues if window["start"] <= x["start"] < min(window["end"],anchor["start"]+18)]
            excerpt=" ".join(x["text"] for x in selected).strip()
        excerpt=re.sub(r"\s+"," ",excerpt).strip()[:220]
        if len(excerpt)<28:
            continue
        start=round(anchor["start"],3)
        if any(start < end+12 and start+4.5 > begin-12 for begin,end in occupied):
            continue
        if re.search(r"\b(18|19|20)\d{2}\b",excerpt):
            kind="timeline"
            years=re.findall(r"\b(?:18|19|20)\d{2}\b",excerpt)[:4]
            label="Fecha mencionada en el relato"
        elif re.search(r"\b(llego|llegó|entro|entró|salio|salió|camino|caminó|viajo|viajó|encontro|encontró|desaparecio|desapareció|cruzo|cruzó|huyo|huyó)\b",excerpt.casefold()):
            kind="stickman"
            years=[]
            label="Recreación ilustrativa"
        else:
            kind="motion_graphic"
            years=[]
            label="Idea del fragmento narrado"
        fallback.append({
            "index":0,"start":start,"duration":4.5,"type":kind,
            "label":label,"excerpt":excerpt,
            "purpose":"Apoyo visual construido a partir del subtítulo literal; no añade hechos externos.",
            "focus":"","years":years,"location_query":"",
            "document_search":"","visual_search":"","confidence":0.60,
            "factual_basis":excerpt,"planner":"transcript_grounded_fallback"
        })
        occupied.append((start,start+4.5))
    return fallback

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
      "instructions":"Crea un storyboard documental semántico. Devuelve SOLO JSON con scenes. Cada escena: start,duration,type,label,excerpt,purpose,focus,years,location_query,document_search,visual_search,confidence,factual_basis. Tipos permitidos: photo,map,document,reconstruction,stickman,timeline,motion_graphic,parallax. Una escena útil por ventana como máximo. Usa el benchmark público solo para detectar enfoques de títulos, duración y presentación que merezcan diferenciarse; no copies títulos, miniaturas ni escenas. No deduzcas CTR ni retención. Usa únicamente datos explícitos de la transcripción. No inventes lugares, fechas, personas, citas, documentos, estadísticas, rutas ni fuentes. location_query solo si un lugar real aparece literalmente en el texto. document_search solo como consulta para buscar material; no afirmes que existe ni que es auténtico. factual_basis debe ser una frase textual de la transcripción. excerpt máximo 220 caracteres. El campo start debe ser tiempo absoluto en segundos desde el inicio del vídeo, no relativo a la ventana. Duración 4-6 segundos y dentro de la ventana. Dirección artística Caspitas basada en las referencias del repositorio: ilustración 2D tipo cómic/storyboard, contornos negros definidos, personajes de cabeza redondeada y rasgos expresivos, ropa y accesorios reconocibles (sombrero, chaqueta, mochila cuando la escena lo requiera), fondos completos y cinematográficos, sombras suaves, tonos azules/grises para tensión y acentos cálidos. Nunca dibujes muñecos de palo de líneas básicas. Las secuencias de acción deben conservar el mismo personaje y vestuario entre escenas y variar poses/ángulos. Alterna viñetas/recreaciones ilustradas con fotos, mapas y documentos de archivo; evita Stickman constante. Devuelve JSON estricto."}
    prompt="Eres director documental e investigador visual. Diseña el storyboard solo con la transcripción proporcionada. "+json.dumps(brief,ensure_ascii=False)
    body=json.dumps({"model":a.model,"temperature":0.15,"max_tokens":6500,
      "messages":[{"role":"system","content":"Devuelve JSON estricto. No inventes hechos. Si no hay evidencia, deja campos vacíos."},
                  {"role":"user","content":prompt}]}).encode()
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=body,
      headers={"Authorization":"Bearer "+a.api_key,"Content-Type":"application/json",
      "HTTP-Referer":"https://github.com/paugarciiaaa-lang/canal-youtube-automation","X-Title":"Caspitas semantic storyboard"})
    parsed=None
    last_error=None
    # Algunos modelos/proveedores responden HTTP 200 pero dejan message.content en null.
    # Reintentar brevemente y, si persiste, continuar con el fallback literal de subtítulos.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=150) as r:
                response=json.loads(r.read().decode("utf-8"))
            choices=response.get("choices") or []
            message=(choices[0].get("message") or {}) if choices else {}
            content=message.get("content")
            if not isinstance(content,str) or not content.strip():
                finish_reason=choices[0].get("finish_reason","unknown") if choices else "no_choices"
                raise ValueError(
                    f"Respuesta sin contenido textual (finish_reason={finish_reason})."
                )
            parsed=extract_json(content)
            if not isinstance(parsed,dict) or not isinstance(parsed.get("scenes"),list):
                raise ValueError("La respuesta JSON no contiene una lista 'scenes'.")
            break
        except (ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
            last_error=str(exc)
            if attempt < 2:
                wait_seconds=2 ** attempt
                print(f"Respuesta semántica no utilizable (intento {attempt+1}/3): {last_error}. Reintentando en {wait_seconds}s.")
                time.sleep(wait_seconds)
    if parsed is None:
        print(
            "AVISO: el modelo no devolvió un storyboard válido tras 3 intentos. "
            "Se usará el fallback construido exclusivamente con subtítulos literales. "
            f"Último error: {last_error}"
        )
        parsed={"scenes":[],"fallback_reason":last_error}
    allowed={"photo","map","document","reconstruction","stickman","timeline","motion_graphic","parallax"}
    transcript_norm=re.sub(r"\s+"," "," ".join(c["text"] for c in cues)).casefold()
    transcript_evidence=normalize_evidence(transcript_norm)
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
        basis_norm=normalize_evidence(basis)
        if not basis_norm or basis_norm not in transcript_evidence: continue
        excerpt_norm=normalize_evidence(excerpt)
        if not excerpt_norm or excerpt_norm not in transcript_evidence: excerpt=basis
        location=str(item.get("location_query","")).strip()[:160]
        location_core=location.split(",")[0].strip()
        if location_core and location_core.casefold() not in transcript_norm: location=""
        document_search=str(item.get("document_search","")).strip()[:180]
        visual_search=str(item.get("visual_search","")).strip()[:180]
        def grounded_query(query):
            terms=[x for x in re.findall(r"[a-z0-9áéíóúüñ]+",query.casefold()) if len(x)>4 and x not in {"historical","documentary","archive","document","photo","photograph","newspaper","letter","image"}]
            return bool(terms) and any(term in transcript_norm for term in terms)
        if document_search and not grounded_query(document_search): document_search=""
        if visual_search and not grounded_query(visual_search): visual_search=""
        confidence=max(0,min(1,float(item.get("confidence",0.5))))
        if length<3.5 or not excerpt or not basis or confidence<0.55: continue
        years=[str(x) for x in item.get("years",[])[:4] if re.fullmatch(r"(18|19|20)\d{2}",str(x))]
        scenes.append({"index":len(scenes)+1,"start":round(start,3),"duration":round(length,3),
          "type":typ,"label":str(item.get("label","Contexto"))[:60],"excerpt":excerpt,
          "purpose":str(item.get("purpose",""))[:240],"focus":str(item.get("focus",""))[:32],
          "years":[year for year in years if year in transcript_norm],"location_query":location,
          "document_search":document_search,
          "visual_search":visual_search,"confidence":confidence,
          "factual_basis":basis,"planner":"openrouter_semantic"})
      except (ValueError,TypeError): continue
    scenes.sort(key=lambda x:x["start"])
    chosen=[]
    for scene in scenes:
      if chosen and scene["start"]<chosen[-1]["start"]+chosen[-1]["duration"]+12: continue
      chosen.append(scene)
    fallback_used=False
    if len(chosen)<3:
        fallback_used=True
        supplemental=transcript_grounded_scenes(cues,windows,chosen)
        chosen.extend(supplemental)
        chosen.sort(key=lambda x:x["start"])
        # Reindex and keep a conservative, non-overlapping visual cadence.
        spaced=[]
        for scene in chosen:
            if spaced and scene["start"] < spaced[-1]["start"]+spaced[-1]["duration"]+12:
                continue
            scene["index"]=len(spaced)+1
            spaced.append(scene)
        chosen=spaced
    if len(chosen)<3:
        raise SystemExit("Storyboard insuficiente: el modelo y los subtítulos no aportan 3 fragmentos visuales literales utilizables.")
    result={"version":"caspitas-semantic-storyboard-v2","planner":"OpenRouter LLM + subtítulos literales" if fallback_used else "OpenRouter LLM","model":a.model,
      "topic":a.topic,"transcript_windows":len(windows),"scene_count":len(chosen),"fallback_used":fallback_used,"scenes":chosen,
      "limitations":["Las escenas de respaldo se construyen con fragmentos literales de subtítulos; no añaden hechos externos.","Lugares y documentos son candidatos, no hechos verificados.","La verificación de mapas y licencias se hace aparte.","No se dispone de métricas privadas de retención."]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Storyboard semántico: {len(chosen)} escenas; {len(windows)} fragmentos analizados.")
if __name__=="__main__": main()
