#!/usr/bin/env python3
"""Optional Gemini Omni cutaways for Caspitas; fail-open to the original video."""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote
import requests

API = "https://generativelanguage.googleapis.com/v1beta"
TEXT_MODEL = "gemini-3.8-flash"
VIDEO_MODEL = "gemini-omni-1.2-flash"
SCENES = 2
SECONDS = 6

def log(message):
    print(f"[google-ai-scenes] {message}", flush=True)

def interaction(key, payload, timeout=900):
    r = requests.post(API + "/interactions",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=payload, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini API HTTP {r.status_code}: {r.text[:1000]}")
    data = r.json()
    if data.get("status") == "failed":
        raise RuntimeError("Gemini interaction failed")
    return data

def model_text(data):
    for step in data.get("steps", []):
        if step.get("type") == "model_output":
            for part in step.get("content", []):
                if part.get("type") == "text":
                    return part.get("text", "")
    return data.get("output_text", "")

def scene_prompts(key, subject, script):
    prompt = (
        "Act as a documentary cinematographer. Based only on this episode subject "
        "and script, return ONLY JSON {\"scenes\":[\"...\",\"...\"]} with exactly "
        "two DISTINCT, specific prompts for separate 6-second, 16:9 photorealistic "
        "documentary B-roll shots. One continuous camera shot each; grounded in "
        "the script; visually rich, plausible and cinematic. No captions, readable "
        "text, logos, dialogue, narration, music, graphic violence or invented "
        "recognizable real people. Avoid generic stock footage and repeated scenes.\n"
        f"SUBJECT:\n{subject}\nSCRIPT:\n{script[:8000]}"
    )
    raw = model_text(interaction(key, {"model": TEXT_MODEL, "input": prompt}, 180)).strip()
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise RuntimeError("No JSON scene prompts returned")
    items = json.loads(match.group(0)).get("scenes")
    if not isinstance(items, list) or len(items) < 2:
        raise RuntimeError("Fewer than two scene prompts returned")
    result = [str(x).strip() for x in items[:SCENES]]
    if any(len(x) < 30 for x in result):
        raise RuntimeError("A scene prompt is too short")
    return result

def video_part(data):
    for step in data.get("steps", []):
        if step.get("type") == "model_output":
            for part in step.get("content", []):
                if part.get("type") == "video":
                    return part
    return data.get("output_video")

def save_video(key, part, destination):
    if part.get("data"):
        destination.write_bytes(base64.b64decode(part["data"]))
        return
    uri = part.get("uri")
    if not uri:
        raise RuntimeError("No video data or URI in Gemini response")
    match = re.search(r"/files/([^/:?]+)", uri)
    if not match:
        url = uri + ("&" if "?" in uri else "?") + "key=" + quote(key)
        r = requests.get(url, timeout=180); r.raise_for_status()
        destination.write_bytes(r.content)
        return
    file_id = match.group(1)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        r = requests.get(f"{API}/files/{quote(file_id)}",
            headers={"x-goog-api-key": key}, timeout=60)
        r.raise_for_status()
        state = r.json().get("state", "")
        if state == "ACTIVE":
            break
        if state == "FAILED":
            raise RuntimeError("Google video file processing failed")
        log(f"Waiting for Google video file ({state or 'unknown'})")
        time.sleep(8)
    else:
        raise TimeoutError("Google video file processing timed out")
    r = requests.get(f"{API}/files/{quote(file_id)}:download?alt=media",
        headers={"x-goog-api-key": key}, timeout=180)
    r.raise_for_status()
    destination.write_bytes(r.content)

def probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        check=True, capture_output=True, text=True, timeout=30)
    return float(r.stdout.strip())

def generate(key, prompts, folder):
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for i, prompt in enumerate(prompts, 1):
        log(f"Generating scene {i}/{len(prompts)} with {VIDEO_MODEL}")
        data = interaction(key, {
            "model": VIDEO_MODEL,
            "input": (prompt + f"\nOne continuous 16:9 landscape shot, {SECONDS} seconds, "
                      "720p. No text, logos, speech, narration or music."),
            "response_format": {"type": "video", "delivery": "uri",
                "aspect_ratio": "16:9", "resolution": "720p", "duration": f"{SECONDS}s"}
        })
        part = video_part(data)
        if not part:
            raise RuntimeError(f"No video returned for scene {i}")
        dest = folder / f"scene_{i:02d}.mp4"
        save_video(key, part, dest)
        if not dest.exists() or dest.stat().st_size < 50000:
            raise RuntimeError(f"Scene {i} is missing or too small")
        files.append(dest)
    (folder / "prompts.json").write_text(
        json.dumps({"model": VIDEO_MODEL, "prompts": prompts}, ensure_ascii=False, indent=2)+"\n",
        encoding="utf-8")
    return files

def composite(base, scenes, output):
    duration = probe(base)
    if duration < 30:
        raise RuntimeError("Base video too short for AI cutaways")
    starts = [duration * .27, duration * .67][:len(scenes)]
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(base)]
    for scene in scenes:
        cmd += ["-i", str(scene)]
    filters, previous = [], "[0:v]"
    for i, start in enumerate(starts, 1):
        pip, label = f"[pip{i}]", f"[v{i}]"
        filters.append(f"[{i}:v]setpts=PTS-STARTPTS,scale=720:405:"
            f"force_original_aspect_ratio=increase,crop=720:405,"
            f"pad=728:413:4:4:white,format=yuv420p{pip}")
        filters.append(f"{previous}{pip}overlay=x=W-w-48:y=40:"
            f"enable='between(t,{start:.3f},{start+SECONDS:.3f})'{label}")
        previous = label
    filters[-1] = filters[-1].replace(f"[v{len(starts)}]", "[vfinal]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vfinal]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(output)]
    log("Adding two small upper-right AI cutaways; preserving original video, subtitles and narration")
    subprocess.run(cmd, check=True, timeout=1800)
    if not output.exists() or output.stat().st_size < 1_000_000:
        raise RuntimeError("FFmpeg did not create a valid output")
    if abs(probe(output)-duration) > 1:
        raise RuntimeError("AI cutaways unexpectedly changed the video duration")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subject-file", required=True)
    p.add_argument("--script-file", required=True)
    p.add_argument("--video-in", required=True)
    p.add_argument("--video-out", required=True)
    p.add_argument("--output-dir", default="output/ai_scenes")
    a = p.parse_args()
    original, output = Path(a.video_in), Path(a.video_out)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    try:
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        subject = Path(a.subject_file).read_text(encoding="utf-8").strip()
        script = Path(a.script_file).read_text(encoding="utf-8").strip()
        if not subject or not script:
            raise RuntimeError("Subject or script is empty")
        prompts = scene_prompts(key, subject, script)
        clips = generate(key, prompts, Path(a.output_dir))
        composite(original, clips, output)
        print(f"video_path={output.as_posix()}")
        print("enabled=true")
    except Exception as exc:
        # Optional feature: never break the existing daily generation/publication path.
        log(f"WARNING: {type(exc).__name__}: {exc}")
        log("Keeping the original MoneyPrinterTurbo video.")
        print(f"video_path={original.as_posix()}")
        print("enabled=false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
