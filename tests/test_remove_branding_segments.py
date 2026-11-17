import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from remove_branding_segments import find_branding_intervals, retime_srt, read_srt


class RemoveBrandingSegmentsTests(unittest.TestCase):
    def test_detects_phrase_split_across_word_level_cues(self):
        cues = [
            {"start": 1.0, "end": 1.3, "text": "Este"},
            {"start": 1.3, "end": 1.7, "text": "es"},
            {"start": 1.7, "end": 2.2, "text": "documental"},
            {"start": 2.2, "end": 2.8, "text": "Caspitas."},
            {"start": 2.9, "end": 3.2, "text": "Seguimos."},
        ]
        self.assertEqual(find_branding_intervals(cues), [(1.58, 2.92)])

    def test_detects_optional_de_and_accents_case_insensitively(self):
        cues = [
            {"start": 5.0, "end": 5.5, "text": "DOCUMENTAL"},
            {"start": 5.5, "end": 5.8, "text": "de"},
            {"start": 5.8, "end": 6.2, "text": "Caspítas"},
        ]
        self.assertEqual(find_branding_intervals(cues), [(4.88, 6.32)])

    def test_retimes_following_subtitles_after_cut(self):
        cues = [
            {"start": 0.0, "end": 1.0, "text": "Inicio"},
            {"start": 2.0, "end": 3.0, "text": "documental"},
            {"start": 3.0, "end": 4.0, "text": "Caspitas"},
            {"start": 5.0, "end": 6.0, "text": "Final"},
        ]
        removed = [(1.88, 4.12)]
        result = retime_srt(cues, removed)
        self.assertIn("00:00:00,000 --> 00:00:01,000", result)
        self.assertIn("00:00:02,880 --> 00:00:03,880", result)
        self.assertNotIn("documental", result)
        self.assertNotIn("Caspitas", result)


if __name__ == "__main__":
    unittest.main()
