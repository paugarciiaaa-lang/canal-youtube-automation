#!/usr/bin/env python3
"""Grounding and provenance gate for Caspitas' semantic visual storyboard."""
from __future__ import annotations
import argparse, json, re, unicodedata
from pathlib import Path

def norm(value: str) -> str:
    value=unicodedata.normalize("NFKD",str(value).casefold())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+"," ",value).strip()

def read_srt(path: Path) -> str:
    raw=path.read_text(encoding="utf-8-sig",errors="replace")
    blocks=re.split(r"\n\s*\n",raw.replace("\r\n","\n"))
    chunks=[]
    for block in blocks:
        lines=[x.strip() for x in block.splitlines() if x.strip()]
        timing=next((i for i,x in enumerate(lines) if "-->" in x),None)
        if timing is not None:
            chunks.extend(lines[timing+1:])
    return norm(" ".join(chunks))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--storyboard",required=True,type=Path)
    p.add_argument("--srt",required=True,type=Path)
    p.add_argument("--assets-manifest",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args()
    data=json.loads(a.storyboard.read_text(encoding="utf-8"))
    manifest=json.loads(a.assets_manifest.read_text(encoding="utf-8"))
    transcript=read_srt(a.srt)
    scenes=data.get("scenes",[])
    errors=[]; warnings=[]
    if len(scenes)<3: errors.append("Menos de tres escenas semánticas.")
    ids=set(); map_count=0; sourced_count=0
    for i,scene in enumerate(scenes,1):
        basis=norm(scene.get("factual_basis",""))
        if not basis or basis not in transcript:
            errors.append(f"Escena {i}: factual_basis no aparece literalmente en los subtítulos.")
        start=float(scene.get("start",0)); duration=float(scene.get("duration",0))
        if start<0 or duration<3.5 or duration>7:
            errors.append(f"Escena {i}: tiempo o duración fuera de límites.")
        location=norm(str(scene.get("location_query","")).split(",")[0])
        if location and location not in transcript:
            errors.append(f"Escena {i}: ubicación no está literalmente respaldada por el relato.")
        if scene.get("type")=="map":
            map_count+=1
            if not location:
                warnings.append(f"Escena {i}: mapa sin ubicación verificada; se mostrará como no verificado.")
        asset=scene.get("asset") or {}
        asset_path=scene.get("asset_path") or asset.get("path")
        if asset_path:
            path=Path(asset_path)
            if not path.is_file():
                errors.append(f"Escena {i}: recurso visual declarado pero no encontrado ({asset_path}).")
            license_name=str(asset.get("license","")).casefold()
            asset_type=asset.get("asset_type","")
            if asset_type=="verified_osm_map":
                if "openstreetmap" not in str(asset.get("attribution","")).casefold() or not asset.get("source_url"):
                    errors.append(f"Escena {i}: mapa OSM sin atribución o URL de fuente.")
                else: sourced_count+=1
            elif asset_type=="wikimedia_commons_candidate":
                accepted=("cc0","public domain","cc by ","cc-by-","cc by-sa","cc-by-sa")
                if not any(license_name.startswith(x) for x in accepted):
                    errors.append(f"Escena {i}: licencia Commons no aceptada o no identificada.")
                elif not asset.get("page_url") or not asset.get("title"):
                    errors.append(f"Escena {i}: falta la procedencia de la imagen Commons.")
                else: sourced_count+=1
            else:
                errors.append(f"Escena {i}: recurso externo sin tipo de licencia/procedencia reconocible.")
        cid=scene.get("character_id")
        if scene.get("type") in ("stickman","reconstruction"):
            if cid!="caspitas_explorer_v1":
                errors.append(f"Escena {i}: falta el bloqueo de identidad del personaje recurrente.")
            ids.add(cid)
    if len(ids)>1: errors.append("Se detectaron varios IDs para el personaje recurrente.")
    report={
        "status":"failed" if errors else "passed",
        "scene_count":len(scenes),
        "map_scene_count":map_count,
        "licensed_or_attributed_assets":sourced_count,
        "recurring_character_ids":sorted(x for x in ids if x),
        "manifest_asset_count":len(manifest.get("assets",[])),
        "errors":errors,"warnings":warnings,
        "checks":["base factual literal en subtítulos","ubicaciones citadas literalmente","duración de escena","procedencia/licencia de cada recurso descargado","identidad recurrente del personaje"],
        "limitations":["La coincidencia textual no demuestra por sí sola que una afirmación sea verdadera.","La licencia identificada no sustituye la revisión de condiciones y atribución antes de publicar.","Los mapas solo muestran ubicaciones geocodificadas; no se dibujan rutas no verificadas."]
    }
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors: raise SystemExit("Control de storyboard/procedencia fallido; se bloquea el montaje.")
if __name__=="__main__": main()
