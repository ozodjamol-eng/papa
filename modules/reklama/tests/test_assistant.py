"""17.10: ИИ-ассистент личного Telegram — только первое сообщение, всегда «ИИ-ёрдамчи», реклама — прайс."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import assistant as A  # noqa: E402

T0 = dt.datetime(2026, 10, 17, 10, 0, tzinfo=dt.timezone.utc)
OWNER = 1638232


class Api:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {}


def msg(text, uid=555, chat=555, **extra):
    m = {"business_connection_id": "BC", "chat": {"id": chat, "type": "private"},
         "from": {"id": uid, "first_name": "Ali", "username": "ali"}, "text": text}
    m.update(extra)
    return {"business_message": m}


class Assistant(unittest.TestCase):
    def setUp(self):
        self.db, self.api = A.connect(":memory:"), Api()
        A.handle(self.db, {"business_connection": {"id": "BC", "user": {"id": OWNER}, "user_chat_id": OWNER, "is_enabled": True}},
                 self.api, T0)
        self.api.calls.clear()

    def sent(self, chat):
        return [p for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == chat]

    def test_ad_gets_price_and_owner_notified(self):
        self.assertEqual(A.handle(self.db, msg("Assalomu alaykum, reklama narxi qancha?"), self.api, T0), "ad")
        r = self.sent(555)[0]
        self.assertEqual(r["business_connection_id"], "BC")
        self.assertIn("ИИ-ёрдамчиси", r["text"])                      # всегда говорит, что это ИИ-ассистент
        self.assertIn("50 000 сўм", r["text"])
        self.assertIn("КАТТА ДАВРА", r["text"])
        self.assertIn("📣 РЕКЛАМА · Ali (@ali)", self.sent(OWNER)[0]["text"])

    def test_personal_short_reply(self):
        self.assertEqual(A.handle(self.db, msg("Ozod aka, qalaysiz?"), self.api, T0), "personal")
        t = self.sent(555)[0]["text"]
        self.assertIn("ИИ-ёрдамчиси", t)
        self.assertIn("тез орада ўзи сиз билан боғланади", t)
        self.assertNotIn("50 000", t)

    def test_only_first_message_per_day(self):
        A.handle(self.db, msg("салом"), self.api, T0)
        self.assertEqual(A.handle(self.db, msg("реклама керак"), self.api, T0 + dt.timedelta(hours=2)), "quiet")
        self.assertEqual(len(self.sent(555)), 1)
        self.assertEqual(A.handle(self.db, msg("салом"), self.api, T0 + dt.timedelta(hours=25)), "personal")

    def test_owner_wrote_bot_silent(self):
        self.assertEqual(A.handle(self.db, msg("Ваалайкум ассалом!", uid=OWNER), self.api, T0), "owner")
        self.assertEqual(A.handle(self.db, msg("реклама?"), self.api, T0 + dt.timedelta(minutes=5)), "quiet")
        self.assertEqual(self.sent(555), [])

    def test_ignores_bots_and_groups(self):
        m = msg("hi"); m["business_message"]["from"]["is_bot"] = True
        self.assertEqual(A.handle(self.db, m, self.api, T0), "skip")
        m = msg("hi"); m["business_message"]["chat"]["type"] = "group"
        self.assertEqual(A.handle(self.db, m, self.api, T0), "skip")

    def test_voice_without_text(self):
        m = msg(""); m["business_message"].pop("text"); m["business_message"]["voice"] = {"file_id": "x"}
        self.assertEqual(A.handle(self.db, m, self.api, T0), "personal")
        self.assertIn("без текста: voice", self.sent(OWNER)[0]["text"])

    def test_keywords(self):
        for t in ("Reklama bormi", "Эълон бермоқчи эдим", "Сколько стоит реклама?", "Narxi qancha turadi"):
            self.assertEqual(A.kind_of(t), "ad", t)
        for t in ("Салом, қалайсиз?", "Ozod aka, tug'ilgan kuningiz bilan!", "Привет"):
            self.assertEqual(A.kind_of(t), "personal", t)


if __name__ == "__main__":
    unittest.main()


class StartTextTest(unittest.TestCase):
    def test_owner_vs_stranger(self):
        import assistant as A
        db = A.connect(":memory:")
        db.execute("INSERT INTO conn VALUES ('c1', 7, 7, 1)")
        self.assertIn("уведомления", A.start_text(db, {"from": {"id": 7}}))
        self.assertIn("@Ozodjamol", A.start_text(db, {"from": {"id": 99}}))


class RightsTest(unittest.TestCase):
    def test_peer_invalid_alerts_owner_once(self):
        import datetime as dt
        import assistant as A
        db = A.connect(":memory:")
        sent = []

        def api(method, **p):
            if p.get("business_connection_id"):
                raise RuntimeError("sendMessage: Bad Request: BUSINESS_PEER_INVALID")
            sent.append(p)
            return {}
        A.handle(db, {"business_connection": {"id": "c1", "user": {"id": 1}, "user_chat_id": 1, "is_enabled": True,
                                              "rights": {"can_reply": False}}}, api)
        self.assertIn("НЕ даёт ему отвечать", sent[-1]["text"])
        sent.clear()
        msg = lambda uid: {"business_message": {"business_connection_id": "c1", "chat": {"id": uid, "type": "private"},
                                                "from": {"id": uid, "first_name": "A"}, "text": "салом"}}
        now = dt.datetime(2026, 10, 19, 4, 0, tzinfo=dt.timezone.utc)
        for uid in (5, 6):
            with self.assertRaises(RuntimeError):
                A.handle(db, msg(uid), api, now=now)
        self.assertEqual(len(sent), 1)                 # инструкция владельцу — один раз в сутки
        self.assertIn("Чат-боты", sent[0]["text"])

