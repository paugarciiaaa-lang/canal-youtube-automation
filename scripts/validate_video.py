#!/usr/bin/env python3
"""Validate the finished Caspitas MP4, audio duration and word-level SRT timing."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path

STAMP = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$")

def seconds(value: str) -> float:
    m = STAMP.match(value.strip())
    if not m:
        raise ValueError(f"timestamp SRT no válido: {value!r}")
    h, minute, sec, ms = map(int, m.groups())
    return h * 3600 + minute * 60 + sec + ms / 1000

def probe(path: Path) -> dict:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path)
    ], text=True)
    return json.loads(raw)

def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing = next((line for line in lines if "-->" in line), None)
        if not timing:
            continue
        left, right = [part.strip().split()[0] for part in timing.split("-->", 1)]
        start, end = seconds(left), seconds(right)
        caption_index = lines.index(timing)
        caption = " ".join(lines[caption_index + 1:]).strip()
        if end <= start or not caption:
            raise SystemExit("Subtítulo vacío o con duración inválida.")
        cues.append((start, end, caption))
    return cues

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    video = args.video.resolve()
    audio = video.parent / "audio.mp3"
    srt = video.parent / "subtitle.srt"

    if not video.is_file() or video.stat().st_size < 1_000_000:
        raise SystemExit("MP4 inexistente o demasiado pequeño.")
    if not audio.is_file() or not srt.is_file():
        raise SystemExit("Falta audio.mp3 o subtitle.srt: no se puede verificar sincronización.")

    vdata, adata = probe(video), probe(audio)
    vstreams = [x for x in vdata.get("streams", []) if x.get("codec_type") == "video"]
    astreams = [x for x in vdata.get("streams", []) if x.get("codec_type") == "audio"]
    if not vstreams or not astreams:
        raise SystemExit("El MP4 debe contener pistas de vídeo y audio.")
    vs, aus = vstreams[0], astreams[0]
    video_duration = float(vdata["format"]["duration"])
    audio_duration = float(adata["format"]["duration"])
    muxed_audio_duration = float(aus.get("duration") or audio_duration)
    av_drift = abs(video_duration - muxed_audio_duration)
    if video_duration < 840:
        raise SystemExit(f"Duración insuficiente: {video_duration/60:.2f} min; mínimo 14 min.")
    if av_drift > 1.0:
        raise SystemExit(f"Desincronización A/V: {av_drift:.2f}s (máximo 1.0s).")
    if (vs.get("width"), vs.get("height")) != (1920, 1080):
        raise SystemExit(f"Resolución inesperada: {vs.get('width')}x{vs.get('height')}.")

    cues = parse_srt(srt)
    if len(cues) < 30:
        raise SystemExit(f"Demasiados pocos subtítulos ({len(cues)}); posible SRT incompleto.")
    starts = [cue[0] for cue in cues]
    if any(b < a for a, b in zip(starts, starts[1:])):
        raise SystemExit("Los subtítulos no están ordenados cronológicamente.")
    if cues[0][0] > 3.0:
        raise SystemExit(f"Los subtítulos empiezan demasiado tarde ({cues[0][0]:.2f}s).")
    subtitle_tail_gap = abs(audio_duration - cues[-1][1])
    if subtitle_tail_gap > 4.0:
        raise SystemExit(
            f"El último subtítulo se separa {subtitle_tail_gap:.2f}s del final del audio; "
            "posible desfase o transcripción incompleta."
        )

    report = {
        "status": "passed",
        "video": str(video.name),
        "file_size_mb": round(video.stat().st_size / 1024 / 1024, 2),
        "duration_seconds": round(video_duration, 3),
        "duration_minutes": round(video_duration / 60, 2),
        "audio_duration_seconds": round(audio_duration, 3),
        "audio_video_drift_seconds": round(av_drift, 3),
        "resolution": f"{vs.get('width')}x{vs.get('height')}",
        "video_codec": vs.get("codec_name"),
        "audio_codec": aus.get("codec_name"),
        "subtitle_cues": len(cues),
        "first_subtitle_seconds": round(cues[0][0], 3),
        "last_subtitle_seconds": round(cues[-1][1], 3),
        "subtitle_audio_tail_gap_seconds": round(subtitle_tail_gap, 3),
        "checks": [
            "MP4 válido y superior a 1 MB",
            "pistas de vídeo y audio presentes",
            "duración mínima de 14 minutos",
            "sincronización audio/vídeo <= 1 segundo",
            "resolución 1920x1080",
            "subtítulos presentes, ordenados y próximos al inicio/final del audio",
        ],
        "note": "La sincronía estructural se valida con la línea temporal SRT de TTS; no sustituye una escucha humana de control."
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
