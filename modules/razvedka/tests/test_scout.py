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
