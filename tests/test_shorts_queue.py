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

    def test_ramp_up_exactly_matches_requested_order(self):
        self.assertEqual(due_for_slot(self.data, "2026-11-01", "12:00")["video_id"], "video1")
        self.assertEqual(due_for_slot(self.data, "2026-11-01", "12:00")["short_number"], 1)
        self.assertIsNone(due_for_slot(self.data, "2026-11-01", "14:00"))

        day2_12 = due_for_slot(self.data, "2026-11-02", "12:00")
        day2_14 = due_for_slot(self.data, "2026-11-02", "14:00")
        self.assertEqual((day2_12["video_id"], day2_12["short_number"]), ("video1", 2))
        self.assertEqual((day2_14["video_id"], day2_14["short_number"]), ("video2", 1))

        day3 = [due_for_slot(self.data, "2026-11-03", slot) for slot in ["12:00", "14:00", "16:00"]]
        self.assertEqual([(x["video_id"], x["short_number"]) for x in day3],
                         [("video1", 3), ("video2", 2), ("video3", 1)])
        self.assertIsNone(due_for_slot(self.data, "2026-11-03", "18:00"))

    def test_fully_running_five_slots(self):
        expected = [
            ("12:00", "video1", 5),
            ("14:00", "video2", 4),
            ("16:00", "video3", 3),
            ("18:00", "video4", 2),
            ("20:00", "video5", 1),
        ]
        for slot, video_id, short_number in expected:
            result = due_for_slot(self.data, "2026-11-05", slot)
            self.assertEqual((result["video_id"], result["short_number"]), (video_id, short_number))

    def test_next_day_rolls_oldest_documentary_forward(self):
        result = due_for_slot(self.data, "2026-11-06", "12:00")
        self.assertEqual((result["video_id"], result["short_number"]), ("video2", 5))

    def test_published_short_is_not_due_again(self):
        mark_published(self.data, "video1", 1, "2026-11-01T12:00:00+01:00")
        self.assertIsNone(due_for_slot(self.data, "2026-11-01", "12:00"))

    def test_queue_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            save_queue(self.data, path)
            self.assertEqual(len(load_queue(path)["videos"]), 7)


if __name__ == "__main__":
    unittest.main()
