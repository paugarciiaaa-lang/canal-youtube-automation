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


if __name__ == "__main__":
    unittest.main()
