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
    target_words = "2.300-2.500 palabras"
    video_script = str(params.video_script or "").strip()
    supplied_script = bool(video_script)

    def word_count(text):
        return len(str(text or "").split())

    def append_continuation(existing, continuation):
        """Append only new text, trimming a repeated ending when detectable."""
        old_words = existing.split()
        new_words = str(continuation or "").strip().split()
        if not new_words:
            return existing.strip(), 0

        def normalize(word):
            return "".join(char.lower() for char in word if char.isalnum())

        old_norm = [normalize(word) for word in old_words]
        new_norm = [normalize(word) for word in new_words]
        max_overlap = min(250, len(old_norm), len(new_norm))
        overlap = 0
        for size in range(max_overlap, 7, -1):
            if old_norm[-size:] == new_norm[:size]:
                overlap = size
                break

        if overlap:
            new_words = new_words[overlap:]
        elif len(old_norm) >= 30 and len(new_norm) >= 30:
            # Some models ignore the continuation instruction and return the
            # whole script again. Detect a repeated opening and reject it.
            if old_norm[:30] == new_norm[:30]:
                return existing.strip(), -1

        if not new_words:
            return existing.strip(), overlap
        return existing.rstrip() + "\\n\\n" + " ".join(new_words), overlap

    if supplied_script:
        best_script = video_script
        logger.info(f"provided script word count: {word_count(best_script)}")
    else:
        initial_prompt = (
            str(params.video_script_prompt or "")
            + f"\\n\\nREQUISITO DE DURACIÓN: redacta un documental de {target_words}. "
            "No resumas. Desarrolla cronología, contexto, pruebas, testimonios "
            "atribuibles, hipótesis contrastadas, contradicciones y consecuencias. "
            "No inventes datos ni alargues con repeticiones."
        )
        best_script = str(llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=max(1, min(10, int(params.paragraph_number or 10))),
            video_script_prompt=initial_prompt,
            custom_system_prompt=params.custom_system_prompt,
        ) or "").strip()

        current_count = word_count(best_script)
        logger.info(
            f"script length validation: initial words={current_count}, "
            f"minimum={minimum_words}"
        )

        # Continue the existing draft instead of discarding it and paying for
        # another complete generation. Each round requests only the missing
        # material and includes the full draft to preserve chronology/context.
        for continuation_round in range(1, 4):
            current_count = word_count(best_script)
            if current_count >= minimum_words:
                break
            if not best_script:
                logger.warning("Initial generation returned an empty script.")
                break

            needed = minimum_words - current_count
            requested = max(300, min(700, needed + 120))
            continuation_prompt = (
                str(params.video_script_prompt or "")
                + "\\n\\nCONTINUACIÓN DEL DOCUMENTAL — NO REESCRIBAS EL TEXTO. "
                + f"El guion actual tiene {current_count} palabras y faltan "
                + f"aproximadamente {needed} para superar el mínimo de {minimum_words}. "
                + f"Escribe SOLO una continuación nueva de unas {requested} palabras. "
                + "Continúa exactamente desde el último párrafo. No repitas la "
                + "introducción, hechos ya explicados ni conclusiones. Añade contexto, "
                + "pruebas, matices o consecuencias que todavía falten. No inventes "
                + "datos. Devuelve únicamente el texto nuevo, sin encabezados técnicos.\\n\\n"
                + "GUION YA GENERADO (úsalo como contexto; no lo copies):\\n"
                + best_script
            )
            continuation = str(llm.generate_script(
                video_subject=params.video_subject,
                language=params.video_language,
                paragraph_number=max(1, min(10, int(params.paragraph_number or 10))),
                video_script_prompt=continuation_prompt,
                custom_system_prompt=params.custom_system_prompt,
            ) or "").strip()

            merged, overlap = append_continuation(best_script, continuation)
            if overlap < 0:
                logger.warning(
                    f"continuation {continuation_round}/3 repeated the opening; "
                    "discarding it to prevent duplicated narration."
                )
                break
            if merged == best_script:
                logger.warning(
                    f"continuation {continuation_round}/3 added no usable text; "
                    "stopping without losing the existing draft."
                )
                break

            best_script = merged
            current_count = word_count(best_script)
            logger.info(
                f"script continuation: round={continuation_round}/3, "
                f"words={current_count}, trimmed_overlap={max(overlap, 0)}, "
                f"minimum={minimum_words}"
            )

    # Always validate and report the best draft actually obtained. Never reset
    # a non-empty short draft to an empty string before the final error report.
    video_script = best_script.strip()
    final_count = word_count(video_script)
    if not video_script or final_count < minimum_words:
        message = (
            f"guion demasiado corto: {final_count} palabras; mínimo "
            f"{minimum_words}. Se detiene antes de generar audio, descargar "
            "materiales o renderizar para no desperdiciar tiempo."
        )
        logger.error(message)
        _mark_task_failed(task_id, "script", message)
        return None

    logger.info(f"accepted script: {final_count} words")
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

old_render = "        bgm_mix_succeeded = video.generate_video(\n            video_path=combined_video_path,\n            audio_path=audio_file,\n            subtitle_path=subtitle_path,\n            output_file=final_video_path,\n            params=params,\n            bgm_file_override=bgm_file_override,\n        )"
new_render = "        # Keep the generated word-level SRT, but do not burn MPT's one-word\n        # captions into the picture. Phrase-level karaoke captions are rendered\n        # in the final FFmpeg pass after the hybrid montage and SFX mix.\n        video_render_params = __import__(\"copy\").copy(params)\n        video_render_params.subtitle_enabled = False\n        bgm_mix_succeeded = video.generate_video(\n            video_path=combined_video_path,\n            audio_path=audio_file,\n            subtitle_path=subtitle_path,\n            output_file=final_video_path,\n            params=video_render_params,\n            bgm_file_override=bgm_file_override,\n        )"
if old_render not in task:
    raise SystemExit("No se encontró el bloque generate_video para desactivar los subtítulos de una palabra.")
task = task.replace(old_render, new_render, 1)
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
