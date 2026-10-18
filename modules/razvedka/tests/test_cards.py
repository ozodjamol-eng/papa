import asyncio
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import PIL  # noqa: F401
except ImportError:                      # на сервере Pillow ставит задача razvedka-cards
    PIL = None

from razvedka import analyze, cards, store  # noqa: E402
from razvedka.collect import collect  # noqa: E402
try:
    from razvedka.telegram import bot_send_album  # noqa: E402
except ImportError:                      # локально без telethon
    bot_send_album = None
from test_razvedka import NOW, FakeSource  # noqa: E402


def sample():
    db = store.connect(":memory:")
    asyncio.run(collect(FakeSource(), db, {"first_days": 10, "refresh_days": 3, "pause_seconds": 0},
                        log=lambda *_: None))
    return analyze.analyze(db, days=7, now=NOW)


class CardsTest(unittest.TestCase):
    def test_advice_never_night(self):
        a = {"hours": [{"key": h, "posts": 100, "strength": 1.5 if h == 3 else (1.1 if h == 20 else 1.0)}
                       for h in range(24)],
             "weekdays": [], "media": [], "ad_hours": {}}
        adv = cards.advice(a)
        self.assertIn("20:00", adv[0])
        self.assertNotIn("03:00", adv[0])
        self.assertIn("ночью не публикуем", adv[1])

    def test_clean_strips_emoji(self):
        self.assertEqual(cards.clean("🛡 Зарарли ⚡ APK"), "Зарарли APK")

    @unittest.skipIf(PIL is None, "нет Pillow")
    def test_render_four_png(self):
        imgs = cards.render_cards(sample())
        self.assertEqual(len(imgs), 4)
        for b in imgs:
            self.assertTrue(b.startswith(b"\x89PNG"))

    def test_caption_limit(self):
        self.assertLessEqual(len(cards.caption(sample())), 1024)

    @unittest.skipIf(bot_send_album is None, "нет telethon")
    def test_album_multipart(self):
        seen = {}

        class R:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps({"ok": True}).encode()

        def fake(req, timeout=0):
            seen["url"], seen["body"] = req.full_url, req.data
            return R()
        self.assertTrue(bot_send_album("T", -1001, [b"img1", b"img2"], "cap", urlopen=fake))
        self.assertTrue(seen["url"].endswith("/sendMediaGroup"))
        self.assertIn(b"attach://p1", seen["body"])
        self.assertIn(b"img2", seen["body"])


if __name__ == "__main__":
    unittest.main()
