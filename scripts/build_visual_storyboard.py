#!/usr/bin/env python3
"""Build a conservative documentary storyboard from subtitle-timed narration."""
import argparse, json, re
from pathlib import Path

STOP={"el","la","los","las","un","una","unos","unas","de","del","al","en","por","para","con","sin","que","y","o","pero","cuando","como","durante","desde","hasta","sobre","tras","ante","entre","su","sus","se","fue","era","habia","había","tambien","también","este","esta","ese","esa","the","and","of","in","on","at","to","for"}
def sec(v):
    h,m,s=v.replace(",",".").split(":")
    return int(h)*3600+int(m)*60+float(s)
def read_srt(path):
    raw=path.read_text(encoding="utf-8-sig",errors="replace").replace("\r\n","\n")
    cues=[]
    for block in re.split(r"\n\s*\n",raw.strip()):
        lines=[x.strip() for x in block.splitlines() if x.strip()]
        timing=next((x for x in lines if "-->" in x),None)
        if not timing: continue
        a,b=[x.strip().split()[0] for x in timing.split("-->",1)]
        text=" ".join(lines[lines.index(timing)+1:]).strip()
        if text: cues.append({"start":sec(a),"end":sec(b),"text":text})
    return cues
def entities(text):
    # Keep explicit named entities, model numbers and proper-name phrases from
    # the narration. These are search leads only, never claims of authenticity.
    patterns=[
      r"\bD\.?\s*B\.?\s*Cooper\b",
      r"\b(?:Boeing|Douglas|Lockheed)\s+\d{2,4}\b",
      r"\b(?:Flight|Vuelo)\s+\d{2,4}\b",
      r"\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+){1,3}\b"
    ]
    found=[]
    for pattern in patterns:
        for value in re.findall(pattern,text,re.I if "Flight" in pattern else 0):
            value=re.sub(r"\s+"," ",value).strip(" .")
            words=value.casefold().split()
            if words and words[0] in STOP: value=" ".join(value.split()[1:])
            if len(value)>3 and value.casefold() not in {x.casefold() for x in found}:
                found.append(value)
    return found
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--srt",required=True,type=Path)
    p.add_argument("--topic",required=True)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--interval",type=float,default=36)
    p.add_argument("--scene-seconds",type=float,default=5)
    a=p.parse_args()
    cues=read_srt(a.srt)
    if not cues: raise SystemExit("No hay subtítulos para construir el storyboard.")
    duration=cues[-1]["end"]
    scenes=[]
    cursor=18.0
    while cursor+a.scene_seconds<duration-5:
        nearby=[x for x in cues if x["end"]>cursor-3 and x["start"]<cursor+a.scene_seconds+5]
        excerpt=re.sub(r"\s+"," "," ".join(x["text"] for x in nearby)).strip()[:260]
        if len(excerpt)<35:
            cursor+=a.interval
            continue
        names=entities(excerpt)
        years=list(dict.fromkeys(re.findall(r"\b(?:18|19|20)\d{2}\b",excerpt)))[:4]
        if years:
            kind,label="timeline","Cronología verificada en el relato"
        elif names:
            kind,label="photo","Imagen de contexto relacionada"
        elif re.search(r"\b(carta|nota|expediente|informe|documento|billetes|paracaídas|fotografía|registro)\b",excerpt,re.I):
            kind,label="document","Documento o pista mencionada"
        else:
            kind,label="motion_graphic","Concepto del fragmento"
        query=(names[len(scenes) % len(names)] if names else "")
        scenes.append({
          "index":len(scenes)+1,"start":round(cursor,3),"duration":a.scene_seconds,
          "type":kind,"label":label,"excerpt":excerpt[:220],
          "purpose":"Apoyo visual basado en el texto sincronizado; no añade hechos externos.",
          "focus":query[:32] or (years[0] if years else "CLAVE"),
          "years":years,"location_query":"",
          "document_search":query if kind=="document" else "",
          "visual_search":query if kind=="photo" else "",
          "confidence":0.72,"factual_basis":excerpt[:220],
          "planner":"subtitle_grounded_named_entities"
        })
        cursor+=a.interval
    if len(scenes)<3: raise SystemExit("No se han encontrado suficientes ventanas narrativas.")
    result={"version":"caspitas-storyboard-v1","planner":"reglas conservadoras + SRT","topic":a.topic,
      "duration_seconds":round(duration,3),"scene_count":len(scenes),"fallback_used":True,
      "scenes":scenes,
      "limitations":["Las búsquedas de imágenes son candidatos, no prueba de autenticidad histórica.",
      "Solo se aceptan recursos de Wikimedia Commons con licencia identificada.",
      "Las imágenes sin coincidencia/licencia aceptable se descartan."]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Storyboard documental: {len(scenes)} escenas; {sum(1 for x in scenes if x['visual_search'])} búsquedas de imágenes específicas.")
if __name__=="__main__": main()
