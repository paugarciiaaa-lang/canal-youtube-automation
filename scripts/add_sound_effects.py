#!/usr/bin/env python3
"""Add original, procedurally synthesised, narration-safe sound effects to Caspitas."""
from __future__ import annotations
import argparse
import json
import math
import random
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

RATE = 48000
CHANNELS = 2

def synth(kind: str, path: Path, seed: int) -> float:
    rng = random.Random(seed)
    duration = {"whoosh": 1.15, "tick": 0.22, "paper": 0.75, "impact": 0.85}.get(kind, 0.5)
    count = int(RATE * duration)
    frames = bytearray()
    phase = 0.0
    for i in range(count):
        t = i / RATE
        p = i / max(1, count - 1)
        noise = rng.uniform(-1.0, 1.0)
        if kind == "whoosh":
            env = math.sin(math.pi * p) ** 1.5
            freq = 180 + 620 * p
            phase += 2 * math.pi * freq / RATE
            sample = (0.58 * noise + 0.42 * math.sin(phase)) * env
        elif kind == "tick":
            env = math.exp(-t * 24)
            phase += 2 * math.pi * 1450 / RATE
            sample = math.sin(phase) * env
        elif kind == "paper":
            env = math.sin(math.pi * p) ** 0.8
            sample = noise * env * (0.65 + 0.35 * math.sin(2 * math.pi * 9 * t))
        else:  # restrained cinematic low impact
            env = math.exp(-t * 5.8)
            phase += 2 * math.pi * (82 - 42 * p) / RATE
            sample = (0.78 * math.sin(phase) + 0.12 * noise) * env
        value = int(max(-1, min(1, sample * 0.42)) * 32767)
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
    mapping = {
        "map": "whoosh", "photo": "whoosh", "parallax": "whoosh",
        "timeline": "tick", "evidence": "paper",
        "reconstruction": "impact", "motion": "tick", "stickman": "paper",
    }
    cues = []
    last = -99.0
    for scene in scenes:
        start = max(0.0, float(scene.get("start", 0)))
        kind = mapping.get(scene.get("type"))
        if kind and start - last >= 9.0:
            cues.append((start, kind))
            last = start
        if len(cues) >= 45:
            break
    if not cues:
        raise SystemExit("El storyboard no contiene escenas adecuadas para efectos; no se genera una mezcla vacía.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="caspitas_sfx_") as tmp:
        tmpdir = Path(tmp)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(args.video)]
        filters = []
        for i, (start, kind) in enumerate(cues, start=1):
            wav = tmpdir / f"sfx_{i:02d}_{kind}.wav"
            synth(kind, wav, seed=20261112 + i)
            cmd.extend(["-i", str(wav)])
            delay = int(start * 1000)
            filters.append(
                f"[{i}:a]adelay={delay}|{delay},volume=0.16,"
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
    report = {
        "status": "passed",
        "sound_effect_count": len(cues),
        "types": {kind: sum(1 for _, k in cues if k == kind) for kind in sorted(set(k for _, k in cues))},
        "source": "procedural_synthesis",
        "external_audio_assets": 0,
        "voice_track_gain": 1.0,
        "effects_gain": 0.16,
        "note": "Efectos originales sintetizados por código; mezcla suave sobre la narración. Revisar auditivamente antes de publicar."
    }
    report_path = args.output.with_name("sfx_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
