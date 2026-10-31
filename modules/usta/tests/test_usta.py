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
        self.assertEqual(h(msg("80 м²")), "details")
        self.assertEqual(h(msg("Навоий маҳалла")), "place")
        self.assertEqual(h(msg(photo=[{"file_id": "x"}])), "photo")
        self.assertEqual(h(msg(contact={"phone_number": "998901234567"})), "lead")
        r = self.b.db.execute("SELECT * FROM leads").fetchone()
        self.assertEqual((r["kind"], r["src"], r["phone"], r["place"]), ("dizayn", "xojaobod", "+998901234567", "Навоий маҳалла"))
        card = [p for p in self.api.to(OWNER) if "text" in p][0]["text"]
        self.assertIn("Ариза №1", card); self.assertIn("xojaobod", card)
        self.assertTrue(any(m == "copyMessage" and p["chat_id"] == OWNER for m, p in self.api.calls))   # фото владельцу
        self.assertIn("№1", self.api.to(42)[-1]["text"])

    def test_skip_photo_and_typed_phone(self):
        h = self.b.handle
        h(msg("/start")); h(msg(T.KINDS["elektr"][0])); h(msg("розетка")); h(msg("Марказ"))
        self.assertEqual(h(msg(T.SKIP)), "skip")
        self.assertEqual(h(msg("салом")), "badphone")
        self.assertEqual(h(msg("90 123 45 67")), "lead")

    def test_owner_buttons_and_stats(self):
        h = self.b.handle
        h(msg("/start ig")); h(msg(T.KINDS["mebel"][0])); h(msg("шкаф")); h(msg("Ҳ")); h(msg(T.SKIP)); h(msg("+998911112233"))
        q = {"callback_query": {"id": "q", "from": {"id": OWNER}, "data": "ok:1", "message": {"chat": {"id": OWNER}, "message_id": 5}}}
        self.assertEqual(h(q), "ok")
        self.assertEqual(self.b.db.execute("SELECT status FROM leads").fetchone()[0], "done")
        q["callback_query"]["from"]["id"] = 999                     # чужой не нажмёт
        self.assertIsNone(h(q))
        self.assertEqual(h(msg("/stats", uid=OWNER)), "stats")
        self.assertIn("Аризалар: 1", self.api.to(OWNER)[-1]["text"])
        self.assertEqual(h(msg("/stats")), "unknown")               # клиенту статистика не видна

    def test_groups_ignored(self):
        u = msg("салом"); u["message"]["chat"]["type"] = "supergroup"
        self.assertIsNone(self.b.handle(u))


if __name__ == "__main__":
    unittest.main()
