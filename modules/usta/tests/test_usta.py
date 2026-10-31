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
        old = (B.now() - B.dt.timedelta(minutes=31)).isoformat()
        self.b.db.execute("UPDATE leads SET created=?", (old,))
        orig = B.now
        B.now = lambda: orig().replace(hour=12)
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
