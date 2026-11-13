#!/usr/bin/env python3
"""Add varied, original, procedurally synthesised sound effects to Caspitas."""
from __future__ import annotations
import argparse
import json
import math
import random
import re
import struct
import subprocess
import tempfile
import unicodedata
import wave
from pathlib import Path

RATE = 48000
CHANNELS = 2
DURATIONS = {
    "whoosh": 1.05, "tick": 0.18, "paper": 0.78, "impact": 0.82,
    "radio": 0.95, "footsteps": 0.62, "camera": 0.34, "pulse": 0.55,
}

def synth(kind: str, path: Path, seed: int) -> float:
    rng = random.Random(seed)
    duration = DURATIONS[kind]
    count = int(RATE * duration)
    frames = bytearray()
    phase = 0.0
    for i in range(count):
        t = i / RATE
        p = i / max(1, count - 1)
        noise = rng.uniform(-1.0, 1.0)
        if kind == "whoosh":
            env = math.sin(math.pi * p) ** 1.5
            phase += 2 * math.pi * (170 + 580 * p) / RATE
            sample = (0.48 * noise + 0.52 * math.sin(phase)) * env
        elif kind == "tick":
            env = math.exp(-t * 28)
            phase += 2 * math.pi * 1250 / RATE
            sample = math.sin(phase) * env
        elif kind == "paper":
            env = math.sin(math.pi * p) ** 0.75
            sample = noise * env * (0.55 + 0.45 * math.sin(2 * math.pi * 11 * t))
        elif kind == "impact":
            env = math.exp(-t * 6.5)
            phase += 2 * math.pi * (78 - 38 * p) / RATE
            sample = (0.82 * math.sin(phase) + 0.10 * noise) * env
        elif kind == "radio":
            env = math.sin(math.pi * p) ** 0.65
            carrier = math.sin(2 * math.pi * (430 + 80 * math.sin(2 * math.pi * 7 * t)) * t)
            sample = (0.52 * noise + 0.28 * carrier) * env
        elif kind == "footsteps":
            # Two soft, separated low thuds rather than a loud cinematic hit.
            beat = math.exp(-((p - 0.22) / 0.09) ** 2) + 0.82 * math.exp(-((p - 0.72) / 0.10) ** 2)
            phase += 2 * math.pi * 92 / RATE
            sample = (0.72 * math.sin(phase) + 0.12 * noise) * beat
        elif kind == "camera":
            env = math.exp(-t * 18)
            phase += 2 * math.pi * (1900 - 700 * p) / RATE
            sample = (0.62 * math.sin(phase) + 0.18 * noise) * env
        else:  # soft investigative pulse
            env = math.sin(math.pi * p) ** 1.4
            phase += 2 * math.pi * (95 + 35 * math.sin(2 * math.pi * p)) / RATE
            sample = math.sin(phase) * env
        value = int(max(-1, min(1, sample * 0.34)) * 32767)
        frames.extend(struct.pack("<hh", value, value))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(CHANNELS)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(frames)
    return duration

def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise SystemExit(p.stderr[-5000:] or "Falló FFmpeg al mezclar los efectos.")

def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", " ", value)

def choose_effect(scene: dict, index: int) -> str | None:
    kind = str(scene.get("type", "")).casefold()
    text = normalized(" ".join(str(scene.get(k, "")) for k in ("label", "excerpt", "purpose", "focus")))
    if kind in ("map", "photo", "parallax"):
        return "whoosh"
    if kind in ("document", "evidence"):
        return "paper"
    if kind == "timeline":
        # Timelines are frequent in documentary storyboards; rotate restrained cues
        # so a chronology-heavy episode does not collapse into one repeated tick.
        return ("camera", "tick", "pulse")[index % 3]
    if kind in ("reconstruction", "stickman"):
        if any(x in text for x in ("camino", "corrio", "viajo", "entro", "salio", "huyo", "llego", "cruzo")):
            return "footsteps"
        return "impact"
    if kind in ("motion", "motion_graphic"):
        if any(x in text for x in ("radio", "senal", "transmision", "mensaje", "llamada", "frecuencia")):
            return "radio"
        if any(x in text for x in ("impacto", "choque", "explosion", "caida", "golpe")):
            return "impact"
        return "pulse" if index % 2 == 0 else "whoosh"
    return None

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--storyboard", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if not args.video.is_file() or not args.storyboard.is_file():
        raise SystemExit("Falta el vídeo híbrido o el storyboard.")
    data = json.loads(args.storyboard.read_text(encoding="utf-8"))
    scenes = sorted(data.get("scenes", []), key=lambda x: float(x.get("start", 0)))
    cues = []
    last = -99.0
    for index, scene in enumerate(scenes):
        start = max(0.0, float(scene.get("start", 0)))
        kind = choose_effect(scene, index)
        # A small breathing gap avoids a constant stream of sound effects.
        if kind and start - last >= 8.0:
            cues.append({"start": start, "kind": kind, "scene_type": scene.get("type", "unknown")})
            last = start
        if len(cues) >= 55:
            break
    if not cues:
        raise SystemExit("El storyboard no contiene escenas adecuadas para efectos; no se genera una mezcla vacía.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="caspitas_sfx_") as tmp:
        tmpdir = Path(tmp)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(args.video)]
        filters = []
        for i, cue in enumerate(cues, start=1):
            wav = tmpdir / f"sfx_{i:02d}_{cue['kind']}.wav"
            synth(cue["kind"], wav, seed=20261113 + i)
            cmd.extend(["-i", str(wav)])
            delay = int(cue["start"] * 1000)
            filters.append(
                f"[{i}:a]adelay={delay}|{delay},volume=0.12,"
                f"aresample={RATE}[s{i}]"
            )
        labels = "".join(f"[s{i}]" for i in range(1, len(cues)+1))
        filters.append(
            f"[0:a]aresample={RATE},volume=1.0[voice];"
            f"[voice]{labels}amix=inputs={len(cues)+1}:duration=first:"
            f"dropout_transition=0:normalize=0,alimiter=limit=0.96[aout]"
        )
        cmd.extend([
            "-filter_complex", ";".join(filters),
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map_metadata", "0", "-movflags", "+faststart", str(args.output)
        ])
        run(cmd)
    counts = {kind: sum(1 for cue in cues if cue["kind"] == kind)
              for kind in sorted({cue["kind"] for cue in cues})}
    report = {
        "status": "passed",
        "sound_effect_count": len(cues),
        "types": counts,
        "cue_details": cues,
        "source": "procedural_synthesis",
        "external_audio_assets": 0,
        "voice_track_gain": 1.0,
        "effects_gain": 0.12,
        "note": "Efectos originales variados y sintetizados por código; mezcla moderada. La escucha final sigue siendo necesaria."
    }
    report_path = args.output.with_name("sfx_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
