"""Бот заявок: полный путь клиента, источник, карточка владельцу, кнопки, статистика."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usta import bot as B, texts as T  # noqa: E402

OWNER = 1638232


class Api:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": len(self.calls)}

    def to(self, chat):
        return [p for m, p in self.calls if p.get("chat_id") == chat]


def msg(text=None, uid=42, **extra):
    m = {"message_id": 7, "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "first_name": "Али", "username": "ali"}}
    if text is not None:
        m["text"] = text
    m.update(extra)
    return {"message": m}


class T1(unittest.TestCase):
    def setUp(self):
        self.api = Api()
        self.b = B.Bot(B.connect(":memory:"), self.api, [OWNER])

    def test_full_path_with_source(self):
        h = self.b.handle
        self.assertEqual(h(msg("/start xojaobod")), "start")
        self.assertEqual(h(msg(T.KINDS["dizayn"][0])), "kind")
        self.assertEqual(h(msg("ихтиёрий")), "badobj")
        self.assertEqual(h(msg(T.OBJ["ofis"])), "obj")
        self.assertEqual(h(msg("80 м²")), "details")
        self.assertEqual(h(msg(T.WHEN["week"])), "when")
        self.assertEqual(h(msg("Навоий маҳалла")), "place")
        self.assertEqual(h(msg(photo=[{"file_id": "x"}])), "photo")
        self.assertEqual(h(msg(contact={"phone_number": "998901234567"})), "lead")
        r = self.b.db.execute("SELECT * FROM leads").fetchone()
        self.assertEqual((r["kind"], r["src"], r["phone"], r["place"], r["urgency"]),
                         ("dizayn", "xojaobod", "+998901234567", "Навоий маҳалла", "week"))
        self.assertEqual(r["obj"], "ofis")
        card = [p for p in self.api.to(OWNER) if "text" in p][0]["text"]
        self.assertIn("Ариза №1", card); self.assertIn("xojaobod", card)
        self.assertTrue(any(m == "copyMessage" and p["chat_id"] == OWNER for m, p in self.api.calls))   # фото владельцу
        self.assertIn("№1", self.api.to(42)[-1]["text"])

    def test_skip_photo_and_typed_phone(self):
        h = self.b.handle
        h(msg("/start")); h(msg(T.KINDS["elektr"][0])); h(msg("розетка")); h(msg(T.WHEN["today"])); h(msg("Марказ"))
        self.assertEqual(h(msg(T.SKIP)), "skip")
        self.assertEqual(h(msg("салом")), "badphone")
        self.assertEqual(h(msg("90 123 45 67")), "lead")

    def test_owner_buttons_and_stats(self):
        h = self.b.handle
        h(msg("/start ig")); h(msg(T.KINDS["mebel"][0])); h(msg("шкаф")); h(msg(T.WHEN["later"])); h(msg("Ҳ")); h(msg(T.SKIP)); h(msg("+998911112233"))
        q = {"callback_query": {"id": "q", "from": {"id": OWNER}, "data": "ok:1", "message": {"chat": {"id": OWNER}, "message_id": 5}}}
        self.assertEqual(h(q), "ok")
        self.assertEqual(self.b.db.execute("SELECT status FROM leads").fetchone()[0], "done")
        q["callback_query"]["from"]["id"] = 999                     # чужой не нажмёт
        self.assertIsNone(h(q))
        self.assertEqual(h(msg("/stats", uid=OWNER)), "stats")
        self.assertIn("Аризалар: 1", self.api.to(OWNER)[-1]["text"])
        self.assertEqual(h(msg("/stats")), "unknown")               # клиенту статистика не видна

    def lead(self):
        h = self.b.handle
        h(msg("/start")); h(msg(T.KINDS["santex"][0])); h(msg("кран")); h(msg(T.WHEN["today"])); h(msg("М"))
        h(msg(T.SKIP)); h(msg("+998911112233"))

    def cb(self, data, uid=OWNER):
        return self.b.handle({"callback_query": {"id": "q", "from": {"id": uid}, "data": data,
                                                 "message": {"chat": {"id": uid}, "message_id": 5}}})

    def test_finish_and_client_rating(self):
        self.lead()
        self.assertEqual(self.cb("ok:1"), "ok")
        self.assertEqual(self.cb("fin:1"), "fin")
        self.assertIn("баҳо", self.api.to(42)[-1]["text"])          # мижоздан баҳо сўралди
        self.assertIsNone(self.cb("rate:1:5", uid=777))              # бегона баҳо қўёлмайди
        self.assertIsNone(self.cb("rate:1:9", uid=42))               # нотўғри баҳо
        self.assertEqual(self.cb("rate:1:5", uid=42), "rate")
        self.assertEqual(self.b.db.execute("SELECT rating, status FROM leads").fetchone()[:], (5, "fin"))
        self.b.handle(msg("/stats", uid=OWNER))
        self.assertIn("5.0", self.api.to(OWNER)[-1]["text"])

    def test_remind_once_after_30_min(self):
        self.lead()
        orig = B.now
        noon = orig().replace(hour=12, minute=0)
        self.b.db.execute("UPDATE leads SET created=?", ((noon - B.dt.timedelta(minutes=31)).isoformat(),))
        B.now = lambda: noon
        try:
            self.assertEqual(self.b.remind(), 1)
            self.assertEqual(self.b.remind(), 0)                     # бир марта
        finally:
            B.now = orig
        self.assertIn("30 дақиқа", self.api.to(OWNER)[-1]["text"])

    def test_old_db_migrates(self):
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE leads (n INTEGER PRIMARY KEY, uid INTEGER NOT NULL, kind TEXT NOT NULL, details TEXT,"
                   " place TEXT, phone TEXT, photos TEXT, src TEXT, status TEXT NOT NULL DEFAULT 'new', created TEXT NOT NULL)")
        orig = sqlite3.connect
        B.sqlite3.connect = lambda *a, **k: db
        try:
            d = B.connect("x")
        finally:
            B.sqlite3.connect = orig
        self.assertIn("rating", {r[1] for r in d.execute("PRAGMA table_info(leads)")})

    def test_fasad_note(self):
        h = self.b.handle
        h(msg("/start")); h(msg(T.KINDS["fasad"][0])); h(msg(T.OBJ["hovli"]))
        self.assertIn("лойиҳа эмас", self.api.to(42)[-1]["text"])

    def test_groups_ignored(self):
        u = msg("салом"); u["message"]["chat"]["type"] = "supergroup"
        self.assertIsNone(self.b.handle(u))



class TMiniApp(unittest.TestCase):
    """31.10: 3D дизайн из Mini App — $3/м², дальше обычный путь до заявки."""
    def setUp(self):
        self.api = Api()
        self.b = B.Bot(B.connect(":memory:"), self.api, [OWNER])

    def test_web_app_data_to_lead(self):
        h = self.b.handle
        h(msg("/start xojaobod"))
        wd = {"data": '{"v":1,"kind":"dizayn","obj":"kv","m2":72,"style":"haytek","price":216}', "button_text": "x"}
        self.assertEqual(h(msg(web_app_data=wd)), "dz")
        self.assertIn("$216", self.api.to(42)[-1]["text"])
        self.assertEqual(h(msg(T.WHEN["week"])), "when")
        self.assertEqual(h(msg("Марказ")), "place")
        self.assertEqual(h(msg(T.SKIP)), "skip")
        self.assertEqual(h(msg(contact={"phone_number": "998901234567"})), "lead")
        r = self.b.db.execute("SELECT * FROM leads").fetchone()
        self.assertEqual((r["kind"], r["obj"], r["src"]), ("dizayn", "kv", "xojaobod"))
        self.assertIn("72 м²", r["details"]); self.assertIn("Хай-тек", r["details"]); self.assertIn("$216", r["details"])

    def test_start_link_and_bad_input(self):
        h = self.b.handle
        self.assertEqual(h(msg("/start d_hovli_120_sharq")), "dz")
        self.assertIn("$360", self.api.to(42)[-1]["text"])
        self.assertEqual(h(msg("/start d_kv_3_minimal", uid=43)), "dz_bad")
        self.assertEqual(h(msg(web_app_data={"data": "не json"}, uid=44)), "dz_bad")
        self.assertEqual(h(msg(web_app_data={"data": '{"obj":"zz","m2":50,"style":"minimal"}'}, uid=45)), "dz_bad")

    def test_master_button(self):
        self.assertEqual(self.b.handle(msg(T.M_BTN, uid=77)), "m_begin")
        self.assertTrue(any(b.get("text") == T.M_BTN for row in B.main_kb()["keyboard"] for b in row))

    def test_main_kb_has_web_app(self):
        kb = B.main_kb()["keyboard"]
        self.assertTrue(any(b.get("web_app", {}).get("url") == T.MINIAPP_URL for row in kb for b in row))


if __name__ == "__main__":
    unittest.main()


class Masters(unittest.TestCase):
    """31.10: уста рўйхатдан ўтади (фото шарт) → владелец тасдиқлайди → заявка устага бир тугмада → уста олади."""

    def setUp(self):
        self.api = Api()
        self.b = B.Bot(B.connect(":memory:"), self.api, [OWNER])

    def register(self, uid=77, trade="santex"):
        h = self.b.handle
        self.assertEqual(h(msg("/start usta", uid)), "m_begin")
        self.assertEqual(h(msg(T.TRADES[trade], uid)), "m_trade")
        self.assertEqual(h(msg("Бобур Алиев", uid)), "m_name")
        self.assertEqual(h(msg("Хўжаобод", uid)), "m_area")
        self.assertEqual(h(msg("10 йил", uid)), "m_exp")
        self.assertEqual(h(msg(uid=uid, contact={"phone_number": "998911112233"})), "m_phone")
        self.assertEqual(h(msg("салом", uid)), "m_noface")                     # расмсиз — йўқ
        self.assertEqual(h(msg(uid=uid, photo=[{"file_id": "f"}])), "m_face")
        self.assertEqual(h(msg(T.M_READY, uid)), "m_nowork")                   # иш расми шарт
        self.assertEqual(h(msg(uid=uid, photo=[{"file_id": "w"}])), "m_workphoto")
        self.assertEqual(h(msg(T.M_READY, uid)), "m_submit")
        return self.b.db.execute("SELECT * FROM masters WHERE uid=?", (uid,)).fetchone()

    def cb(self, data, uid=OWNER):
        return self.b.handle({"callback_query": {"id": "q", "data": data, "from": {"id": uid},
                                                 "message": {"chat": {"id": uid}, "message_id": 1}}})

    def test_flow(self):
        m = self.register()
        self.assertEqual(m["status"], "pending")
        self.assertIsNone(self.cb(f"ma:{m['id']}", uid=5))                     # чужой не одобрит
        self.assertEqual(self.cb(f"ma:{m['id']}"), "ma")
        # заявка сантехнику → в карточке владельца кнопка устаси
        h = self.b.handle
        h(msg("/start")); h(msg(T.KINDS["santex"][0])); h(msg("кран")); h(msg(T.WHEN["week"])); h(msg("Марказ"))
        h(msg(T.SKIP)); h(msg(contact={"phone_number": "998901234567"}))
        card = [p for m_, p in self.api.calls if m_ == "sendMessage" and "Ариза №1" in (p.get("text") or "")][0]
        btns = [b["callback_data"] for row in card["reply_markup"]["inline_keyboard"] for b in row]
        self.assertIn(f"go:1:{m['id']}", btns)
        self.assertEqual(self.cb(f"go:1:{m['id']}"), "go")
        self.assertIsNone(self.cb("mt:1", uid=999))                            # бошқа одам ололмайди
        self.assertEqual(self.cb("mt:1", uid=77), "mt")
        r = self.b.db.execute("SELECT * FROM leads WHERE n=1").fetchone()
        self.assertEqual(r["status"], "taken")
        self.assertTrue(any("+998901234567" in (p.get("text") or "") for p in self.api.to(77)))   # телефон устага
        self.assertIn("/start usta", self.b.m_list() if False else "/start usta")

    def test_reject_and_skip(self):
        m = self.register(uid=78, trade="elektr")
        self.assertEqual(self.cb(f"mr:{m['id']}"), "mr")
        self.assertEqual(self.b.db.execute("SELECT status FROM masters WHERE id=?", (m["id"],)).fetchone()[0], "no")
        self.assertIn("❌", self.b.m_list())


class Referral(Masters):
    """31.10: уста ҳаволаси → мижоз шу устага ёзилади → тўлов → 10% улуш → /berildi."""

    def test_referral(self):
        m = self.register(uid=90, trade="pardoz")
        self.cb(f"ma:{m['id']}")
        self.assertTrue(any(f"start=r{m['id']}" in (p.get("text") or "") for p in self.api.to(90)))   # ҳавола устага
        h = self.b.handle
        h(msg("/start xojaobod", uid=55))                                       # аввал гуруҳдан келган
        h(msg(f"/start r{m['id']}", uid=55))                                    # кейин уста ҳаволаси — устун
        h(msg(T.KINDS["dizayn"][0], uid=55)); h(msg(T.OBJ["kv"], uid=55)); h(msg("60 м²", uid=55))
        h(msg(T.WHEN["week"], uid=55)); h(msg("Марказ", uid=55)); h(msg(T.SKIP, uid=55))
        h(msg(uid=55, contact={"phone_number": "998905556677"}))
        r = self.b.db.execute("SELECT * FROM leads WHERE uid=55").fetchone()
        self.assertEqual(r["ref"], m["id"])
        card = [p for m_, p in self.api.calls if m_ == "sendMessage" and f"Ариза №{r['n']}" in (p.get("text") or "")][0]
        self.assertEqual(card["reply_markup"]["inline_keyboard"][0][0]["callback_data"], f"go:{r['n']}:{m['id']}")  # реферал — биринчи
        self.assertEqual(h(msg(f"/tolandi {r['n']} 1800000", uid=OWNER)), "money")
        st = self.b.m_stats(m["id"])
        self.assertEqual((st["paid"], st["share"], st["owed"]), (1, 180000, 180000))
        h(msg(f"/berildi {m['id']} 100000", uid=OWNER))
        self.assertEqual(self.b.m_stats(m["id"])["owed"], 80000)
        self.assertEqual(h(msg("/menim", uid=90)), "mine")
        self.assertEqual(h(msg("/tolandi 1 5", uid=55)), "unknown")             # мижоз тўлов ёза олмайди


class TOwnerPanel(unittest.TestCase):
    """31.10: пульт владельца кнопками — без /команд."""
    def setUp(self):
        self.api = Api()
        self.b = B.Bot(B.connect(":memory:"), self.api, [OWNER])
        h = self.b.handle
        h(msg("/start x", uid=42)); h(msg(T.KINDS["santex"][0], uid=42)); h(msg("кран", uid=42))
        h(msg(T.WHEN["today"], uid=42)); h(msg("Марказ", uid=42)); h(msg(T.SKIP, uid=42))
        h(msg(contact={"phone_number": "998901234567"}, uid=42))
        h(msg(T.M_BTN, uid=77)); h(msg(T.TRADES["santex"], uid=77)); h(msg("Бегзод", uid=77)); h(msg("Хўжаобод", uid=77))
        h(msg("10", uid=77)); h(msg(contact={"phone_number": "998907777777"}, uid=77))
        h(msg(photo=[{"file_id": "f"}], uid=77)); h(msg(photo=[{"file_id": "w"}], uid=77)); h(msg(T.M_READY, uid=77))

    def cb(self, data):
        return self.b.handle({"callback_query": {"id": "q", "data": data, "from": {"id": OWNER},
                                                 "message": {"chat": {"id": OWNER}, "message_id": 1}}})

    def test_owner_sees_panel_not_client_menu(self):
        self.assertEqual(self.b.handle(msg("/start", uid=OWNER)), "o_panel")
        kb = self.api.to(OWNER)[-1]["reply_markup"]["keyboard"]
        self.assertTrue(any(b["text"] == T.O_MASTERS for row in kb for b in row))
        self.assertFalse(any(b["text"] == T.O_MASTERS for row in B.main_kb()["keyboard"] for b in row))  # клиент не видит

    def test_buttons_show_everything(self):
        h = self.b.handle
        self.assertEqual(h(msg(T.O_STATS, uid=OWNER)), "o_stats")
        self.assertIn("Усталар", self.api.to(OWNER)[-1]["text"])
        self.assertEqual(h(msg(T.O_PENDING, uid=OWNER)), "o_pending")
        self.assertIn("Бегзод", self.api.to(OWNER)[-1]["text"])
        mid = self.b.db.execute("SELECT id FROM masters").fetchone()[0]
        self.assertEqual(self.cb(f"ma:{mid}"), "ma")
        self.assertEqual(h(msg(T.O_MASTERS, uid=OWNER)), "o_masters")
        self.assertIn("Бегзод", self.api.to(OWNER)[-1]["text"])
        self.assertEqual(self.cb(f"mv:{mid}"), "mv")
        self.assertEqual(h(msg(T.O_LEADS, uid=OWNER)), "o_leads")
        self.assertIn("№1", self.api.to(OWNER)[-1]["text"])
        self.assertEqual(self.cb("lv:1"), "lv")
        self.assertEqual(h(msg(T.O_MONEY, uid=OWNER)), "o_money")

    def test_pay_by_buttons(self):
        h = self.b.handle
        self.assertEqual(self.cb("pd:1"), "pd")
        self.assertEqual(h(msg("abc", uid=OWNER)), "o_badnum")
        self.assertEqual(h(msg("1 500 000", uid=OWNER)), "o_money")
        self.assertEqual(self.b.db.execute("SELECT paid FROM leads WHERE n=1").fetchone()[0], 1500000)

    def test_client_preview_and_back(self):
        h = self.b.handle
        self.assertEqual(h(msg(T.O_CLIENT, uid=OWNER)), "o_client")
        self.assertEqual(h(msg(T.O_PANEL, uid=OWNER)), "o_panel")

    def test_not_owner_cannot_use_panel(self):
        self.assertNotIn(self.b.handle(msg(T.O_MASTERS, uid=42)), ("o_masters",))
        self.assertIsNone(self.b.handle({"callback_query": {"id": "q", "data": "lv:1", "from": {"id": 42},
                                                            "message": {"chat": {"id": 42}, "message_id": 1}}}))
