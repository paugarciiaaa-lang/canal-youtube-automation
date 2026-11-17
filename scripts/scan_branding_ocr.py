#!/usr/bin/env python3
"""OCR-scan a documentary MP4 for on-screen 'Documental Caspitas' title cards."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--width", type=int, default=960)
    args = parser.parse_args()
    if not args.video.is_file():
        raise SystemExit("No se encuentra el vídeo para analizar.")
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(args.video)
    ], text=True).strip())
    evidence = []
    with tempfile.TemporaryDirectory(prefix="caspitas-ocr-") as tmp:
        frames = Path(tmp)
        pattern = str(frames / "frame_%06d.jpg")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.video),
            "-vf", f"fps={args.fps},scale={args.width}:-2", "-q:v", "4", pattern
        ], check=True)
        for frame in sorted(frames.glob("frame_*.jpg")):
            index = int(frame.stem.split("_")[-1]) - 1
            timestamp = index / args.fps
            text = subprocess.run(
                ["tesseract", str(frame), "stdout", "--psm", "6"],
                check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            ).stdout.strip()
            normalized = normalize(text)
            if re.search(r"documental.{0,80}caspitas|caspitas.{0,80}documental", normalized):
                evidence.append({
                    "time_seconds": round(timestamp, 3),
                    "ocr_text": text[:500],
                    "normalized_text": normalized[:300]
                })
    result = {
        "video": args.video.name,
        "duration_seconds": round(duration, 3),
        "scan_fps": args.fps,
        "frames_with_brand_phrase": len(evidence),
        "evidence": evidence
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not evidence:
        raise SystemExit("OCR: no se ha localizado el rótulo 'Documental Caspitas'.")


if __name__ == "__main__":
    main()
