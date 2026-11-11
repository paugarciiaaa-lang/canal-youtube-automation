#!/usr/bin/env python3
"""Apply small, fail-closed quality/performance patches to the pinned MPT release."""
from pathlib import Path
import re

task_path = Path("app/services/task.py")
video_path = Path("app/services/video.py")
task = task_path.read_text(encoding="utf-8")
video = video_path.read_text(encoding="utf-8")

start = task.find("def generate_script(task_id, params):")
end = task.find("\ndef generate_terms(", start)
if start < 0 or end < 0:
    raise SystemExit("No se pudo localizar generate_script/generate_terms en MoneyPrinterTurbo; no se aplican parches parciales.")

new_function = '''def generate_script(task_id, params):
    logger.info("\\n\\n## generating and validating long-form video script")
    minimum_words = 1700
    target_words = "1.900-2.200 palabras"
    video_script = str(params.video_script or "").strip()

    if video_script:
        word_count = len(video_script.split())
        logger.info(f"provided script word count: {word_count}")
    else:
        video_script = ""
        for attempt in range(1, 4):
            retry_note = (
                f"\\n\\nREQUISITO DE DURACIÓN OBLIGATORIO: redacta entre {target_words}. "
                "No resumas ni acortes. Desarrolla cronología, contexto, pruebas, "
                "testimonios atribuibles, hipótesis contrastadas y consecuencias. "
                "Antes de terminar, comprueba que el texto supera 1.900 palabras. "
                f"Esta es la generación {attempt} de 3."
            )
            prompt = str(params.video_script_prompt or "") + retry_note
            video_script = llm.generate_script(
                video_subject=params.video_subject,
                language=params.video_language,
                paragraph_number=max(16, int(params.paragraph_number or 10)),
                video_script_prompt=prompt,
                custom_system_prompt=params.custom_system_prompt,
            )
            video_script = str(video_script or "").strip()
            word_count = len(video_script.split())
            logger.info(
                f"script length validation: attempt={attempt}/3, "
                f"words={word_count}, minimum={minimum_words}"
            )
            if word_count >= minimum_words:
                break
            logger.warning(
                f"script too short ({word_count} words); regenerating BEFORE "
                "voice, stock downloads and video rendering."
            )
            video_script = ""

    word_count = len(video_script.split())
    if not video_script or word_count < minimum_words:
        message = (
            f"guion demasiado corto: {word_count} palabras; mínimo "
            f"{minimum_words}. Se detiene antes de generar audio, descargar "
            "materiales o renderizar para no desperdiciar tiempo."
        )
        logger.error(message)
        _mark_task_failed(task_id, "script", message)
        return None

    logger.info(f"accepted script: {word_count} words")
    return video_script

'''
task = task[:start] + new_function + task[end:]

# Reject short TTS before subtitle generation, stock downloads, clip processing or rendering.
old_audio_guard = """    if not audio_file:
        return _mark_task_failed(
            task_id,
            "audio",
            "failed to prepare narration audio",
        )

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30)
"""
new_audio_guard = """    if not audio_file:
        return _mark_task_failed(
            task_id,
            "audio",
            "failed to prepare narration audio",
        )

    if audio_duration is None or float(audio_duration) < 720:
        actual = 0.0 if audio_duration is None else float(audio_duration)
        message = (
            f"narración demasiado corta: {actual / 60:.2f} minutos; "
            "mínimo 12 minutos. Se detiene antes de subtítulos, descarga "
            "de clips y renderizado."
        )
        logger.error(message)
        return _mark_task_failed(task_id, "audio", message)

    logger.info(f"audio duration preflight passed: {float(audio_duration) / 60:.2f} minutes")
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30)
"""
if old_audio_guard not in task:
    raise SystemExit("No se encontró la validación de audio de task.py; se cancela el parche.")
task = task.replace(old_audio_guard, new_audio_guard, 1)
task_path.write_text(task, encoding="utf-8")

old_concat = '''            "-c:v",
            codec,
            "-threads",'''
new_concat = '''            "-c:v",
            codec,
            # GitHub-hosted runners are CPU-limited. veryfast/CRF 23 is a
            # deliberate speed-quality tradeoff for daily 1080p YouTube videos.
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-threads",'''
if old_concat not in video:
    raise SystemExit("No se encontró el bloque de FFmpeg concat; se cancela el parche.")
video = video.replace(old_concat, new_concat, 1)

old_params = 'kwargs.setdefault("ffmpeg_params", _BT709_FFMPEG_PARAMS)'
new_params = 'kwargs.setdefault("ffmpeg_params", _BT709_FFMPEG_PARAMS + ["-preset", "veryfast", "-crf", "23"])'
if old_params not in video:
    raise SystemExit("No se encontró la configuración de parámetros FFmpeg final; se cancela el parche.")
video = video.replace(old_params, new_params, 1)
video_path.write_text(video, encoding="utf-8")
print("MoneyPrinterTurbo parcheado: control de palabras antes del render y FFmpeg veryfast/CRF23.")
