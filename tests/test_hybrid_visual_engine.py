import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import hybrid_visual_engine as engine


class HybridVisualEngineTests(unittest.TestCase):
    def test_reads_numeric_subtitle_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.srt"
            path.write_text("1\\n00:00:01,000 --> 00:00:02,000\\n1981\\n\\n2\\n00:00:02,000 --> 00:00:03,000\\nLa estación\\n", encoding="utf-8")
            cues = engine.read_srt(path)
        self.assertEqual(cues[0]["text"], "1981")
        self.assertEqual(cues[1]["text"], "La estación")

    def test_classifies_year_as_timeline(self):
        kind, _ = engine.classify("El 12 de junio de 1981 ocurrió el suceso.", 0)
        self.assertEqual(kind, "timeline")

    def test_classifies_location_as_schematic_map(self):
        kind, _ = engine.classify("La expedición llegó a la montaña durante la noche.", 1)
        self.assertEqual(kind, "map")

    def test_plan_creates_spaced_scenes(self):
        cues = [
            {"start": 0.0, "end": 220.0, "text": "En 1981 el investigador llegó a la estación y encontró un documento."}
        ]
        scenes = engine.plan(cues, 240.0, 55.0, 4.5)
        self.assertGreaterEqual(len(scenes), 3)
        self.assertTrue(all(s["duration"] == 4.5 for s in scenes))
        self.assertTrue(all(a["start"] < b["start"] for a, b in zip(scenes, scenes[1:])))


if __name__ == "__main__":
    unittest.main()
