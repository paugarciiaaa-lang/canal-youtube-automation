#!/usr/bin/env python3
"""Actualiza data/topic_history.json mediante la API de GitHub con control optimista de SHA.

Cada intento lee la versión remota más reciente y solo escribe si su SHA sigue vigente.
Así se evitan los rechazos non-fast-forward de git push y se preservan los IDs añadidos
por otras ejecuciones.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if len(sys.argv) != 2 or not sys.argv[1].strip():
    raise SystemExit("Uso: update_topic_history.py <topic_id>")

token = os.environ.get("GH_TOKEN")
repository = os.environ.get("GITHUB_REPOSITORY")
branch = os.environ.get("GITHUB_REF_NAME", "main")
if not token or not repository:
    raise SystemExit("Faltan GH_TOKEN o GITHUB_REPOSITORY.")

topic_id = sys.argv[1].strip()
all_topics = json.loads(Path("data/topics.json").read_text(encoding="utf-8"))
all_ids = {item["id"] for item in all_topics}
if topic_id not in all_ids:
    raise SystemExit(f"El topic_id {topic_id!r} no existe en data/topics.json.")

api = f"https://api.github.com/repos/{repository}/contents/data/topic_history.json"
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Caspitas-topic-history-updater",
}

def request(method, url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code in (409, 422):
            return exc.code, {"message": body}
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {body}") from exc

for attempt in range(1, 13):
    status, remote = request("GET", api + "?ref=" + branch)
    if status != 200:
        raise RuntimeError(f"No se pudo leer el historial remoto: HTTP {status}")

    current_sha = remote["sha"]
    current_text = base64.b64decode(remote["content"]).decode("utf-8")
    history = json.loads(current_text)
    used = list(dict.fromkeys(history.get("used_ids", [])))

    # Reinicia el ciclo solo cuando todos los temas del catálogo ya se usaron.
    if all_ids and all_ids.issubset(set(used)):
        used = []
    if topic_id not in used:
        used.append(topic_id)

    new_content = json.dumps({"used_ids": used}, ensure_ascii=False, indent=2) + "\n"
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("ascii")
    payload = {
        "message": f"Registrar tema de Caspitas: {topic_id}",
        "content": encoded,
        "sha": current_sha,
        "branch": branch,
    }
    put_status, result = request("PUT", api, payload)
    if put_status in (200, 201):
        print(f"Historial actualizado correctamente (intento {attempt}/12).")
        print(f"Temas registrados en el ciclo actual: {len(used)}")
        sys.exit(0)

    print(f"El historial cambió durante la escritura; releyendo (intento {attempt}/12).", flush=True)
    time.sleep(min(attempt, 4))

raise SystemExit("No se pudo actualizar el historial tras 12 conflictos consecutivos.")
