import unittest

from scripts.hybrid_visual_engine import classify


class HybridVisualEngineTests(unittest.TestCase):
    def test_generic_fallback_does_not_insert_stickman(self):
        kind, _ = classify("El relato continuó durante varios meses sin novedades.", 0)
        self.assertEqual(kind, "motion")
        self.assertNotEqual(kind, "stickman")

    def test_historical_action_is_reconstruction(self):
        kind, _ = classify("Los bomberos llegaron a la casa durante el incendio.", 1)
        self.assertEqual(kind, "reconstruction")

    def test_island_story_is_mapped_as_location(self):
        kind, _ = classify("La isla estaba rodeada por el mar.", 2)
        self.assertEqual(kind, "map")


if __name__ == "__main__":
    unittest.main()
