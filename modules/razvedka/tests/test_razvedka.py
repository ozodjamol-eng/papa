import asyncio
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import analyze, report, store  # noqa: E402
from razvedka.collect import collect  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 14, 18, 0, tzinfo=UTC)


class FakeSource:
    """Имитирует Telegram: 3 канала, посты каждые 2 часа за 10 дней."""
    def __init__(self, fail_title=None):
        self.fail_title = fail_title
        self.calls = []

    async def channels(self, cfg):
        return [
            {"id": 1, "username": "big", "title": "Big News", "folder": "Новости", "is_own": 0, "subscribers": 500000},
            {"id": 2, "username": "small", "title": "Small Fun", "folder": "Шоу", "is_own": 0, "subscribers": 20000},
            {"id": 3, "username": "xojaobodcity24", "title": "Xo'jaobod City", "folder": "свои", "is_own": 1, "subscribers": 6649},
        ]

    async def messages(self, ch, since):
        self.calls.append((ch["id"], since))
        if ch["title"] == self.fail_title:
            raise RuntimeError("boom")
        base = {1: 20000, 2: 3000, 3: 900}[ch["id"]]
        for i in range(120):
            d = NOW - dt.timedelta(hours=2 * i)
            if d < since:
                break
            local_h = (d + dt.timedelta(hours=5)).hour
            boost = 3 if local_h in (20, 21) else 1          # вечер сильнее
            text = "Yangilik matni"
            if i % 10 == 0:
                text = "#reklama Chegirma! Murojaat: +998 90 123 45 67 @shopbot"
            yield {"id": 1000 - i, "date": d, "views": base * boost, "forwards": 1, "replies": 0,
                   "reactions": 5, "media": "video" if i % 3 == 0 else "photo", "text": text,
                   "is_forward": False, "grp": None}


def run(coro):
    return asyncio.run(coro)


class TestRazvedka(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        import razvedka.collect as col
        col.utcnow = lambda: NOW
        self.cfg = {"first_days": 7, "refresh_days": 3, "pause_seconds": 0}

    def test_collect_and_incremental(self):
        src = FakeSource()
        s = run(collect(src, self.db, self.cfg, log=lambda *_: None))
        self.assertEqual(s["channels"], 3)
        self.assertEqual(s["errors"], [])
        n1 = self.db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        self.assertEqual(n1, 3 * 85)  # 7 дней по 2 часа + текущий
        # повторный прогон: известные каналы — только refresh_days, без дублей
        src2 = FakeSource()
        run(collect(src2, self.db, self.cfg, log=lambda *_: None))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM posts").fetchone()[0], n1)
        self.assertTrue(all((NOW - since).days == 3 for _, since in src2.calls))

    def test_one_channel_error_does_not_stop_run(self):
        s = run(collect(FakeSource(fail_title="Small Fun"), self.db, self.cfg, log=lambda *_: None))
        self.assertEqual(len(s["errors"]), 1)
        ids = {r[0] for r in self.db.execute("SELECT DISTINCT channel_id FROM posts")}
        self.assertEqual(ids, {1, 3})

    def test_ad_detection(self):
        self.assertTrue(analyze.is_ad("#reklama Chegirma! +998 90 123 45 67", 1))
        self.assertTrue(analyze.is_ad("Скидка 30%! Заказ: @fastfood_bot", 1))
        self.assertFalse(analyze.is_ad("Bugun shaharda yomg'ir yog'di", 0))
        self.assertFalse(analyze.is_ad("Президент выступил с речью", 0))

    def test_analysis_finds_evening_and_ads(self):
        run(collect(FakeSource(), self.db, self.cfg, log=lambda *_: None))
        a = analyze.analyze(self.db, days=7, now=NOW)
        best = max((h for h in a["hours"] if h["strength"]), key=lambda h: h["strength"])
        self.assertIn(best["key"], (20, 21))
        big = next(c for c in a["channels"] if c["id"] == 1)
        self.assertEqual(big["median_views"], 20000)
        self.assertGreater(big["ads"], 0)
        self.assertAlmostEqual(big["err"], 4.0)
        self.assertEqual(a["channels"][0]["id"], 1)  # лидер по просмотрам первый

    def test_album_counts_once(self):
        now_s = NOW.isoformat()
        store.upsert_channel(self.db, {"id": 9, "username": "a", "title": "A", "folder": "x", "is_own": 0,
                                       "subscribers": 100}, now_s)
        for mid, v in ((1, 50), (2, 70), (3, 60)):
            store.upsert_post(self.db, {"channel_id": 9, "msg_id": mid, "date_utc": (NOW - dt.timedelta(days=2)).isoformat(),
                                        "views": v, "forwards": 0, "replies": 0, "reactions": 0, "media": "photo",
                                        "text_len": 0, "text": "", "links": 0, "is_forward": 0, "grp": 777}, now_s)
        posts, _ = analyze.load(self.db, 7, NOW)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["views"], 70)
        self.assertEqual(posts[0]["media"], "album")

    def test_report_renders(self):
        run(collect(FakeSource(), self.db, self.cfg, log=lambda *_: None))
        text = report.render(analyze.analyze(self.db, days=7, now=NOW))
        for part in ("ЛУЧШИЕ ЧАСЫ", "ЛИДЕРЫ", "СВОИ КАНАЛЫ", "РЕКЛАМА У КОНКУРЕНТОВ", "Big News"):
            self.assertIn(part, text)


if __name__ == "__main__":
    unittest.main()
