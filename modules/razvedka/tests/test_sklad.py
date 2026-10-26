"""26.10: 📦 склады владельца — доверенный материал, сам по сетке с вето."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import sklad  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=5))
MORNING = dt.datetime(2026, 10, 26, 8, 0, tzinfo=TZ)
NOON = dt.datetime(2026, 10, 26, 12, 30, tzinfo=TZ)
EVENING = dt.datetime(2026, 10, 26, 17, 0, tzinfo=TZ)


def it(i, kind="video", text="Фойдали маслаҳат", days=100, ad=False):
    return {"id": i, "ids": [i], "kind": kind, "text": text, "date": MORNING - dt.timedelta(days=days), "ad": ad}


class TestSklad(unittest.TestCase):
    def test_daily_quota_split_over_three_runs(self):
        self.assertEqual(sklad.allowed_now("davra", 0, MORNING), 2)       # 4 → 2 + 1 + 1
        self.assertEqual(sklad.allowed_now("davra", 2, NOON), 1)
        self.assertEqual(sklad.allowed_now("davra", 3, EVENING), 1)
        self.assertEqual(sklad.allowed_now("davra", 4, EVENING), 0)
        self.assertEqual(sklad.allowed_now("paparazzi", 0, MORNING), 2)   # 4 → 2 + 1 + 1
        self.assertEqual(sklad.allowed_now("davra", 0, EVENING), 4)       # утром не вышло — вечером догоняем

    def test_eligible_media_fresh_policy(self):
        self.assertTrue(sklad.eligible(it(1), "ФОЙДАЛИК", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, kind=None), "ФОЙДАЛИК", "davra", MORNING))       # голая ссылка/текст
        self.assertFalse(sklad.eligible(it(1, ad=True), "ФОЙДАЛИК", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, days=3), "NEWS INBOX", "davra", MORNING))       # старая новость
        self.assertTrue(sklad.eligible(it(1, days=1), "NEWS INBOX", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, days=1, text="Президент парламентда сўзлади"), "NEWS INBOX", "davra", MORNING))
        self.assertTrue(sklad.eligible(it(1, days=1, text="Президент парламентда сўзлади"), "NEWS INBOX", "xojaobod", MORNING))

    def test_plan_round_robin_once_and_opposite_ends(self):
        stashes = {"ФОЙДАЛИК": [it(i) for i in range(1, 11)], "РАЗВЛЕКАТЕЛЬНО": [it(i) for i in range(100, 103)],
                   "Jonlik ijrolar": [it(i) for i in range(200, 205)]}
        p = sklad.plan(stashes, {}, {}, EVENING)
        self.assertEqual([(s, x["id"]) for s, x in p["davra"]],
                         [("ФОЙДАЛИК", 1), ("РАЗВЛЕКАТЕЛЬНО", 100), ("ФОЙДАЛИК", 2), ("РАЗВЛЕКАТЕЛЬНО", 101)])
        self.assertEqual([x["id"] for _, x in p["xojaobod"]], [10, 9, 8])     # Хўжаобод — с конца архива
        self.assertEqual([(s, x["id"]) for s, x in p["paparazzi"]],
                         [("ФОЙДАЛИК", 6), ("Jonlik ijrolar", 202), ("ФОЙДАЛИК", 7), ("Jonlik ijrolar", 203)])  # с середины
        used = {"davra|ФОЙДАЛИК": ["1", "2"]}
        p2 = sklad.plan(stashes, used, {"rr_davra": 1}, EVENING)
        self.assertEqual(p2["davra"][0], ("РАЗВЛЕКАТЕЛЬНО", stashes["РАЗВЛЕКАТЕЛЬНО"][0]))   # круг продолжается
        self.assertNotIn(1, [x["id"] for s, x in p2["davra"] if s == "ФОЙДАЛИК"])          # один раз

    def test_left_counts_hungriest_channel(self):
        stashes = {"ФОЙДАЛИК": [it(i) for i in range(1, 6)]}
        self.assertEqual(sklad.left(stashes, {"davra|ФОЙДАЛИК": ["1", "2", "3"]}, MORNING), {"ФОЙДАЛИК": 2})

    def test_titles_match_without_case_and_emoji(self):
        self.assertEqual(sklad._norm("📦 Фойдалик  овкат"), sklad._norm("ФОЙДАЛИК ОВКАТ"))


if __name__ == "__main__":
    unittest.main()
