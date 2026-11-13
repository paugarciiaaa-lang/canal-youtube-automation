#!/usr/bin/env python3
"""Render phrase-based ASS karaoke captions from word-timed SRT cues."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path

STAMP = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$")
TOKEN = re.compile(r"\S+")

def to_seconds(value: str) -> float:
    match = STAMP.match(value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value!r}")
    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000

def ass_time(value: float) -> str:
    cs = max(0, round(value * 100))
    hours, rem = divmod(cs, 360000)
    minutes, rem = divmod(rem, 6000)
    seconds, centis = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"

def parse_srt(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing = next((line for line in lines if "-->" in line), None)
        if not timing:
            continue
        left, right = [part.strip().split()[0] for part in timing.split("-->", 1)]
        start, end = to_seconds(left), to_seconds(right)
        body = " ".join(lines[lines.index(timing) + 1:]).strip()
        words = TOKEN.findall(body)
        if end <= start:
            raise SystemExit(f"Invalid cue duration: {body!r}")
        if not words:
            continue
        # Multiple words in a cue are evenly split and flagged as estimated.
        step = (end - start) / len(words)
        for i, word in enumerate(words):
            cues.append({"start": start + i * step, "end": start + (i + 1) * step,
                         "text": word, "estimated": len(words) > 1})
    cues.sort(key=lambda x: x["start"])
    if len(cues) < 30:
        raise SystemExit(f"Expected word-level SRT; found only {len(cues)} word cues.")
    return cues

def sentence_end(word: str) -> bool:
    return bool(re.search(r"[.!?…][\"'»)]*$", word))

def group_phrases(cues: list[dict]) -> list[list[dict]]:
    groups, current = [], []
    for cue in cues:
        if current:
            gap = cue["start"] - current[-1]["end"]
            span = cue["start"] - current[0]["start"]
            if gap > 0.48 or len(current) >= 6 or span > 2.65 or sentence_end(current[-1]["text"]):
                groups.append(current)
                current = []
        current.append(cue)
    if current:
        groups.append(current)
    return groups

def escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

def build_ass(groups: list[list[dict]], path: Path) -> dict:
    header = """[Script Info]
Title: Caspitas phrase karaoke subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,56,&H0000D7FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,150,150,82,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for group in groups:
        parts = []
        for i, cue in enumerate(group):
            next_start = group[i + 1]["start"] if i + 1 < len(group) else cue["end"]
            centiseconds = max(1, round(max(0.02, next_start - cue["start"]) * 100))
            parts.append("{\\kf" + str(centiseconds) + "}" + escape_ass(cue["text"]))
        events.append(
            f"Dialogue: 0,{ass_time(group[0]['start'])},{ass_time(group[-1]['end'])},"
            f"Karaoke,,0,0,0,,{' '.join(parts)}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return {"phrase_count": len(groups), "word_count": sum(len(g) for g in groups),
            "estimated_word_timings": sum(c["estimated"] for g in groups for c in g),
            "max_words_per_phrase": max(map(len, groups))}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--srt", type=Path, required=True)
    parser.add_argument("--ass", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    cues = parse_srt(args.srt)
    groups = group_phrases(cues)
    stats = build_ass(groups, args.ass)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(args.video), "-map", "0:v:0", "-map", "0:a?",
        "-vf", "ass=" + args.ass.resolve().as_posix(),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
        str(args.output)
    ], check=True)
    if not args.output.is_file() or args.output.stat().st_size < 1_000_000:
        raise SystemExit("Karaoke render did not produce a valid MP4.")
    report = {"status": "passed", "style": "short phrases; active word highlighted yellow",
              **stats, "ass_file": args.ass.name, "video_file": args.output.name,
              "note": "Highlight timing comes from word-level Edge TTS SRT cues; review the rendered video."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
