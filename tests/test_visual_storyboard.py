import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_visual_storyboard as storyboard


class VisualStoryboardTests(unittest.TestCase):
    def test_extracts_named_entities_and_aircraft_models(self):
        found = storyboard.entities(
            "D. B. Cooper subió a un Boeing 727 y el vuelo 305 partió de Portland."
        )
        self.assertIn("D. B. Cooper", found)
        self.assertIn("Boeing 727", found)
        self.assertIn("vuelo 305", [x.casefold() for x in found])

    def test_creates_time_aligned_visual_queries_from_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            srt = root / "source.srt"
            output = root / "storyboard.json"
            blocks = []
            for i in range(0, 180, 3):
                blocks.extend([
                    str(i // 3 + 1),
                    f"00:00:{i:02d},000 --> 00:00:{i+2:02d},000",
                    "D. B. Cooper abordó un Boeing 727 en el vuelo 305.",
                    ""
                ])
            srt.write_text("\n".join(blocks), encoding="utf-8")
            storyboard.main = storyboard.main
            import subprocess
            import json
            subprocess.run([
                sys.executable, str(ROOT / "scripts" / "build_visual_storyboard.py"),
                "--srt", str(srt), "--topic", "D. B. Cooper",
                "--output", str(output), "--interval", "36"
            ], check=True, capture_output=True, text=True)
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertGreaterEqual(result["scene_count"], 3)
        self.assertTrue(any(x["visual_search"] for x in result["scenes"]))


if __name__ == "__main__":
    unittest.main()
