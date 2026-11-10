import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from shorts_queue import add_video, due_for_slot, mark_published, load_queue, save_queue


class ShortsQueueTests(unittest.TestCase):
    def setUp(self):
        self.data = {"version": 1, "timezone": "Europe/Madrid", "videos": []}
        for day in range(1, 8):
            add_video(self.data, f"video{day}", f"2026-11-{day:02d}",
                      [f"video{day}/short{i}.mp4" for i in range(1, 6)])

    def test_ramp_up_and_five_daily_slots(self):
        self.assertEqual(due_for_slot(self.data, "2026-11-01", "12:00"), None)
        self.assertEqual(due_for_slot(self.data, "2026-11-02", "12:00")["video_id"], "video1")
        self.assertEqual(due_for_slot(self.data, "2026-11-03", "12:00")["short_number"], 1)
        self.assertEqual(due_for_slot(self.data, "2026-11-03", "14:00")["video_id"], "video1")
        self.assertEqual(due_for_slot(self.data, "2026-11-03", "14:00")["short_number"], 2)

    def test_each_slot_uses_its_matching_age(self):
        expected = [
            ("12:00", "video5", 1),
            ("14:00", "video4", 2),
            ("16:00", "video3", 3),
            ("18:00", "video2", 4),
            ("20:00", "video1", 5),
        ]
        for slot, video_id, short_number in expected:
            result = due_for_slot(self.data, "2026-11-05", slot)
            self.assertEqual((result["video_id"], result["short_number"]), (video_id, short_number))

    def test_published_short_is_not_due_again(self):
        mark_published(self.data, "video1", 1, "2026-11-02T12:00:00+01:00")
        self.assertIsNone(due_for_slot(self.data, "2026-11-02", "12:00"))

    def test_queue_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            save_queue(self.data, path)
            self.assertEqual(len(load_queue(path)["videos"]), 7)


if __name__ == "__main__":
    unittest.main()
