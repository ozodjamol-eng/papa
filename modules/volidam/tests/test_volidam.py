import datetime as dt
import json
import unittest
from pathlib import Path

from volidam import bot as B

TZ = B.TZ
DATA = json.loads((Path(__file__).resolve().parent.parent / "data.json").read_text(encoding="utf-8"))


class FakeApi:
    def __init__(self):
        self.calls = []
        self.mid = 0

    def __call__(self, method, **p):
        self.calls.append((method, p))
        self.mid += 1
        return {"message_id": self.mid, "username": "VolidamTestBot"}

    def texts(self, chat=None):
        return [p.get("text") or p.get("caption") or "" for m, p in self.calls
                if m in ("sendMessage", "sendPhoto") and (chat is None or p.get("chat_id") == chat)]


def make(clock=None):
    api = FakeApi()
    db = B.connect(":memory:")
    cfg = B.load_cfg()
    c = clock or (lambda: dt.datetime(2026, 11, 2, 12, 0, tzinfo=TZ))
    return B.Bot(api, db, {1}, cfg, data=DATA, clock=c, mgr_code="SEKRET"), api


def msg(uid, text=None, contact=None):
    m = {"chat": {"id": uid, "type": "private"}, "from": {"id": uid, "first_name": "Али"}}
    if text is not None:
        m["text"] = text
    if contact:
        m["contact"] = {"phone_number": contact}
    return {"message": m}


def cb(uid, data):
    return {"callback_query": {"id": "x", "from": {"id": uid, "first_name": "Али"}, "data": data}}


class T(unittest.TestCase):
    def test_parse_start(self):
        self.assertEqual(B.parse_start("site_anjum_1911_3"), {"src": "Сайт", "pkg": "anjum", "date": "19.11", "room": "3"})
        self.assertEqual(B.parse_start("mgr_ABC"), {"mgr": "ABC"})
        self.assertEqual(B.parse_start("instagram")["src"], "Instagram")
        self.assertEqual(B.parse_start("")["src"], "Telegram")

    def test_phone(self):
        self.assertEqual(B.norm_phone("90 766 82 84"), "+998907668284")
        self.assertIsNone(B.norm_phone("салом"))

    def test_past_dates_hidden(self):
        b, _ = make()
        ds = b.dates(b.pkg("comfort"))
        self.assertTrue(all(d >= dt.date(2026, 11, 2) for d in ds))
        self.assertEqual(ds[0], dt.date(2026, 11, 4))
        self.assertEqual(b.dates(b.pkg("standart")), [])

    def test_full_order_flow_and_manager_card(self):
        b, api = make()
        b.handle(msg(5, "/start"))
        b.handle(cb(5, "o:anjum"))
        b.handle(cb(5, "d:19.11"))
        b.handle(cb(5, "r:3"))
        b.handle(cb(5, "n:2"))
        b.handle(msg(5, contact="+998901234567"))
        lead = b.db.execute("SELECT * FROM leads").fetchone()
        self.assertEqual(lead["phone"], "+998901234567")
        self.assertIn("Tawaf Anjum", lead["details"])
        self.assertIn("$1900", lead["details"])
        self.assertTrue(any("АРИЗА №1" in t for t in api.texts(1)))
        b.handle(cb(1, "l:taken:1"))
        self.assertEqual(b.db.execute("SELECT status FROM leads").fetchone()[0], "taken")

    def test_site_deeplink_prefills(self):
        b, api = make()
        b.handle(msg(7, "/start site_comfort_1811_2"))
        d = b.user(7)["data"]
        self.assertEqual((d["pkg"], d["date"], d["room"]), ("comfort", "18.11", "2"))
        self.assertTrue(any("Неча киши" in t for t in api.texts(7)))

    def test_manager_registration(self):
        b, _ = make()
        b.handle(msg(9, "/start mgr_SEKRET"))
        self.assertIn(9, b.managers)
        b.handle(msg(10, "/start mgr_WRONG"))
        self.assertNotIn(10, b.managers)

    def test_remind(self):
        t = [dt.datetime(2026, 11, 2, 12, 0, tzinfo=TZ)]
        b, api = make(lambda: t[0])
        b.handle(msg(5, "/start"))
        b.handle(cb(5, "o:-"))
        b.handle(msg(5, "Нодир"))
        b.handle(msg(5, "90 111 22 33"))
        t[0] += dt.timedelta(minutes=16)
        self.assertEqual(b.remind(), 1)
        self.assertEqual(b.remind(), 0)


class T2(unittest.TestCase):
    def test_faq(self):
        b, api = make()
        b.handle(msg(5, "❓ Савол-жавоб"))
        b.handle(cb(5, "q:0"))
        self.assertTrue(any("Авиабилет ва виза" in t for t in api.texts(5)))
        b.handle(cb(5, "o:start"))
        self.assertTrue(any("1/4" in t for t in api.texts(5)))

    def test_channel_offer_after_lead(self):
        b, api = make()
        b.cfg["channel"] = "https://t.me/volidam_test"
        b.handle(msg(5, "/start"))
        b.handle(cb(5, "o:-"))
        b.handle(msg(5, "Али"))
        b.handle(msg(5, "+998901234567"))
        self.assertTrue(any("каналимизга" in t for t in api.texts(5)))


class T3(unittest.TestCase):
    def test_owner_post_flow(self):
        b, api = make()
        b.cfg["channel_id"] = "@test_ch"
        b.handle(msg(1, "📣 Каналга пост"))
        m = msg(1, "Янги сана: 19-ноябрь")
        m["message"]["message_id"] = 77
        b.handle(m)
        self.assertTrue(any(c[0] == "copyMessage" and c[1]["chat_id"] == 1 for c in api.calls))
        b.handle(cb(1, "pub:77"))
        self.assertTrue(any(c[0] == "copyMessage" and c[1]["chat_id"] == "@test_ch" for c in api.calls))
        n = len(api.calls)
        b.handle(cb(1, "pub:77"))
        self.assertFalse(any(c[0] == "copyMessage" and c[1]["chat_id"] == "@test_ch" for c in api.calls[n:]))

    def test_stranger_cannot_post(self):
        b, api = make()
        b.cfg["channel_id"] = "@test_ch"
        b.handle(msg(5, "📣 Каналга пост"))
        b.handle(cb(5, "pub:1"))
        self.assertFalse(any(c[0] == "copyMessage" for c in api.calls))


if __name__ == "__main__":
    unittest.main()
