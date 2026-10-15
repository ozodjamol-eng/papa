import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import hub, plan, service, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}


class FakeBot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}


def post(mid, text="Янгилик @bugungi_gap", photo=True):
    p = {"message_id": mid, "chat": {"id": -100777}, "caption" if photo else "text": text}
    if photo:
        p["photo"] = [{}]
    return {"channel_post": p}


def cb(data, uid=42):
    return {"callback_query": {"id": "q", "from": {"id": uid}, "data": data, "message": {"chat": {"id": 42}, "message_id": 5}}}


class TestHub(unittest.TestCase):
    def setUp(self):
        self.db, self.bot = store.connect(":memory:"), FakeBot()

    def h(self, u):
        return hub.handle(self.bot, self.db, CFG, ENV, u)

    def test_two_taps_to_queue(self):
        self.assertEqual(self.h(post(10)), "material")
        self.assertEqual(self.h(post(10)), "dup")                       # повтор не дублирует
        self.h(cb("ch:1:x"))
        i = hub.rubrics(CFG, "xojaobod").index("Ҳажвия")
        self.h(cb(f"rb:1:{i}"))
        m = store.get(self.db, 1)
        self.assertEqual((m["channel"], m["rubric"], m["status"]), ("xojaobod", "Ҳажвия", "queued"))

    def test_both_channels_and_owner_only(self):
        self.h(post(11))
        self.assertEqual(self.h(cb("ch:1:b", uid=7)), "denied")
        self.h(cb("ch:1:b"))
        self.h(cb("rb:1:0"))
        self.h(cb(f"rb:2:{hub.rubrics(CFG, 'paparazzi').index('Видео')}"))
        rows = self.db.execute("SELECT channel, status FROM materials ORDER BY id").fetchall()
        self.assertEqual([tuple(r) for r in rows], [("davra", "queued"), ("paparazzi", "queued")])

    def test_delete(self):
        self.h(post(12)); self.h(cb("ch:1:p")); self.h(cb("del:1"))
        self.assertEqual(store.get(self.db, 1)["status"], "rejected")


class FakeAcc:
    def __init__(self):
        self.sent = []

    async def publish(self, chat, body, hub_chat, hub_msg, has_media):
        self.sent.append((chat, body)); return 1


class FakeBotPub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, body, hub_chat, hub_msg, has_media):
        self.sent.append((chat, body)); return 2


class TestService(unittest.TestCase):
    def setUp(self):
        self.db, self.bot = store.connect(":memory:"), FakeBot()
        self.pubs = {"account": FakeAcc(), "bot": FakeBotPub()}

    def queue(self, hub_msg, channel, rubric, urgent=False):
        mid = store.add_material(self.db, -100777, hub_msg, "Матн @bugungi_gap", True)
        store.update(self.db, mid, channel=channel, rubric=rubric, status="queued", urgent=int(urgent),
                     created_at="2026-10-19T00:00:00+00:00")
        return mid

    def test_shadow_publishes_due_slot_to_test_chat_once(self):
        self.queue(1, "xojaobod", "Ҳажвия")
        now = plan.slot_time(dt.date(2026, 10, 19), "12:41")
        log = []
        r = asyncio.run(service.tick(self.db, CFG, ENV, self.pubs, now, log.append))
        self.assertEqual(r["published"], 1)
        chat, body = self.pubs["account"].sent[0]
        self.assertEqual(chat, -100111)                                   # теневой режим — тестовая группа
        self.assertNotIn("bugungi", body)
        self.assertIn("@XOJAOBODCITY24", body)
        asyncio.run(service.tick(self.db, CFG, ENV, self.pubs, now, log.append))
        self.assertEqual(len(self.pubs["account"].sent), 1)               # второй раз не публикует

    def test_urgent_now_and_paparazzi_via_bot(self):
        self.queue(2, "paparazzi", "Видео", urgent=True)
        asyncio.run(service.tick(self.db, CFG, ENV, self.pubs, plan.slot_time(dt.date(2026, 10, 19), "03:00"), lambda *_: None))
        self.assertEqual(self.pubs["bot"].sent[0][0], -100222)

    def test_live_targets_real_channels(self):
        self.assertEqual(service.target(dict(CFG, mode="live"), ENV, "paparazzi"), "@ozodjamoll")

    def test_per_channel_live(self):
        c = {**CFG, "channels": {**CFG["channels"], "paparazzi": {**CFG["channels"]["paparazzi"], "mode": "live"}}}
        self.assertEqual(service.target(c, ENV, "paparazzi"), "@ozodjamoll")
        self.assertEqual(service.target(c, ENV, "xojaobod"), -100111)   # Хўжаобод остаётся в тесте

    def test_today_text(self):
        self.queue(3, "paparazzi", "Қўшиқ")
        t = service.today_text(self.db, CFG, plan.slot_time(dt.date(2026, 10, 19), "09:00"))
        self.assertIn("🧪 тест", t)
        self.assertIn("PaparazziUZ", t)


if __name__ == "__main__":
    unittest.main()
