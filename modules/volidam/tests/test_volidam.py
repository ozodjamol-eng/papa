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


def gmsg(uid, chat_id=-100, username="umraxojaobod", **kw):
    m = {"message_id": kw.pop("mid", 50), "chat": {"id": chat_id, "type": "supergroup", "username": username,
                                                   "title": "Умра Хўжаобод"},
         "from": {"id": uid, "first_name": "Ҳасан", "is_bot": False}}
    m.update(kw)
    return {"message": m}


class Branch(unittest.TestCase):
    def order(self, b, uid, start):
        b.handle(msg(uid, f"/start {start}"))
        b.handle(cb(uid, "o:anjum"))
        b.handle(cb(uid, "d:19.11"))
        b.handle(cb(uid, "r:3"))
        b.handle(cb(uid, "n:2"))
        b.handle(msg(uid, contact="+998901234567"))

    def test_branch_link_and_aliases(self):
        b, _ = make()
        self.assertEqual(b.branch_of_payload("br_xojaobod"), "xojaobod")
        self.assertEqual(b.branch_of_payload("filial"), "xojaobod")
        self.assertEqual(b.branch_of_payload("insta_filial"), "xojaobod")
        self.assertIsNone(b.branch_of_payload("instagram"))

    def test_branch_manager_sees_only_own_leads(self):
        b, api = make()
        b.handle(msg(7, "/start mgr_SEKRET_xojaobod"))      # Шаҳзодбек
        b.handle(msg(8, "/start mgr_SEKRET"))               # главный менеджер
        self.assertEqual(b.mgr_branch(7), "xojaobod")
        self.assertIsNone(b.mgr_branch(8))
        self.order(b, 5, "br_xojaobod")                     # заявка филиала
        self.order(b, 6, "instagram")                       # обычная заявка
        l1, l2 = b.db.execute("SELECT branch, src FROM leads ORDER BY n").fetchall()
        self.assertEqual(l1[0], "xojaobod")
        self.assertIsNone(l2[0])
        t7 = [t for t in api.texts(7) if "АРИЗА" in t]
        self.assertEqual(len(t7), 1)
        self.assertIn("Хўжаобод филиали", t7[0])
        self.assertEqual(len([t for t in api.texts(8) if "АРИЗА" in t]), 2)
        self.assertEqual(len([t for t in api.texts(1) if "АРИЗА" in t]), 2)
        b.handle(cb(7, "l:taken:2"))                        # чужую заявку взять нельзя
        self.assertEqual(b.db.execute("SELECT status FROM leads WHERE n=2").fetchone()[0], "new")
        b.handle(cb(7, "l:taken:1"))
        self.assertEqual(b.db.execute("SELECT status FROM leads WHERE n=1").fetchone()[0], "taken")

    def test_branch_client_contact_first_phone_and_write_button(self):
        b, api = make()
        b.handle(msg(5, "/start filial"))
        b.handle(msg(5, "/aloqa"))
        p = [p for m, p in api.calls if m == "sendMessage" and "Алоқа" in p.get("text", "")][-1]
        self.assertLess(p["text"].index("97 543"), p["text"].index("90 766"))
        btns = [r[0]["text"] for r in p["reply_markup"]["inline_keyboard"]]
        self.assertEqual(btns[0], "✍️ Шаҳзодбекка ёзиш")
        urls = [r[0].get("url", "") for r in p["reply_markup"]["inline_keyboard"]]
        self.assertIn("https://t.me/UmraXojaobod", urls)

    def test_bad_branch_manager_code(self):
        b, _ = make()
        b.handle(msg(7, "/start mgr_WRONG_xojaobod"))
        self.assertIsNone(b.db.execute("SELECT 1 FROM managers WHERE uid=7").fetchone())

    def test_group_welcome_and_cleanup(self):
        b, api = make()
        b.handle(gmsg(9, new_chat_members=[{"id": 9, "first_name": "Ҳасан", "is_bot": False}], mid=60))
        dels = [p["message_id"] for m, p in api.calls if m == "deleteMessage"]
        self.assertIn(60, dels)                              # служебное «вошёл» удалено
        w = [p for m, p in api.calls if m == "sendMessage" and p["chat_id"] == -100][-1]
        self.assertIn("Хўжаобод филиали", w["text"])
        self.assertIn("start=br_xojaobod", w["reply_markup"]["inline_keyboard"][0][0]["url"])
        first = b.db.execute("SELECT v FROM kv WHERE k='welcome:-100'").fetchone()[0]
        b.handle(gmsg(10, new_chat_members=[{"id": 10, "first_name": "Али", "is_bot": False}], mid=61))
        self.assertIn(int(first), [p["message_id"] for m, p in api.calls if m == "deleteMessage"])  # старое убрано

    def test_group_link_spam_deleted_admin_kept(self):
        b, api = make()
        api_calls = api.calls
        orig = api.__call__

        def fake(method, **p):
            if method == "getChatAdministrators":
                api_calls.append((method, p))
                return [{"user": {"id": 77}}]
            return orig(method, **p)
        b.api = fake
        b.handle(gmsg(9, text="Арзон кредит https://spam.uz", mid=70))
        b.handle(gmsg(9, text="Ассалому алайкум, нархлар қанча?", mid=71))
        b.handle(gmsg(77, text="Сайтимиз: https://safomarvaumra.uz", mid=72))
        b.handle(gmsg(9, text="кан", forward_origin={"type": "channel"}, mid=73))
        dels = [p["message_id"] for m, p in api_calls if m == "deleteMessage"]
        self.assertEqual(sorted(dels), [70, 73])

    def test_foreign_group_ignored(self):
        b, api = make()
        b.handle(gmsg(9, chat_id=-555, username="other", text="https://x.uz", mid=80))
        self.assertFalse([1 for m, p in api.calls if m in ("deleteMessage", "sendMessage")])

    def test_bind_and_post_to_group(self):
        b, api = make()
        b.handle(gmsg(1, chat_id=-777, username=None, text="/bind xojaobod", mid=90))
        self.assertEqual(b.group_chat("xojaobod"), -777)
        self.assertEqual([k for k, _, _ in b.post_targets()], ["ch", "xojaobod"])
        b.handle(msg(1, "📣 Пост юбориш"))
        b.handle({"message": {"message_id": 5, "chat": {"id": 1, "type": "private"}, "from": {"id": 1}, "text": "Янги сана!"}})
        b.handle(cb(1, "pub:5:xojaobod"))
        cp = [p for m, p in api.calls if m == "copyMessage" and p["chat_id"] == -777]
        self.assertEqual(len(cp), 1)
        b.handle(cb(1, "pub:5:xojaobod"))                  # второй раз не дублирует
        self.assertEqual(len([p for m, p in api.calls if m == "copyMessage" and p["chat_id"] == -777]), 1)
        b.handle(cb(9, "pub:5:xojaobod"))                  # не владелец — ничего
        self.assertEqual(len([p for m, p in api.calls if m == "copyMessage" and p["chat_id"] == -777]), 1)

    def test_old_db_migrates(self):
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.executescript("CREATE TABLE managers (uid INTEGER PRIMARY KEY, name TEXT, added TEXT);"
                         "CREATE TABLE leads (n INTEGER PRIMARY KEY, uid INTEGER NOT NULL, phone TEXT, details TEXT, "
                         "src TEXT, status TEXT NOT NULL DEFAULT 'new', created TEXT NOT NULL, reminded INTEGER NOT NULL "
                         "DEFAULT 0, cards TEXT, log TEXT);"
                         "INSERT INTO managers VALUES (8,'Нодирбек','x');")
        import volidam.bot as BB
        db.row_factory = sqlite3.Row
        db.executescript(BB.SCHEMA)
        for t, c in BB.MIGRATE.items():
            if c not in {r[1] for r in db.execute(f"PRAGMA table_info({t})")}:
                db.execute(f"ALTER TABLE {t} ADD COLUMN {c} TEXT")
        b = BB.Bot(FakeApi(), db, {1}, BB.load_cfg(), data=DATA)
        self.assertIn(8, b.recipients("xojaobod"))          # старый менеджер = главный, видит всё


class MgrLink(unittest.TestCase):
    def test_owner_gets_links_others_not(self):
        b, api = make()
        b.handle(msg(1, "/mgrlink"))
        t = api.texts(1)[-1]
        self.assertIn("start=mgr_SEKRET_xojaobod", t)
        b.handle(msg(5, "/mgrlink"))
        self.assertFalse(any("SEKRET" in x for x in api.texts(5)))
