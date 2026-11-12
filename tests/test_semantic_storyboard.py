import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from semantic_storyboard import extract_json, read_srt, transcript_grounded_scenes, normalize_evidence


class SemanticStoryboardTests(unittest.TestCase):
    def test_reads_subtitle_timing_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "captions.srt"
            path.write_text("\n".join([
                "1",
                "00:00:01,000 --> 00:00:02,500",
                "En 1981 llegó a la estación.",
                "",
                "2",
                "00:00:02,500 --> 00:00:04,000",
                "Encontró una carta.",
                "",
            ]), encoding="utf-8")
            cues = read_srt(path)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]["start"], 1.0)
        self.assertEqual(cues[0]["end"], 2.5)
        self.assertIn("1981", cues[0]["text"])

    def test_extracts_plain_json(self):
        result = extract_json('{"scenes":[{"type":"timeline"}]}')
        self.assertEqual(result["scenes"][0]["type"], "timeline")

    def test_extracts_json_inside_markdown_fence(self):
        ticks = chr(96) * 3
        result = extract_json(ticks + "json\n{\"scenes\":[]}\n" + ticks)
        self.assertEqual(result, {"scenes": []})

    def test_transcript_grounded_fallback_uses_only_literal_subtitles(self):
        cues = [
            {"start": 2.0, "end": 3.0, "text": "En 1981 llegó a una pequeña estación."},
            {"start": 4.0, "end": 5.0, "text": "Llevaba una carta y una maleta."},
            {"start": 52.0, "end": 53.0, "text": "La policía encontró varios documentos."},
            {"start": 54.0, "end": 55.0, "text": "Ninguno tenía un nombre completo."},
            {"start": 102.0, "end": 103.0, "text": "La investigación continuó durante años."},
            {"start": 104.0, "end": 105.0, "text": "Pero quedaron muchas preguntas abiertas."},
        ]
        windows = [
            {"start": 0.0, "end": 48.0},
            {"start": 48.0, "end": 96.0},
            {"start": 96.0, "end": 144.0},
        ]
        scenes = transcript_grounded_scenes(cues, windows, [])
        self.assertGreaterEqual(len(scenes), 3)
        full_text = normalize_evidence(" ".join(x["text"] for x in cues))
        for scene in scenes:
            self.assertIn(normalize_evidence(scene["factual_basis"]), full_text)
            self.assertEqual(scene["planner"], "transcript_grounded_fallback")
            self.assertEqual(scene["location_query"], "")
            self.assertEqual(scene["document_search"], "")


if __name__ == "__main__":
    unittest.main()
