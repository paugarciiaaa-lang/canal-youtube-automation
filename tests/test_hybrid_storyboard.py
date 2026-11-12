import json
import tempfile
import unittest
from pathlib import Path
from scripts.hybrid_storyboard import parse_srt, pick_style

class HybridStoryboardTests(unittest.TestCase):
    def test_parse_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"x.srt"
            p.write_text("1\n00:00:01,000 --> 00:00:03,500\nLa prueba apareció en la estación.\n",encoding="utf-8")
            cues=parse_srt(p)
            self.assertEqual(len(cues),1)
            self.assertEqual(cues[0]["start"],1.0)
            self.assertEqual(cues[0]["end"],3.5)

    def test_relevant_style_selection(self):
        self.assertEqual(pick_style("El mapa muestra la ruta hasta Bergen",0),1)
        self.assertEqual(pick_style("La carta y el informe son pruebas",0),3)

if __name__=="__main__": unittest.main()
