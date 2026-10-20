"""20.10: перенос из GENPLAN 5 — ☀️ погода и курс 07:00, 🌙 Якуний пост 22:00 каждый день, 📣 реклама на N дней."""
import asyncio
import datetime as dt
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import extras, hub, plan, service, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
CFG["channels"]["xojaobod"]["mode"] = "live"
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}
TZ = plan.TZ


def at(hm, day=dt.date(2026, 10, 21)):
    h, m = map(int, hm.split(":"))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)


class Acc:
    def __init__(self):
        self.sent = []

    async def publish(self, chat, body, hub_chat=None, hub_msg=None, has_media=False):
        self.sent.append((chat, body, hub_chat, hub_msg, has_media)); return 77

    async def publish_album(self, chat, hub_chat, ids, body):
        self.sent.append((chat, body, hub_chat, ids)); return 78


class BotPub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, body, hub_chat=None, hub_msg=None, has_media=False, button=None):
        self.sent.append((chat, body)); return 5


W = {"Хўжаобод": {"t": 10, "code": 0, "night": False}}
R = {"USD": {"rate": 12044.72}, "EUR": {"rate": 13525.02}}


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(str(Path(tempfile.mkdtemp()) / "g.db"))
        self.pubs = {"account": Acc(), "bot": BotPub()}
        service.ERRORS.clear()

    def tick(self, now, fetch=None):
        return asyncio.run(service.tick_extras(self.db, CFG, ENV, self.pubs, now, lambda *_: None, fetch=fetch))

    def test_info_text_like_genplan5(self):
        t = extras.info_text(CFG["channels"]["xojaobod"], W, R, dt.date(2026, 10, 21))
        self.assertTrue(t.startswith("#ОБ_ҲАВО"))
        self.assertIn("Хўжаободда ҳаво: 10°С, очиқ", t)
        self.assertIn("USD: 12044.72 сўм | EUR: 13525.02 сўм", t)
        self.assertIn("@XOJAOBODCITY24", t)
        self.assertIsNone(extras.info_text(CFG["channels"]["xojaobod"], None, None, dt.date(2026, 10, 21)))

    def test_info_published_0700_by_account(self):
        from genplan import digest
        orig = (digest.weather, digest.rates)
        digest.weather, digest.rates = (lambda get: W), (lambda get: R)
        self.addCleanup(lambda: (setattr(digest, "weather", orig[0]), setattr(digest, "rates", orig[1])))
        self.assertEqual(self.tick(at("06:59")), 0)
        self.assertEqual(self.tick(at("07:00")), 1)
        chat, body, *_ = self.pubs["account"].sent[0]
        self.assertEqual(chat, "@xojaobodcity24")
        self.assertIn("💱", body)
        self.assertEqual(self.tick(at("07:05")), 0)                   # один раз в день

    def test_no_false_missed_on_start(self):
        self.tick(at("15:00"))                                         # служба запущена днём — 07:00 не «пропущен»
        self.assertEqual(service.ERRORS, [])

    def test_final_post_every_day_until_replaced(self):
        mid = store.add_material(self.db, -100777, 55, "#муфтий_минбари\n\nТарози босувчи икки калима", True)
        store.update(self.db, mid, channel="xojaobod")
        extras.final_set(self.db, "xojaobod", store.get(self.db, mid))
        self.assertEqual(store.get(self.db, mid)["status"], "rejected")     # не ждёт обычной публикации
        for day in (dt.date(2026, 10, 21), dt.date(2026, 10, 22)):
            self.assertEqual(self.tick(at("22:00", day)), 1)
        self.assertEqual(len(self.pubs["account"].sent), 2)
        chat, body, hub_chat, hub_msg, media = self.pubs["account"].sent[1]
        self.assertEqual((chat, hub_chat, hub_msg, media), ("@xojaobodcity24", -100777, 55, True))
        self.assertTrue(body.startswith("#муфтий_минбари"))

    def test_ad_package_daily_same_time(self):
        mid = store.add_material(self.db, -100777, 60, "🔥 ЎТИНЛАР СОТИЛАДИ!", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        c = extras.campaign_from(self.db, store.get(self.db, mid), 3)
        self.assertIn("3 кун · ҳар куни 17:30 · 21.10–23.10", extras.campaign_note(c))
        self.assertEqual(extras.ensure_campaigns(self.db, at("08:00")), [])          # день 1 — сам исходный пост
        for d in (22, 23):
            made = extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, d)))
            self.assertEqual(len(made), 1)
            m = store.get(self.db, made[0])
            self.assertEqual((m["status"], m["rubric"], m["hub_msg"], m["locked"]), ("queued", "Реклама", 60, 1))
            self.assertEqual(m["scheduled_at"][11:16], "17:30")
            self.assertEqual(extras.ensure_campaigns(self.db, at("09:00", dt.date(2026, 10, d))), [])   # не дублирует
        self.assertEqual(extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 24))), [])    # пакет кончился
        self.assertEqual(self.db.execute("SELECT status FROM ad_campaigns").fetchone()[0], "done")

    def test_pult_buttons(self):
        mid = store.add_material(self.db, -100777, 61, "Реклама матни", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        _, kb = hub.card(self.db, CFG, mid, at("08:00"))
        self.assertIn("pk:", json.dumps(kb))
        self.assertIn("Якуний пост", hub.rubrics(CFG, "xojaobod"))


if __name__ == "__main__":
    unittest.main()
