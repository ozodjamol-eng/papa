"""📣 30.10 владелец, протокол «реклама → закрывающий пост»: реклама держится 10 мин, потом сразу пост,
чтобы реклама не висела до следующего часа (было: 19:30 реклама → 20:00 пост, полчаса висела)."""
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


def at(hhmm):
    return plan.slot_time(MON, hhmm)


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

    def add(self, rubric="Видео", t=None, locked=0, status="queued", stock=0):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, f"Пост {self.n}", False)
        store.update(self.db, mid, channel="xojaobod", rubric=rubric, status=status, locked=locked, stock=stock,
                     scheduled_at=t.isoformat() if t else None)
        return mid

    def st(self, mid):
        return store.get(self.db, mid)["status"]

    def tick(self, hhmm):
        return asyncio.run(service.tick(self.db, self.cfg, {}, {}, at(hhmm), log=lambda *_: None))

    def test_ad_1930_closed_at_1940(self):
        ad = self.add(rubric="Реклама", t=at("19:30"), locked=1)
        nxt = self.add(t=at("20:00"))
        self.tick("19:30")
        self.assertEqual(self.st(ad), "published")
        self.tick("19:35")
        self.assertEqual(self.st(nxt), "queued")                  # 10 минут реклама держится
        self.tick("19:40")
        self.assertEqual(self.st(nxt), "published")               # и сразу закрывающий пост

    def test_from_stock_when_queue_empty(self):
        self.add(rubric="Реклама", t=at("19:30"), locked=1)
        s = self.add(rubric="Ҳажвия", status="draft", stock=1)
        self.tick("19:30")
        self.tick("19:40")
        self.assertEqual(self.st(s), "published")

    def test_locked_not_pulled(self):
        self.add(rubric="Реклама", t=at("19:30"), locked=1)
        mine = self.add(t=at("20:00"), locked=1)                  # время выбрал владелец — не трогаем
        self.tick("19:30")
        self.tick("19:40")
        self.assertEqual(self.st(mine), "queued")

    def test_on_the_hour_ad_uses_plus_10(self):
        p = self.add(t=at("15:00"))
        nxt = self.add(t=at("16:00"))
        self.add(rubric="Реклама", t=at("15:00"), locked=1)
        self.tick("15:00")
        self.tick("15:01")
        self.tick("15:10")
        self.assertEqual(self.st(p), "published")
        self.tick("15:11")
        self.assertEqual(self.st(nxt), "queued")                  # закрыто — следующий час не трогаем

    def test_grid_post_soon_nothing_pulled(self):
        self.add(rubric="Реклама", t=at("19:45"), locked=1)
        nxt = self.add(t=at("20:00"))
        self.tick("19:45")
        self.tick("19:55")
        self.assertEqual(self.st(nxt), "queued")                  # через 5 мин и так выйдет
        self.tick("20:00")
        self.assertEqual(self.st(nxt), "published")


ORIG = service.publish_one

if __name__ == "__main__":
    unittest.main()
