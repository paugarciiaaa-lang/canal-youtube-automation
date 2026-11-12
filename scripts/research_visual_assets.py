#!/usr/bin/env python3
"""Find named places and archival candidates; retain attribution and licence metadata."""
import argparse,json,math,re,time,urllib.parse,urllib.request
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont

UA="CaspitasDocumentaryWorkflow/1.0 (documentary research; contact via repository)"
HEADERS={"User-Agent":UA}

def get_json(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())

def geocode(query):
    url="https://nominatim.openstreetmap.org/search?"+urllib.parse.urlencode({"q":query,"format":"jsonv2","limit":1,"addressdetails":1})
    data=get_json(url)
    if not data: return None
    x=data[0]
    return {"lat":float(x["lat"]),"lon":float(x["lon"]),"display_name":x.get("display_name",""),
            "osm_type":x.get("osm_type"),"osm_id":x.get("osm_id"),
            "source_url":"https://www.openstreetmap.org/"+str(x.get("osm_type","node"))+"/"+str(x.get("osm_id",""))}

def tile_xy(lat,lon,z):
    lat=max(-85.0511,min(85.0511,lat)); n=2**z
    x=(lon+180)/360*n; r=math.radians(lat)
    y=(1-math.asinh(math.tan(r))/math.pi)/2*n
    return x,y

def make_map(place,out):
    z=6 if abs(place["lat"])>50 else 7
    fx,fy=tile_xy(place["lat"],place["lon"],z); cx,cy=int(fx),int(fy)
    canvas=Image.new("RGB",(768,768),(235,235,229)); successful=0
    for dx in (-1,0,1):
      for dy in (-1,0,1):
        x,y=cx+dx,cy+dy
        url=f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        try:
          req=urllib.request.Request(url,headers=HEADERS)
          with urllib.request.urlopen(req,timeout=25) as r: tile=Image.open(BytesIO(r.read())).convert("RGB")
          canvas.paste(tile,((dx+1)*256,(dy+1)*256)); successful+=1
        except Exception: pass
        time.sleep(1.05)
    if successful<5: return None
    px=int((fx-(cx-1))*256); py=int((fy-(cy-1))*256)
    d=ImageDraw.Draw(canvas)
    d.ellipse((px-20,py-20,px+20,py+20),fill=(190,48,44),outline="white",width=6)
    d.ellipse((px-6,py-6,px+6,py+6),fill="white")
    try: f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    except Exception: f=ImageFont.load_default()
    d.rectangle((0,718,768,768),fill="white")
    d.text((12,722),place["display_name"][:80],fill=(28,38,48),font=f)
    d.text((12,745),"© OpenStreetMap contributors · ODbL · Mapa de localización",fill=(28,38,48),font=f)
    out.parent.mkdir(parents=True,exist_ok=True); canvas.save(out)
    return {"path":str(out),"asset_type":"verified_osm_map","attribution":"© OpenStreetMap contributors, ODbL",
            "source_url":place["source_url"],"verified_place":place["display_name"],
            "coordinates":[place["lat"],place["lon"]],"marker_xy":[px,py],"map_size":[768,768],
            "tiles_used":successful}

def clean_html(value):
    return re.sub(r"<[^>]+>","",value or "").strip()

