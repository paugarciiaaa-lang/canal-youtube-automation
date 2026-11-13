#!/usr/bin/env python3
"""Apply small, fail-closed quality/performance patches to the pinned MPT release."""
from pathlib import Path
import re

# The workflow runs this script from the repository root, while MPT is
# cloned into ./mpt. Also allow running it manually from inside ./mpt.
candidates = [Path("mpt"), Path(".")]
mpt_root = next(
    (root for root in candidates
     if (root / "app/services/task.py").is_file()
     and (root / "app/services/video.py").is_file()),
    None,
)
if mpt_root is None:
    raise SystemExit(
        "No encuentro MoneyPrinterTurbo: esperaba ./mpt/app/services/ "
        "o ./app/services/. Comprueba que el repositorio MPT se haya clonado."
    )

task_path = mpt_root / "app/services/task.py"
video_path = mpt_root / "app/services/video.py"
task = task_path.read_text(encoding="utf-8")
video = video_path.read_text(encoding="utf-8")

start = task.find("def generate_script(task_id, params):")
end = task.find("\ndef generate_terms(", start)
if start < 0 or end < 0:
    raise SystemExit("No se pudo localizar generate_script/generate_terms en MoneyPrinterTurbo; no se aplican parches parciales.")

new_function = '''def generate_script(task_id, params):
    logger.info("\\n\\n## generating and validating long-form video script")
    minimum_words = 2200
    video_script = str(params.video_script or "").strip()

    def count_words(text):
        return len(str(text or "").split())

    def append_continuation(original, continuation):
        """Append only genuinely new words, removing a repeated opening overlap."""
        original_words = original.split()
        extra_words = str(continuation or "").strip().split()
        if not extra_words:
            return original
        def key(word):
            return re.sub(r"[^a-z0-9áéíóúüñ]", "", word.casefold())
        max_overlap = min(100, len(original_words), len(extra_words))
        overlap = 0
        for size in range(max_overlap, 7, -1):
            left = [key(x) for x in original_words[-size:]]
            right = [key(x) for x in extra_words[:size]]
            if left == right:
                overlap = size
                break
        if overlap:
            extra_words = extra_words[overlap:]
        if not extra_words:
            return original
        return (original.rstrip() + "\\n\\n" + " ".join(extra_words)).strip()

    if not video_script:
        initial_prompt = str(params.video_script_prompt or "")
        video_script = str(llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=max(1, min(10, int(params.paragraph_number or 10))),
            video_script_prompt=initial_prompt,
            custom_system_prompt=params.custom_system_prompt,
        ) or "").strip()

    word_count = count_words(video_script)
    logger.info(
        f"initial script length: words={word_count}, minimum={minimum_words}"
    )

    # Preserve the best draft and extend it instead of discarding it and
    # asking the model to regenerate the whole documentary from scratch.
    for attempt in range(1, 4):
        word_count = count_words(video_script)
        if word_count >= minimum_words:
            break

        missing = minimum_words - word_count
        requested_words = min(650, max(300, missing + 180))
        tail = " ".join(video_script.split()[-115:])
        continuation_prompt = (
            "CONTINUACIÓN DE UN GUION DOCUMENTAL YA ESCRITO. "
            f"El guion actual tiene {word_count} palabras y necesita al menos "
            f"{minimum_words}. Escribe aproximadamente {requested_words} palabras NUEVAS "
            "para continuar desde el final indicado. No repitas ni reescribas el guion. "
            "No incluyas títulos, listas de instrucciones ni comentarios sobre el proceso. "
            "Mantén español de España, tono documental y continuidad narrativa. "
            "No inventes nombres, fechas, citas, pruebas, fuentes ni hechos nuevos: "
            "amplía únicamente el contexto y las implicaciones de lo ya expuesto, "
            "distinguiendo hechos de hipótesis. Termina de forma natural. "
            "Último fragmento del guion (solo contexto; no lo repitas): "
            + tail
        )
        logger.info(
            f"script continuation: attempt={attempt}/3, "
            f"current_words={word_count}, target_addition={requested_words}"
        )
        continuation = llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=3,
            video_script_prompt=continuation_prompt,
            custom_system_prompt=params.custom_system_prompt,
        )
        continuation = str(continuation or "").strip()
        added_words = count_words(continuation)
        if added_words:
            updated = append_continuation(video_script, continuation)
            new_count = count_words(updated)
            if new_count > word_count:
                video_script = updated
                logger.info(
                    f"continuation accepted: added={new_count-word_count}, "
                    f"total_words={new_count}"
                )
            else:
                logger.warning(
                    f"continuation produced no new words: returned={added_words}"
                )
        else:
            logger.warning("continuation returned empty text; preserving current draft")

    word_count = count_words(video_script)
    if not video_script or word_count < minimum_words:
        message = (
            f"guion insuficiente tras conservar y ampliar el mejor borrador: "
            f"{word_count} palabras; mínimo {minimum_words}. "
            "No se ha descartado el texto generado. Se detiene antes de voz, "
            "descarga de materiales y renderizado."
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

    if audio_duration is None or float(audio_duration) < 600:
        actual = 0.0 if audio_duration is None else float(audio_duration)
        message = (
            f"narración demasiado corta: {actual / 60:.2f} minutos; "
            "mínimo 10 minutos. Se detiene antes de subtítulos, descarga "
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
