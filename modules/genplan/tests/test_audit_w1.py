"""30.10 полный аудит (W1): тихое окно Жумы при публикации, КАТТА ДАВРА без рекламы в дайджесте,
done-файл заказа читаем ассистентом, заказ на N дней — кнопка «по заказу», предпросмотр без «новостей»."""
import asyncio
import datetime as dt
import inspect
import json
import os
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import adsin, digest, hub, namaz, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
FRI = dt.date(2026, 10, 23)


def at(hhmm, day=FRI):
    return plan.slot_time(day, hhmm)


async def fake_publish(db, cfg, env, pubs, channel, m, slot, day, log=print, now=None):
    store.update(db, m["id"], status="published")
    store.pulse_add(db, channel, now, "ad" if smart.is_ad_rubric(m["rubric"]) else "bot")
    return True


class Juma(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        namaz.setup(self.db)
        self.n = 0
        self.cfg = {**CFG, "channels": {k: dict(v) for k, v in CFG["channels"].items()}}
        for c in self.cfg["channels"]:
            self.cfg["channels"][c].pop("hour_rubrics", None)
            self.cfg["channels"][c]["mode"] = "shadow"
            store.kv_set(self.db, f"hourly_v1:{c}", "done")
        self.db.execute("INSERT INTO namaz_locks(channel,day,start,end) VALUES (?,?,?,?)",
                        ("xojaobod", FRI.isoformat(), at("12:25").isoformat(), at("13:20").isoformat()))
        self.orig_pub, self.orig_nz = service.publish_one, service.tick_namaz
        service.publish_one = fake_publish

        async def no_namaz(*a, **k):
            return 0
        service.tick_namaz = no_namaz

    def tearDown(self):
        service.publish_one, service.tick_namaz = self.orig_pub, self.orig_nz

    def add(self, rubric="Видео", t=None, urgent=0, locked=0):
        self.n += 1
        mid = store.add_material(self.db, -100777, self.n, f"Пост {self.n}", False)
        store.update(self.db, mid, channel="xojaobod", rubric=rubric, status="queued", urgent=urgent, locked=locked,
                     scheduled_at=t.isoformat() if t else None)
        return mid

    def tick(self, hhmm):
        return asyncio.run(service.tick(self.db, self.cfg, {}, {}, at(hhmm), log=lambda *_: None))

    def st(self, mid):
        r = store.get(self.db, mid)
        return r["status"], dt.datetime.fromisoformat(r["scheduled_at"]).strftime("%H:%M")

    def test_post_in_window_waits(self):
        p = self.add(t=at("12:30"), locked=1)                     # поставлен заранее (за 2–3 дня) на пятницу
        self.tick("12:30")
        self.assertEqual(self.st(p), ("queued", "13:21"))
        self.tick("13:21")
        self.assertEqual(self.st(p)[0], "published")

    def test_urgent_and_ad_wait_too(self):
        u = self.add(t=at("12:40"), urgent=1)
        a = self.add(rubric="Реклама", t=at("12:40"), locked=1)
        self.tick("12:40")
        self.assertEqual(self.st(u), ("queued", "13:21"))
        self.assertEqual(self.st(a), ("queued", "13:21"))

    def test_collision_defer_not_into_window(self):
        store.pulse_add(self.db, "xojaobod", at("12:18"), "bot")
        p = self.add(t=at("12:20"))
        later = smart.collision_defer(self.db, self.cfg, "xojaobod", store.get(self.db, p), at("12:20"))
        self.assertEqual(f"{later:%H:%M}", "13:21")                # +10 попало бы в 12:28 — внутрь окна

    def test_outside_window_unchanged(self):
        self.assertIsNone(smart.lock_end(self.db, "xojaobod", at("12:24")))
        self.assertIsNone(smart.lock_end(self.db, "davra", at("12:30")))


class DavraDigest(unittest.TestCase):
    def test_no_ad_in_davra_caption(self):
        cw = {"Тошкент": {"max": 15, "min": 5, "code": 1}}
        cap = digest.compose_davra(FRI, cw, {}, [], "")
        self.assertNotIn("@Ozodjamol", cap)
        self.assertNotIn("Реклама", cap)

    def test_build_passes_empty_ad(self):
        src = inspect.getsource(digest)
        self.assertNotIn('compose_davra(day, cw, r, news, os.environ.get("DIGEST_AD_TEXT"))', src)

    def test_preview_no_news_count(self):
        sent = []

        class B:
            def __call__(self, method, **p):
                sent.append(p.get("text", ""))
                return {}
        old = digest.NEWS_IN_DIGEST
        try:
            digest.NEWS_IN_DIGEST = False
            digest.preview({"OWNER_IDS": "1"}, {"status": "READY", "news": 0}, B(),
                           davra={"status": "READY", "news": 0})
        finally:
            digest.NEWS_IN_DIGEST = old
        self.assertTrue(sent)
        self.assertFalse(any("новостей" in t for t in sent))


class Orders(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.inbox = Path(tempfile.mkdtemp())

    def mat(self, days):
        mid = store.add_material(self.db, -100777, 1, "Реклама", False)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued",
                     scheduled_at=at("15:00").isoformat())
        store.kv_set(self.db, f"ad_order_{mid}", json.dumps({"id": "o1", "days": days}))
        return mid

    def test_done_file_readable_by_assistant(self):
        mid = self.mat(1)
        self.assertTrue(adsin.published(self.db, CFG, mid, 777, inbox=self.inbox))
        f = self.inbox / "done-o1.json"
        self.assertEqual(os.stat(f).st_mode & 0o777, 0o664)

    def test_ordered_days_button(self):
        mid = self.mat(3)
        rows = hub.kb_queued(self.db, CFG, store.get(self.db, mid), at("10:00"))
        btns = [b for r in rows for b in r]
        b = next(b for b in btns if "по заказу" in b["text"])
        self.assertEqual(b["callback_data"], f"pk:{mid}:3")

    def test_single_day_order_plain(self):
        mid = self.mat(1)
        rows = hub.kb_queued(self.db, CFG, store.get(self.db, mid), at("10:00"))
        self.assertFalse(any("по заказу" in b["text"] for r in rows for b in r))


if __name__ == "__main__":
    unittest.main()
