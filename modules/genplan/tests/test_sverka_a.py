"""30.10 сверка, поток A: №5 две рекламы подряд, №9 умное время рекламы и дайджест, №10 лимит 20 в день,
№14 исходное время для Стража (planned_at)."""
import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
MON = dt.date(2026, 10, 19)


def at(hhmm, day=MON):
    return plan.slot_time(day, hhmm)


async def fake_publish(db, cfg, env, pubs, channel, m, slot, day, log=print, now=None):
    store.update(db, m["id"], status="published")
    store.pulse_add(db, channel, now, "ad" if smart.is_ad_rubric(m["rubric"]) else "bot")
    return True


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.n = 0
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        for c in ("davra", "xojaobod"):
            self.cfg["channels"][c].pop("hour_rubrics", None)
            self.cfg["channels"][c]["mode"] = "shadow"
            store.kv_set(self.db, f"hourly_v1:{c}", "done")
        service.publish_one = fake_publish

    def tearDown(self):
        service.publish_one = ORIG

    def add(self, rubric="Видео", t=None, locked=0, status="queued", stock=0, ch="xojaobod"):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, f"Пост {self.n}", False)
        store.update(self.db, mid, channel=ch, rubric=rubric, status=status, locked=locked, stock=stock,
                     scheduled_at=t.isoformat() if t else None)
        return mid

    def st(self, mid):
        return store.get(self.db, mid)["status"]

    def when(self, mid):
        return dt.datetime.fromisoformat(store.get(self.db, mid)["scheduled_at"]).strftime("%H:%M")

    def tick(self, hhmm):
        return asyncio.run(service.tick(self.db, self.cfg, {}, {}, at(hhmm), log=lambda *_: None))

    # №5
    def test_two_ads_same_time_second_waits_10(self):
        a1 = self.add(rubric="Реклама", t=at("15:00"), locked=1)
        a2 = self.add(rubric="Реклама", t=at("15:00"), locked=1)
        self.tick("15:00")
        self.assertEqual((self.st(a1), self.st(a2)), ("published", "queued"))
        self.tick("15:00")
        self.assertEqual(self.st(a2), "queued")
        self.assertEqual(self.when(a2), "15:10")                   # первая держит свои 10 минут
        self.tick("15:10")
        self.assertEqual(self.st(a2), "published")

    # №9
    def test_ad_smart_time_keeps_off_digest(self):
        ch = self.cfg["channels"]["xojaobod"]
        ch["digest"] = {"live": True, "at": "20:30", "until": "22:00"}
        busy = smart.occupied(self.db, "xojaobod", at("19:00"), ch=ch, grid_posts=False)
        self.assertIn(at("20:30"), busy)
        self.assertFalse(smart.is_free(ch, at("20:25"), busy))     # вплотную перед дайджестом — нет
        self.assertTrue(smart.is_free(ch, at("19:30"), busy))

    # №10
    def test_day_limit_blocks_stock_only(self):
        for i in range(20):
            store.pulse_add(self.db, "davra", at("07:00") + dt.timedelta(minutes=30 * i), "bot")
        self.assertEqual(smart.day_room(self.db, self.cfg, "davra", at("17:00")), 0)
        s = self.add(rubric="Видео", status="draft", stock=1, ch="davra")
        self.assertEqual(smart.fill_from_stock(self.db, self.cfg, "davra", at("17:00")), [])
        self.assertEqual(self.st(s), "draft")
        mine = self.add(t=at("18:00"), ch="davra", locked=1)       # владелец выбрал — выходит
        self.tick("18:00")
        self.assertEqual(self.st(mine), "published")

    def test_day_limit_xojaobod_counts_only_posts(self):
        for i in range(10):
            store.pulse_add(self.db, "xojaobod", at("07:00") + dt.timedelta(minutes=30 * i), "namaz")
            store.pulse_add(self.db, "xojaobod", at("07:05") + dt.timedelta(minutes=30 * i), "ad")
        self.assertEqual(smart.day_room(self.db, self.cfg, "xojaobod", at("13:00")), 20)

    def test_ad_closer_respects_limit(self):
        for i in range(20):                                          # 20 обычных постов — лимит дня
            store.pulse_add(self.db, "xojaobod", at("07:00") + dt.timedelta(minutes=30 * i), "bot")
        self.add(rubric="Реклама", t=at("19:30"), locked=1)
        s = self.add(rubric="Ҳажвия", status="draft", stock=1)
        self.tick("19:30")
        self.tick("19:40")
        self.assertEqual(self.st(s), "draft")                       # лимит — запас не трогаем

    # №14
    def test_planned_at_kept_on_auto_move(self):
        p = self.add(t=at("15:00"))
        self.assertEqual(store.get(self.db, p)["planned_at"], at("15:00").isoformat())
        store.update(self.db, p, scheduled_at=at("15:10").isoformat())          # авто +10
        self.assertEqual(store.get(self.db, p)["planned_at"], at("15:00").isoformat())
        store.update(self.db, p, status="queued", scheduled_at=at("17:00").isoformat(), urgent=0, locked=1)  # владелец
        self.assertEqual(store.get(self.db, p)["planned_at"], at("17:00").isoformat())
        store.update(self.db, p, status="draft", scheduled_at=None)
        self.assertIsNone(store.get(self.db, p)["planned_at"])


ORIG = service.publish_one

if __name__ == "__main__":
    unittest.main()
