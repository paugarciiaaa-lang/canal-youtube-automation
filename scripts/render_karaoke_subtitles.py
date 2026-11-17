#!/usr/bin/env python3
"""Render readable phrase-based karaoke captions from MoneyPrinterTurbo word SRT."""
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path

def timestamp(value: str) -> float:
    h, m, s = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def parse_srt(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        timing = next((x for x in lines if "-->" in x), None)
        if not timing: continue
        a, b = [x.strip().split()[0] for x in timing.split("-->", 1)]
        text = " ".join(lines[lines.index(timing)+1:]).strip()
        if text:
            start, end = timestamp(a), timestamp(b)
            if end > start: cues.append({"start": start, "end": end, "text": text})
    if not cues: raise SystemExit("El SRT no contiene cues válidos.")
    return sorted(cues, key=lambda x: (x["start"], x["end"]))

def split_words(cue: dict) -> list[dict]:
    words = cue["text"].split()
    span = cue["end"] - cue["start"]
    # Some TTS subtitle cues contain short phrases. Distribute their duration
    # evenly across the words while retaining the original cue boundaries.
    return [{"start": cue["start"] + span*i/len(words),
             "end": cue["start"] + span*(i+1)/len(words), "word": word}
            for i, word in enumerate(words)]

def phrase_groups(cues: list[dict], max_words=6, max_chars=44, max_duration=2.8, max_gap=0.24):
    words = [word for cue in cues for word in split_words(cue)]
    groups, current = [], []
    def flush():
        if current:
            groups.append(current.copy()); current.clear()
    for item in words:
        if current:
            gap = item["start"] - current[-1]["end"]
            candidate_chars = sum(len(x["word"]) + 1 for x in current) + len(item["word"])
            span = item["end"] - current[0]["start"]
            previous = current[-1]["word"]
            boundary = bool(re.search(r"[.!?;:]([”’\"')\]]*)$", previous))
            if gap > max_gap or len(current) >= max_words or candidate_chars > max_chars or span > max_duration or boundary:
                flush()
        current.append(item)
        if re.search(r"[.!?;:]([”’\"')\]]*)$", item["word"]):
            flush()
    flush()
    return groups

def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

def ass_escape(value: str) -> str:
    return value.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", " ")

def build_ass(cues: list[dict], output: Path, width=1920, height=1080):
    groups = phrase_groups(cues)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Karaoke,DejaVu Sans,50,&H00FFFFFF,&H0000D7FF,&H00101010,&HA6000000,-1,0,0,0,100,100,0,0,3,18,1,2,100,100,105,1",
        "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"
    ]
    for group in groups:
        start, end = group[0]["start"], group[-1]["end"]
        tokens = []
        for item in group:
            duration = max(1, round((item["end"] - item["start"]) * 100))
            tokens.append(r"{\kf" + str(duration) + "}" + ass_escape(item["word"]))
        text = " ".join(tokens)
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Karaoke,,0,0,0,,{text}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return groups

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--srt", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--ass-output", type=Path, default=None)
    p.add_argument("--crf", type=int, default=19)
    p.add_argument("--mask-existing-subtitles", action="store_true", help="Oculta la antigua capa de subtítulos antes de dibujar una sola capa nueva.")
    a = p.parse_args()
    if not a.video.is_file() or not a.srt.is_file():
        raise SystemExit("No se encuentra el MP4 o el SRT.")
    ass = a.ass_output or a.output.with_suffix(".ass")
    groups = build_ass(parse_srt(a.srt), ass)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(ass.resolve()).replace("\\", "/").replace(":", r"\:")
    filters = []
    if a.mask_existing_subtitles:
        # Cover the original burned-in captions before rendering the cleaned
        # karaoke layer, so only one readable subtitle track remains visible.
        filters.append("drawbox=x=0:y=ih-220:w=iw:h=220:color=black@1.0:t=fill")
    filters.append(f"ass='{escaped}'")
    video_filter = ",".join(filters)
    cmd = ["ffmpeg", "-y", "-i", str(a.video), "-vf", video_filter,
           "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-c:a", "copy",
           "-movflags", "+faststart", str(a.output)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode:
        raise SystemExit(proc.stderr[-5000:])
    print(f"Karaoke generado: {len(groups)} frases; ASS: {ass}; MP4: {a.output}")

if __name__ == "__main__":
    main()
