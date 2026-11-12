import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MoneyPrinterPatchTests(unittest.TestCase):
    def test_patch_keeps_best_draft_and_adds_continuation(self):
        repo_root = Path(__file__).resolve().parents[1]
        patcher = repo_root / "scripts" / "patch_moneyprinter.py"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            services = root / "mpt" / "app" / "services"
            services.mkdir(parents=True)
            task = services / "task.py"
            video = services / "video.py"

            task.write_text(
                '''def generate_script(task_id, params):
    return "old"

def generate_terms():
    pass

def audio_stage():
    if not audio_file:
        return _mark_task_failed(
            task_id,
            "audio",
            "failed to prepare narration audio",
        )

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30)
''',
                encoding="utf-8",
            )
            video.write_text(
                '''def concat():
    args = [
            "-c:v",
            codec,
            "-threads",
    ]

def render(kwargs):
    kwargs.setdefault("ffmpeg_params", _BT709_FFMPEG_PARAMS)
''',
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(patcher)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched_task = task.read_text(encoding="utf-8")
            compile(patched_task, str(task), "exec")
            compile(video.read_text(encoding="utf-8"), str(video), "exec")

            self.assertIn("best_script", patched_task)
            self.assertIn("continuation_round", patched_task)
            self.assertIn("append_continuation", patched_task)
            self.assertIn("final_count = word_count(video_script)", patched_task)
            self.assertNotIn('video_script = ""', patched_task)
            self.assertIn("guion demasiado corto: {final_count} palabras", patched_task)

            # Exercise the patched function: a short first draft must be kept
            # and extended, rather than erased before the final validation.
            class Logger:
                def info(self, *args, **kwargs): pass
                def warning(self, *args, **kwargs): pass
                def error(self, *args, **kwargs): pass

            class FakeLLM:
                def __init__(self, responses):
                    self.responses = list(responses)
                    self.calls = 0

                def generate_script(self, **kwargs):
                    self.calls += 1
                    return self.responses.pop(0)

            from types import SimpleNamespace
            first = "inicio " * 1800
            extra = "continuacion " * 500
            fake_llm = FakeLLM([first, extra])
            namespace = {
                "logger": Logger(),
                "llm": fake_llm,
                "_mark_task_failed": lambda *args: "FAILED",
            }
            exec(compile(patched_task, str(task), "exec"), namespace)
            params = SimpleNamespace(
                video_script="",
                video_script_prompt="documental",
                video_subject="prueba",
                video_language="es-ES",
                paragraph_number=10,
                custom_system_prompt=None,
            )
            result = namespace["generate_script"]("test-task", params)
            self.assertIsNotNone(result)
            self.assertGreaterEqual(len(result.split()), 2200)
            self.assertEqual(fake_llm.calls, 2)

            # If all continuations remain too short, the error must report
            # the actual best word count, never the misleading value zero.
            fake_llm = FakeLLM([first, "añadido " * 10, "más " * 10, "final " * 10])
            namespace["llm"] = fake_llm
            failed = []
            namespace["_mark_task_failed"] = lambda *args: failed.append(args) or "FAILED"
            result = namespace["generate_script"]("test-task", params)
            self.assertIsNone(result)
            self.assertIn("1830 palabras", failed[0][2])
            self.assertNotIn("0 palabras", failed[0][2])


if __name__ == "__main__":
    unittest.main()