def commons_candidate(query,out):
    params={"action":"query","format":"json","generator":"search","gsrsearch":query,"gsrnamespace":6,
            "gsrlimit":8,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1400}
    try: data=get_json("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(params))
    except Exception: return None
    pages=(data.get("query",{}).get("pages",{}) or {}).values()
    query_terms=[x for x in re.findall(r"[a-z0-9áéíóúüñ]+",query.casefold())
                 if len(x)>4 and x not in {"historical","documentary","archive","document","photo","photograph","newspaper","letter","image","scan"}]
    for page in pages:
      title_text=page.get("title","").casefold()
      matched=sum(1 for term in query_terms if term in title_text)
      if query_terms and matched < min(2,len(query_terms)): continue
      info=(page.get("imageinfo") or [{}])[0]; meta=info.get("extmetadata",{})
      license_name=clean_html((meta.get("LicenseShortName") or {}).get("value",""))
      low=license_name.lower()
      accepted=("cc0","public domain","cc by ","cc-by-","cc by-sa","cc-by-sa")
      if not any(low.startswith(prefix) for prefix in accepted): continue
      url=info.get("thumburl") or info.get("url")
      if not url: continue
      try:
        req=urllib.request.Request(url,headers=HEADERS)
        with urllib.request.urlopen(req,timeout=35) as r: raw=r.read()
        img=Image.open(BytesIO(raw)).convert("RGB")
        if img.width<500 or img.height<280: continue
        out.parent.mkdir(parents=True,exist_ok=True); img.save(out,quality=91)
        title=page.get("title","")
        return {"path":str(out),"asset_type":"wikimedia_commons_candidate",
          "title":title,"page_url":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_")),
          "image_url":url,"license":license_name,"artist":clean_html((meta.get("Artist") or {}).get("value",""))[:300],
          "credit":clean_html((meta.get("Credit") or {}).get("value",""))[:300],
          "attribution_required":not ("cc0" in low or "public domain" in low)}
      except Exception: continue
    return None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--storyboard",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    a=p.parse_args(); data=json.loads(a.storyboard.read_text(encoding="utf-8"))
    records=[]; map_count=0; image_count=0
    for scene in data.get("scenes",[]):
      asset=None
      if scene.get("type")=="map" and scene.get("location_query"):
        try:
          place=geocode(scene["location_query"])
          if place:
            core=scene["location_query"].split(",")[0].strip().casefold()
            tokens=[x for x in re.findall(r"[a-z0-9áéíóúüñ]+",core) if len(x)>2]
            display=place["display_name"].casefold()
            if not tokens or not all(token in display for token in tokens):
              asset={"status":"geocoding_name_mismatch","query":scene["location_query"],
                     "candidate":place["display_name"]}
            else:
              asset=make_map(place,a.output_dir/f"map_{scene['index']:02d}.png")
              if asset: map_count+=1
          else: asset={"status":"geocoding_no_match","query":scene["location_query"]}
        except Exception as exc: asset={"status":"map_unavailable","reason":type(exc).__name__}
      elif scene.get("type") in ("document","photo","parallax") and scene.get("document_search"):
        asset=commons_candidate(scene["document_search"],a.output_dir/f"commons_{scene['index']:02d}.jpg")
        if asset: image_count+=1
        else: asset={"status":"no_accepted_commons_result","query":scene["document_search"]}
      elif scene.get("type")=="photo" and scene.get("visual_search"):
        asset=commons_candidate(scene["visual_search"],a.output_dir/f"commons_{scene['index']:02d}.jpg")
        if asset: image_count+=1
        else: asset={"status":"no_accepted_commons_result","query":scene["visual_search"]}
      if asset:
        scene["asset"]=asset
        if asset.get("path"): scene["asset_path"]=asset["path"]
      records.append({"scene":scene.get("index"),"type":scene.get("type"),"asset":asset or {"status":"not_requested"}})
      time.sleep(1.05)
    manifest={"version":"visual-research-v1","maps_found":map_count,"licensed_commons_candidates":image_count,
      "assets":records,"policy":"Los mapas usan geocodificación Nominatim y mosaicos OSM con atribución. Las imágenes Commons solo se descargan cuando se identifica una licencia aceptada; la licencia y atribución se registran para revisión humana. Una coincidencia de búsqueda no demuestra por sí sola autenticidad histórica."}
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/"visual_asset_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    a.storyboard.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Recursos encontrados: {map_count} mapas OSM; {image_count} imágenes Commons con licencia identificada.")
if __name__=="__main__": main()
