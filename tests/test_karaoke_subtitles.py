import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_karaoke_subtitles import phrase_groups, parse_srt, build_ass


class KaraokeSubtitleTests(unittest.TestCase):
    def test_groups_word_cues_into_readable_phrases(self):
        cues = [
            {"start": 0.0, "end": 0.2, "text": "El"},
            {"start": 0.21, "end": 0.5, "text": "avión"},
            {"start": 0.51, "end": 0.7, "text": "despegó"},
            {"start": 0.71, "end": 0.9, "text": "de"},
            {"start": 0.91, "end": 1.2, "text": "Portland."},
        ]
        groups = phrase_groups(cues)
        self.assertEqual(len(groups), 1)
        self.assertEqual(" ".join(x["word"] for x in groups[0]), "El avión despegó de Portland.")

    def test_phrase_breaks_at_sentence_punctuation(self):
        cues = [
            {"start": 0.0, "end": 0.2, "text": "Llegó"},
            {"start": 0.21, "end": 0.5, "text": "a"},
            {"start": 0.51, "end": 0.9, "text": "Seattle."},
            {"start": 1.0, "end": 1.2, "text": "Después"},
            {"start": 1.21, "end": 1.5, "text": "desapareció."},
        ]
        groups = phrase_groups(cues)
        self.assertEqual(len(groups), 2)

    def test_builds_ass_with_progressive_highlight_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.srt"
            target = Path(tmp) / "sample.ass"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:00,300\nEl\n\n"
                "2\n00:00:00,300 --> 00:00:00,700\navión\n\n"
                "3\n00:00:00,700 --> 00:00:01,200\ndespegó.\n",
                encoding="utf-8")
            groups = build_ass(parse_srt(source), target)
            data = target.read_text(encoding="utf-8")
        self.assertEqual(len(groups), 1)
        self.assertIn(r"{\kf", data)
        self.assertIn("Style: Karaoke", data)


if __name__ == "__main__":
    unittest.main()
