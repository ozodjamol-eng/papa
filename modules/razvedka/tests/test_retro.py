import unittest
from razvedka import retro


class TestRetro(unittest.TestCase):
    def test_pick_filters_and_sorts(self):
        items = [
            {"id": "a", "title": "A", "viewCount": 5_000_000, "duration": "00:03:40", "channelName": "X"},
            {"id": "b", "title": "B", "viewCount": 900_000, "duration": "00:03:40"},          # мало просмотров
            {"id": "c", "title": "C", "viewCount": 9_000_000, "duration": "01:10:00"},         # длинный сборник
            {"id": "d", "title": "D", "viewCount": "12,345,678 views", "duration": "4:05"},
            {"id": "e", "title": "E", "viewCount": 7_000_000, "duration": "00:03:00"},         # уже присылали
            {"id": "a", "title": "A2", "viewCount": 5_000_000, "duration": "00:03:40"},        # дубль
        ]
        got = retro.pick(items, {"e"})
        self.assertEqual([p["id"] for p in got], ["d", "a"])
        self.assertEqual(got[0]["sec"], 245)

    def test_card(self):
        t = retro.card([{"id": "a", "title": "Song", "views": 5_000_000, "sec": 220, "channel": "X", "url": "https://www.youtube.com/watch?v=a"}], "12.11")
        self.assertIn("5.0 млн", t); self.assertIn("ҚИДИРУВ", t); self.assertIn("3:40", t); self.assertIn("watch?v=a", t)


if __name__ == "__main__":
    unittest.main()
