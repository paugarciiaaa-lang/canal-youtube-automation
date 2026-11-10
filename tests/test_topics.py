import json
import unittest
from pathlib import Path


class TopicCatalogTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.topics = json.loads((root / "data" / "topics.json").read_text(encoding="utf-8"))

    def test_catalog_has_at_least_25_topics(self):
        self.assertGreaterEqual(len(self.topics), 25)

    def test_topic_ids_are_unique_and_non_empty(self):
        ids = [topic.get("id", "").strip() for topic in self.topics]
        self.assertTrue(all(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_topic_has_a_subject(self):
        self.assertTrue(all(topic.get("video_subject", "").strip() for topic in self.topics))


if __name__ == "__main__":
    unittest.main()
