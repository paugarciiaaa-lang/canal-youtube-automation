#!/usr/bin/env python3
"""Remove only narration intervals that say 'documental Caspitas' and retime SRT."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path


def seconds(value: str) -> float:
    h, m, s = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def stamp(value: float) -> str:
    ms = max(0, round(value * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    sec, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{milli:03d}"


def normalize(word: str) -> str:
    value = unicodedata.normalize("NFKD", word.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value)


def read_srt(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing = next((line for line in lines if "-->" in line), None)
        if not timing:
            continue
        left, right = [part.strip().split()[0] for part in timing.split("-->", 1)]
        text_lines = lines[lines.index(timing) + 1:]
        text = " ".join(text_lines).strip()
        if text:
            cues.append({"start": seconds(left), "end": seconds(right), "text": text})
    if not cues:
        raise SystemExit("El SRT no contiene subtítulos válidos.")
    return sorted(cues, key=lambda cue: (cue["start"], cue["end"]))


def find_branding_intervals(cues: list[dict], padding: float = 0.12) -> list[tuple[float, float]]:
    tokens = []
    for cue_index, cue in enumerate(cues):
        for word in re.findall(r"[^\W_]+", cue["text"], flags=re.UNICODE):
            tokens.append((normalize(word), cue_index))
    intervals = []
    for i in range(len(tokens)):
        if tokens[i][0] != "documental":
            continue
        matched_end = None
        if i + 1 < len(tokens) and tokens[i + 1][0] == "caspitas":
            matched_end = i + 1
        elif i + 2 < len(tokens) and tokens[i + 1][0] == "de" and tokens[i + 2][0] == "caspitas":
            matched_end = i + 2
        if matched_end is not None:
            first = cues[tokens[i][1]]
            last = cues[tokens[matched_end][1]]
            intervals.append((max(0.0, first["start"] - padding), last["end"] + padding))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 0.08:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def find_ocr_intervals(path: Path, before: float = 1.5, after: float = 2.0) -> list[tuple[float, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    times = sorted(float(item["time_seconds"]) for item in data.get("evidence", []))
    groups = []
    for value in times:
        if groups and value - groups[-1][-1] <= 3.0:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [(max(0.0, group[0] - before), group[-1] + after) for group in groups]


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 0.15:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def retime_srt(cues: list[dict], removed: list[tuple[float, float]]) -> str:
    output = []
    for cue in cues:
        start, end = cue["start"], cue["end"]
        # A cue that overlaps a removed spoken fragment is omitted rather than
        # leaving a partial word or the unwanted brand phrase in the captions.
        if any(start < cut_end and end > cut_start for cut_start, cut_end in removed):
            continue
        shift_start = sum(max(0.0, min(start, b) - a) for a, b in removed if a < start)
        shift_end = sum(max(0.0, min(end, b) - a) for a, b in removed if a < end)
        new_start, new_end = max(0.0, start - shift_start), max(0.0, end - shift_end)
        if new_end <= new_start:
            continue
        output.append(f"{len(output)+1}\n{stamp(new_start)} --> {stamp(new_end)}\n{cue['text']}\n")
    return "\n".join(output)


def cut_video(video: Path, output: Path, removed: list[tuple[float, float]]) -> None:
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video)
    ], text=True)
    duration = float(probe.strip())
    cuts = [(max(0.0, a), min(duration, b)) for a, b in removed]
    cuts = [(a, b) for a, b in cuts if b > a]
    keep = []
    cursor = 0.0
    for start, end in cuts:
        if start > cursor + 0.05:
            keep.append((cursor, start))
        cursor = max(cursor, end)
    if duration > cursor + 0.05:
        keep.append((cursor, duration))
    if not keep:
        raise SystemExit("Los cortes eliminarían el vídeo completo; se cancela.")
    filters = []
    concat_inputs = []
    for index, (start, end) in enumerate(keep):
        filters.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{index}]")
        filters.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{index}]")
        concat_inputs.append(f"[v{index}][a{index}]")
    filters.append("".join(concat_inputs) + f"concat=n={len(keep)}:v=1:a=1[vout][aout]")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(video), "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(output)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise SystemExit(result.stderr[-5000:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--srt", required=True, type=Path)
    parser.add_argument("--output-video", required=True, type=Path)
    parser.add_argument("--output-srt", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--ocr-evidence", type=Path, default=None)
    parser.add_argument("--padding", type=float, default=0.12)
    args = parser.parse_args()
    cues = read_srt(args.srt)
    removed = find_branding_intervals(cues, args.padding)
    ocr_intervals = find_ocr_intervals(args.ocr_evidence) if args.ocr_evidence else []
    removed = merge_intervals(removed + ocr_intervals)
    if not removed:
        raise SystemExit("No se encontró 'documental Caspitas' en los subtítulos; no se modifica el vídeo.")
    cut_video(args.video, args.output_video, removed)
    args.output_srt.parent.mkdir(parents=True, exist_ok=True)
    args.output_srt.write_text(retime_srt(cues, removed), encoding="utf-8")
    report = {
        "status": "processed",
        "removed_phrase": "documental Caspitas",
        "ocr_evidence_frames": len(json.loads(args.ocr_evidence.read_text(encoding="utf-8")).get("evidence", [])) if args.ocr_evidence else 0,
        "removed_intervals_seconds": [[round(a, 3), round(b, 3)] for a, b in removed],
        "removed_duration_seconds": round(sum(b-a for a, b in removed), 3),
        "original_subtitle_cues": len(cues),
        "remaining_subtitle_cues": len(read_srt(args.output_srt)),
        "note": "Se han cortado únicamente los intervalos donde la transcripción contiene la frase indicada."
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
