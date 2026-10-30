"""⏱ Часовая сетка (25.10 владелец): посты из рубрик — по одному в час ровно в :00 (07:00–22:00).
Протоколы и реклама — вне сетки. Срочный — сразу. Совпало — плановый через 10 минут, сетка не сдвигается.
Работает в КАТТА ДАВРА и Хўжаобод, PaparazziUZ — по-старому."""
import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import extras, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
MON = dt.date(2026, 10, 19)


def at(hhmm, day=MON):
    return plan.slot_time(day, hhmm)


class Pub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, text, *a, **k):
        self.sent.append(text)
        return 1000 + len(self.sent)


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.n = 0
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        self.cfg["channels"]["davra"]["mode"] = "shadow"

    def add(self, rubric="Видео", t=None, ch="davra", urgent=0, locked=0, status="queued"):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, f"Пост {self.n}", False)
        store.update(self.db, mid, channel=ch, rubric=rubric, status=status, urgent=urgent, locked=locked,
                     scheduled_at=t.isoformat() if t else None)
        return mid

    def when(self, mid):
        return dt.datetime.fromisoformat(store.get(self.db, mid)["scheduled_at"]).strftime("%H:%M")

    def test_config(self):
        self.assertTrue(smart.hourly(CFG["channels"]["davra"]))
        self.assertTrue(smart.hourly(CFG["channels"]["xojaobod"]))
        self.assertIsNone(smart.hourly(CFG["channels"]["paparazzi"]))
        hs = smart.hour_slots(CFG["channels"]["davra"], MON)
        self.assertEqual((f"{hs[0]:%H:%M}", f"{hs[-1]:%H:%M}", len(hs)), ("07:00", "22:00", 16))

    def test_smart_time_next_free_hour(self):
        now = at("10:20")
        t, why = smart.smart_time(self.db, self.cfg, "davra", "Ҳажвия", now)
        self.assertEqual((f"{t:%H:%M}", why), ("11:00", "часовая сетка"))
        self.add(t=at("11:00"))
        self.add(t=at("12:10"))                       # сдвинутый после рекламы — час 12 тоже занят
        t, _ = smart.smart_time(self.db, self.cfg, "davra", "Ҳажвия", now)
        self.assertEqual(f"{t:%H:%M}", "13:00")

    def test_protocols_and_ads_dont_take_hours(self):
        smart_now = at("06:00")
        store.pulse_add(self.db, "davra", at("05:00"), "morning")
        self.add(rubric="Реклама", t=at("07:00"), locked=1)
        t, _ = smart.smart_time(self.db, self.cfg, "davra", "Видео", smart_now)
        self.assertEqual(f"{t:%H:%M}", "07:00")      # реклама в 07:00 час не занимает — пост уступит при выходе

    def test_night_and_tomorrow(self):
        for h in range(7, 23):
            self.add(t=at(f"{h:02d}:00"))
        t, _ = smart.smart_time(self.db, self.cfg, "davra", "Видео", at("09:00"))
        self.assertEqual(t, at("07:00", MON + dt.timedelta(days=1)))
        self.assertTrue(all(7 <= x.hour <= 22 for x in smart.other_times(self.db, self.cfg, "davra", "Видео", at("09:00"))))

    def test_ad_shift_ignores_grid(self):
        self.add(t=at("15:00"))
        self.assertTrue(smart.free_at(self.db, self.cfg, "xojaobod", at("15:00"), "Реклама", at("08:00")))
        self.assertFalse(smart.free_at(self.db, self.cfg, "davra", at("15:00"), "Видео", at("08:00")))
        self.assertEqual(extras.shift_time(self.db, self.cfg, "davra", at("15:00"), at("08:00")), at("15:00"))

    def test_urgent_doesnt_shift_grid(self):
        a, b = self.add(t=at("14:00")), self.add(t=at("15:00"))
        self.assertEqual(smart.shift_after_urgent(self.db, self.cfg, "davra", at("13:58"), at("13:58")), [])
        self.assertEqual((self.when(a), self.when(b)), ("14:00", "15:00"))

    def tick(self, now):
        for c in ("davra", "xojaobod"):
            store.kv_set(self.db, f"hourly_v1:{c}", "done")       # переход на сетку уже был
        return asyncio.run(service.tick(self.db, self.cfg, {}, {"bot": Pub(), "test": Pub()}, now, log=lambda *_: None))

    def test_ad_first_post_plus_10_grid_stays(self):
        p = self.add(t=at("15:00"))
        nxt = self.add(t=at("16:00"))
        ad = self.add(rubric="Реклама", t=at("15:00"), locked=1)
        service.publish_one = self._fake_publish
        try:
            self.tick(at("15:00"))
            self.assertEqual(store.get(self.db, ad)["status"], "published")     # реклама — первой
            self.assertEqual(store.get(self.db, p)["status"], "queued")
            self.tick(at("15:01"))
            self.assertEqual(self.when(p), "15:10")                               # плановый — через 10 минут
            self.tick(at("15:10"))
            self.assertEqual(store.get(self.db, p)["status"], "published")
            self.assertEqual(self.when(nxt), "16:00")                             # сетка не сдвинулась
        finally:
            service.publish_one = ORIG

    def test_urgent_or_protocol_then_post_plus_10(self):
        p = self.add(t=at("14:00"))
        store.pulse_add(self.db, "davra", at("13:57"), "bot")                   # срочный / протокол в 13:57
        service.publish_one = self._fake_publish
        try:
            self.tick(at("14:00"))
            self.assertEqual(self.when(p), "14:07")
            self.tick(at("14:07"))
            self.assertEqual(store.get(self.db, p)["status"], "published")
        finally:
            service.publish_one = ORIG

    def test_migrate_once(self):
        old = self.add(t=at("07:30"))
        old2 = self.add(t=at("08:15"))
        mine = self.add(t=at("09:45"), locked=1)                                # выбрано владельцем — не трогаем
        ad = self.add(rubric="Реклама", t=at("11:50"), locked=1)
        service.reconcile(self.db, self.cfg, at("06:00"))
        self.assertEqual((self.when(old), self.when(old2), self.when(mine), self.when(ad)), ("07:00", "08:00", "09:45", "11:50"))
        store.update(self.db, old, scheduled_at=at("10:00").isoformat())
        service.reconcile(self.db, self.cfg, at("06:00"))
        self.assertEqual(self.when(old), "10:00")                                # один раз

    def test_paparazzi_untouched(self):
        t, why = smart.smart_time(self.db, self.cfg, "paparazzi", "Қўшиқ", at("06:00"))
        self.assertNotEqual(why, "часовая сетка")

    def test_xojaobod_hour_rubrics_smart_time(self):
        # 30.10: кулги — в свой час 10:00, а не в ближайший свободный 07:00
        t, why = smart.smart_time(self.db, self.cfg, "xojaobod", "Ҳажвия", at("06:00"))
        self.assertEqual((f"{t:%H:%M}", why), ("10:00", "час рубрики «Ҳажвия»"))
        t, _ = smart.smart_time(self.db, self.cfg, "xojaobod", "Огоҳлантириш", at("06:00"))
        self.assertEqual(f"{t:%H:%M}", "17:00")
        self.assertIn("Огоҳлантириш", __import__("genplan.hub", fromlist=["x"]).rubrics(self.cfg, "xojaobod"))

    def test_xojaobod_stock_takes_only_hour_rubric(self):
        self.cfg["channels"]["xojaobod"]["mode"] = "shadow"
        fun = self.add(rubric="Ҳажвия", ch="xojaobod", status="draft")
        news = self.add(rubric="Янгиликлар", ch="xojaobod", status="draft")
        for m in (fun, news):
            store.update(self.db, m, stock=1, scheduled_at=None)
        used = smart.fill_from_stock(self.db, self.cfg, "xojaobod", at("08:40"))   # впереди часы 09 и 10
        self.assertEqual(sorted(used), sorted([fun, news]))
        self.assertEqual((self.when(news), self.when(fun)), ("09:00", "10:00"))   # 09 — запасная «Янгиликлар», 10 — кулги

    def test_xojaobod_no_match_leaves_hour_empty(self):
        fun = self.add(rubric="Ҳажвия", ch="xojaobod", status="draft")
        store.update(self.db, fun, stock=1, scheduled_at=None)
        used = smart.fill_from_stock(self.db, self.cfg, "xojaobod", at("12:20"))    # часы 13, 14 — польза/соғлиқ
        self.assertEqual(used, [])

    async def _fake_publish(self, db, cfg, env, pubs, channel, m, slot, day, log=print, now=None):
        store.update(db, m["id"], status="published")
        store.pulse_add(db, channel, now, "bot")
        return True


ORIG = service.publish_one

if __name__ == "__main__":
    unittest.main()
