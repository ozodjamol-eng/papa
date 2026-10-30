import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import insta  # noqa: E402


def reel(code, owner, views, dur=30):
    return {"shortCode": code, "ownerUsername": owner, "videoPlayCount": views, "videoUrl": "u", "videoDuration": dur}


class T(unittest.TestCase):
    def test_choose(self):
        st = {"views": {"a": [10000, 12000, 11000]}, "seen": ["old"]}
        items = [reel("x1", "a", 60000), reel("x2", "a", 70000), reel("old", "b", 900000), reel("x3", "c", 5000),
                 reel("x4", "d", 50000, dur=400)]
        got = [x["_code"] for x in insta.choose(items, st, 4, 20000, 1.3)]
        self.assertEqual(got, ["x2"])                 # один от автора, лучший; старый/слабый/длинный — нет
        self.assertIn(70000, st["views"]["a"])

    def test_apify_request(self):
        seen = []
        out = insta.apify_reels(["a", "b"], 3, "tok", http=lambda req: seen.append(req) or [{"shortCode": "z"}])
        self.assertEqual(out[0]["shortCode"], "z")
        self.assertIn(b'"resultsLimit": 3', seen[0].data)
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer tok")


class Learn(unittest.TestCase):
    def test_learn_and_fresh(self):
        import datetime as dt
        st = {}
        items = [{"ownerUsername": "A", "videoPlayCount": 50000}, {"ownerUsername": "a", "videoPlayCount": 90000},
                 {"ownerUsername": "b", "videoPlayCount": 99000}, {"ownerUsername": "c", "videoPlayCount": 100}]
        self.assertEqual(insta.learn(st, items), ["a"])
        now = dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc)
        f = insta.fresh([{"timestamp": "2026-10-29T10:00:00.000Z"}, {"timestamp": "2026-10-01T10:00:00Z"}, {}], now)
        self.assertEqual(len(f), 2)


class Footer(unittest.TestCase):
    def test_footer(self):
        f = insta.footer("music", "xayrshou", 2175972)
        self.assertTrue(f.startswith(insta.MARK))
        self.assertIn("PaparazziUZ", f)
        self.assertIn("рубрика: Қўшиқ", f)
        self.assertIn("2.2 млн", f)
