"""30.10: вечерний пул — отбор Pixabay и фон по кругу."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from razvedka import evening


def hit(i, tags="sunset, sky", dur=20, w=1920, h=1080):
    return {"id": i, "tags": tags, "duration": dur,
            "videos": {"medium": {"url": f"https://x/{i}.mp4", "width": w, "height": h}}}


class TestEvening(unittest.TestCase):
    def test_no_people_and_duration(self):
        self.assertTrue(evening.ok(hit(1)))
        self.assertFalse(evening.ok(hit(2, tags="sunset, woman, beach")))
        self.assertFalse(evening.ok(hit(3, dur=4)))
        self.assertFalse(evening.ok(hit(4, w=640, h=360)))           # мелкое — нет

    def test_vertical_preferred(self):
        h = {"id": 5, "tags": "sky", "duration": 15, "videos": {
            "large": {"url": "L", "width": 3840, "height": 2160},
            "medium": {"url": "M", "width": 1080, "height": 1920}}}
        self.assertEqual(evening.best_file(h)["url"], "M")

    def test_season_and_pick_rotates(self):
        self.assertEqual(evening.season(dt.date(2026, 10, 30)), "kuz")
        self.assertEqual(evening.season(dt.date(2026, 12, 1)), "qish")
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for n in (1, 2, 3):
                (d / f"kuz-{n}.mp4").write_bytes(b"x")
            (d / "qish-9.mp4").write_bytes(b"x")
            a = evening.pick(dt.date(2026, 10, 30), d)
            b = evening.pick(dt.date(2026, 10, 31), d)
            self.assertNotEqual(a, b)
            self.assertTrue(a.name.startswith("kuz-"))
            self.assertIsNone(evening.pick(dt.date(2026, 10, 30), d / "нет"))


if __name__ == "__main__":
    unittest.main()
