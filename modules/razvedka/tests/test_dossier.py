"""17.10: досье больших каналов — режим дня, сильное/слабое, сравнение с нашими, предложения."""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from razvedka import collect as col, dossier, store  # noqa: E402
from razvedka.collect import collect  # noqa: E402
from test_razvedka import NOW, FakeSource  # noqa: E402


class Dossier(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self._u = col.utcnow
        col.utcnow = lambda: NOW
        self.addCleanup(setattr, col, "utcnow", self._u)
        asyncio.run(collect(FakeSource(), self.db, {"first_days": 10, "refresh_days": 3, "pause_seconds": 0}, log=lambda *_: None))

    def test_build_and_render(self):
        d = dossier.build(self.db, days=10, now=NOW)
        self.assertEqual([r["title"] for r in d["leaders"]], ["Big News", "Small Fun"])     # по подписчикам
        self.assertEqual([r["title"] for r in d["own"]], ["Xo'jaobod City"])
        big = d["leaders"][0]
        self.assertEqual(big["per_day"], 10.8)                      # посты каждые 2 ч, без рекламы
        self.assertEqual(big["gap"], 120)
        self.assertIn(21, [h for h, _ in big["best_hours"]])        # вечер сильнее (×3)
        t = dossier.render(d)
        self.assertIn("ДОСЬЕ БОЛЬШИХ КАНАЛОВ", t)
        self.assertIn("💪 Сильные часы", t)
        self.assertIn("🏠 МЫ", t)
        self.assertIn("сетку меняем только после вашего ✅", t)
        self.assertNotIn("reklama", t.lower())                      # реклама — не их контент

    def test_advice_compares(self):
        leaders = [{"first": "05:00", "per_day": 20, "empty_hours": [14, 15], "best_hours": [(20, 1.8)], "media": [("video", 1.5, 9)]},
                   {"first": "05:20", "per_day": 18, "empty_hours": [14], "best_hours": [(20, 1.4)], "media": [("video", 1.3, 9)]}]
        own = [{"title": "КАТТА ДАВРА", "first": "06:30", "per_day": 8, "gap": 15}]
        a = "\n".join(dossier.advice(leaders, own))
        self.assertIn("первый пост у лидеров ~05:10, у нас ~06:30", a)
        self.assertIn("постов в день", a)
        self.assertIn("слишком плотно", a)
        self.assertIn("14:00", a)
        self.assertIn("20:00", a)
        self.assertIn("видео", a)


if __name__ == "__main__":
    unittest.main()
