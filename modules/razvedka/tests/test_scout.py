import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import scout  # noqa: E402


class T(unittest.TestCase):
    def test_rank(self):
        f = [{"id": 1, "title": "A", "username": "a", "broadcast": True, "subscribers": 90000, "q": "x"},
             {"id": 2, "title": "B", "username": "b", "broadcast": True, "subscribers": 500, "q": "x"},
             {"id": 3, "title": "Known", "username": "k", "broadcast": True, "subscribers": 900000, "q": "x"},
             {"id": 4, "title": "Group", "username": "g", "broadcast": False, "subscribers": 900000, "q": "x"},
             {"id": 5, "title": "Own", "username": "xojaobodcity24", "broadcast": True, "subscribers": 7000, "q": "x"},
             {"id": 1, "title": "A", "username": "a", "broadcast": True, "subscribers": 90000, "q": "y"}]
        r = scout.rank(f, {3}, {"xojaobodcity24"})
        self.assertEqual([x["id"] for x in r], [1])
        self.assertIn("90 000", scout.render(r))


class Humor(unittest.TestCase):
    def test_connect_once(self):
        ok = [{"id": 7, "title": "Fun", "username": "fun", "subscribers": 50000, "median_views": 9000}]
        bad = [({"id": 8, "title": "Logo", "username": "lg"}, "чужое лого 2/2")]
        d = scout.connect(None, ok, bad, "t")
        self.assertEqual(d["channels"]["davra"]["humor"][0]["found_by"], "scout")
        self.assertIn(8, d["humor_tried"])
        d2 = scout.connect(d, ok, [], "t")
        self.assertEqual(len(d2["channels"]["davra"]["humor"]), 1)          # повторно не добавляем
        self.assertIn("✅ Fun", scout.render_humor(ok, bad))
