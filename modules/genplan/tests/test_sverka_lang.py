"""30.10 сверка, поток B: №6 короткая узбекская латиница → кириллица; №8 ИИ вернул русский — пост не выходит,
остаётся в очереди (+1 ч, не больше 2 раз), владельцу — строка «пост задержан»."""
import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import ai, plan, service, store, translit  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
RU = ("Сегодня в нашем городе прошло очень важное событие, и все жители были рады, что это наконец случилось. "
      "Если вы хотите узнать больше, читайте наш канал.")


class Short(unittest.TestCase):
    def test_short_uz_latin(self):
        self.assertEqual(translit.auto("Juma muborak!"), ("Жума муборак!", True))
        t, ok = translit.auto("Assalomu aleykum Juma murodbaxsh kun barchangizga")
        self.assertTrue(ok)
        self.assertTrue(t.startswith("Ассалому алейкум Жума"))
        self.assertEqual(translit.auto("Ko'p go'sht yeyapmiz")[0], "Кўп гўшт еяпмиз")

    def test_english_and_protected_untouched(self):
        for x in ("Happy birthday to you", "Breaking news", "iPhone 17 Pro Max", "PaparazziUZ", "OK",
                  "Follow @xojaobodcity24 https://t.me/xojaobodcity24", "#tabrik"):
            self.assertEqual(translit.auto(x), (x, False), x)

    def test_protect_kept_in_converted(self):
        t, ok = translit.auto("Juma muborak! @xojaobodcity24")
        self.assertTrue(ok)
        self.assertIn("@xojaobodcity24", t)


class Pub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, text, *a, **k):
        self.sent.append(text)
        return 1


class Held(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        self.cfg["channels"]["davra"]["mode"] = "shadow"
        self.cfg["channels"]["davra"]["publisher"] = "test"
        self.orig = ai.rewrite
        service.ERRORS.clear()

    def tearDown(self):
        ai.rewrite = self.orig
        service.ERRORS.clear()

    def run_one(self, mid, now):
        m = store.get(self.db, mid)
        return asyncio.run(service.publish_one(self.db, self.cfg, {}, {"test": Pub(), "bot": Pub()}, "davra", m, "12:00",
                                               now.date().isoformat(), log=lambda *_: None, now=now))

    def test_ai_still_russian_held_then_dropped(self):
        ai.rewrite = lambda db, text, title: RU                     # ИИ «перевёл», а текст всё ещё русский
        mid = store.add_material(self.db, -100777, 1, RU, False)
        now = plan.slot_time(dt.date(2026, 10, 19), "12:00")
        store.update(self.db, mid, channel="davra", rubric="Видео", status="queued", scheduled_at=now.isoformat())
        self.assertEqual(self.run_one(mid, now), service.HELD)
        m = store.get(self.db, mid)
        self.assertEqual((m["status"], m["scheduled_at"][11:16]), ("queued", "13:00"))
        self.assertTrue(any("пост задержан: текст не на узбекском" in e for e in service.ERRORS))
        self.assertEqual(self.run_one(mid, now + dt.timedelta(hours=1)), service.HELD)
        self.assertFalse(self.run_one(mid, now + dt.timedelta(hours=2)))    # третий раз — снят
        self.assertTrue(any("не вышел" in e for e in service.ERRORS))

    def test_tick_keeps_held_post_queued(self):
        ai.rewrite = lambda db, text, title: RU
        mid = store.add_material(self.db, -100777, 1, RU, False)
        now = plan.slot_time(dt.date(2026, 10, 19), "12:00")
        store.update(self.db, mid, channel="davra", rubric="Видео", status="queued", scheduled_at=now.isoformat())
        for c in ("davra", "xojaobod"):
            store.kv_set(self.db, f"hourly_v1:{c}", "done")
        out = asyncio.run(service.tick(self.db, self.cfg, {}, {"test": Pub(), "bot": Pub()}, now, log=lambda *_: None))
        self.assertEqual(store.get(self.db, mid)["status"], "queued")
        self.assertEqual(out["failed"], 0)


if __name__ == "__main__":
    unittest.main()
