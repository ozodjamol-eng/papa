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
        self.assertIn("XO'JAOBOD CITY 24", r["text"])          # реклама только в Хўжаобод (20.10)
        self.assertNotIn("КАТТА ДАВРА", r["text"])
        self.assertNotIn("PaparazziUZ", r["text"])
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



class AiTest(unittest.TestCase):
    """30.10: настоящий ИИ-разговор (Gemini) — поздравления, реклама, знакомые, владелец, сбой ИИ."""
    def setUp(self):
        self.db, self.api = A.connect(":memory:"), Api()
        A.handle(self.db, {"business_connection": {"id": "BC", "user": {"id": OWNER}, "user_chat_id": OWNER, "is_enabled": True}},
                 self.api, T0)
        self.api.calls.clear()
        self.seen = []

    def ai(self, kind, reply):
        def f(system, hist, incoming, known):
            self.seen.append((hist, incoming, known))
            return {"kind": kind, "reply": reply}
        return f

    def sent(self, chat):
        return [p["text"] for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == chat]

    def test_juma_greeting_warm_reply_and_keeps_talking(self):
        r = A.handle(self.db, msg("Жума муборак!"), self.api, T0, ai=self.ai("greeting", "Жумангиз муборак бўлсин!"))
        self.assertEqual(r, "greeting")
        self.assertIn("ИИ-ёрдамчиси", self.sent(555)[0])          # первый ответ дня — с пометкой ИИ
        self.assertIn("Жумангиз муборак", self.sent(555)[0])
        A.handle(self.db, msg("Реклама қанча?"), self.api, T0 + dt.timedelta(minutes=2),
                 ai=self.ai("ad", "50 000 сўм, XO'JAOBOD CITY 24 да."))
        self.assertEqual(len(self.sent(555)), 2)                  # разговор продолжается, не глохнет
        self.assertNotIn("ИИ-ёрдамчиси:", self.sent(555)[1])
        self.assertEqual(self.seen[1][0][-1][0], "ai")            # ИИ видит свою прошлую реплику
        self.assertIn("📣 РЕКЛАМА", self.sent(OWNER)[-1])

    def test_known_contact_only_greetings(self):
        A.handle(self.db, msg("салом", uid=OWNER), self.api, T0)
        later = T0 + dt.timedelta(hours=30)
        self.assertEqual(A.handle(self.db, msg("Пул керак эди"), self.api, later, ai=self.ai("personal", "Етказаман")), "contact_quiet")
        self.assertEqual(self.sent(555), [])
        self.assertEqual(A.handle(self.db, msg("Жума муборак"), self.api, later, ai=self.ai("greeting", "Сизга ҳам!")), "greeting")
        self.assertTrue(self.seen[-1][2])                          # ИИ знает, что это знакомый

    def test_owner_wrote_ai_silent(self):
        A.handle(self.db, msg("ассалом", uid=OWNER), self.api, T0)
        self.assertEqual(A.handle(self.db, msg("реклама?"), self.api, T0 + dt.timedelta(minutes=5), ai=self.ai("ad", "x")), "quiet")
        self.assertEqual(self.sent(555), [])

    def test_ai_failure_falls_back_to_template(self):
        def bad(*a):
            raise RuntimeError("gemini 500")
        self.assertEqual(A.handle(self.db, msg("салом"), self.api, T0, ai=bad), "personal")
        self.assertIn("тез орада ўзи сиз билан боғланади", self.sent(555)[0])

    def test_daily_limit(self):
        f = self.ai("other", "ок")
        for i in range(A.AI_PER_CHAT_DAY):
            A.handle(self.db, msg(f"м{i}"), self.api, T0 + dt.timedelta(minutes=i), ai=f)
        self.assertEqual(A.handle(self.db, msg("ещё"), self.api, T0 + dt.timedelta(minutes=50), ai=f), "limit")


class ImageTest(unittest.TestCase):
    """30.10: ИИ смотрит картинки — фото, стикер, превью видео."""
    def test_image_ref(self):
        self.assertEqual(A.image_ref({"photo": [{"file_id": "s"}, {"file_id": "big"}]}), ("big", "image/jpeg"))
        self.assertEqual(A.image_ref({"sticker": {"file_id": "st", "emoji": "🙏"}}), ("st", "image/webp"))
        self.assertEqual(A.image_ref({"sticker": {"file_id": "a", "is_animated": True, "thumbnail": {"file_id": "th"}}}),
                         ("th", "image/webp"))
        self.assertEqual(A.image_ref({"video": {"file_id": "v", "thumbnail": {"file_id": "vt"}}}), ("vt", "image/jpeg"))
        self.assertIsNone(A.image_ref({"text": "салом"}))

    def test_ai_gets_image(self):
        db, api = A.connect(":memory:"), Api()
        api.download = lambda fid: b"IMG" if fid == "st" else b""
        A.handle(db, {"business_connection": {"id": "BC", "user": {"id": OWNER}, "user_chat_id": OWNER, "is_enabled": True}}, api, T0)
        got = []

        def ai(system, hist, incoming, known, image=None):
            got.append(image)
            return {"kind": "greeting", "reply": "Жумангиз муборак!"}
        m = msg(""); m["business_message"].pop("text"); m["business_message"]["sticker"] = {"file_id": "st", "emoji": "🕌"}
        self.assertEqual(A.handle(db, m, api, T0, ai=ai), "greeting")
        self.assertEqual(got[0], (b"IMG", "image/webp"))


class AutoGreetingTest(unittest.TestCase):
    """30.10: авто-приветствие Telegram от имени владельца не глушит ассистента."""
    def test_auto_greeting_does_not_silence(self):
        db, api = A.connect(":memory:"), Api()
        A.handle(db, {"business_connection": {"id": "BC", "user": {"id": OWNER}, "user_chat_id": OWNER, "is_enabled": True}}, api, T0)
        ai = lambda *a, **k: {"kind": "greeting", "reply": "Жумангиз муборак!"}
        A.handle(db, msg("Juma muborak"), api, T0, ai=ai)
        self.assertEqual(A.handle(db, msg("Ассалому алейкум 🙏", uid=OWNER), api, T0), "owner_auto")
        self.assertEqual(A.handle(db, msg("🕌"), api, T0 + dt.timedelta(minutes=1), ai=ai), "greeting")   # не «quiet»
        for chat in (1, 2, 3):                                    # одинаковый текст владельца в 3 чатах — тоже авто
            A.handle(db, msg("Салом! Ҳозир бандман", uid=OWNER, chat=chat), api, T0)
        self.assertTrue(A.is_auto_owner(db, "Салом! Ҳозир бандман", T0))
        self.assertFalse(A.is_auto_owner(db, "Ваалайкум, яхшимисиз?", T0))


class OrderTest(unittest.TestCase):
    """30.10 реклама под ключ, этап 1: готовый заказ — владельцу пакетом."""
    def test_order_sent_once(self):
        db, api = A.connect(":memory:"), Api()
        A.handle(db, {"business_connection": {"id": "BC", "user": {"id": OWNER}, "user_chat_id": OWNER, "is_enabled": True}}, api, T0)
        m = msg(""); m["business_message"].pop("text"); m["business_message"]["photo"] = [{"file_id": "P1"}]
        m["business_message"]["caption"] = "Дўконимиз очилди!"
        order = {"ready": True, "what": "дўкон", "days": 3, "evening": True, "pin": False, "date": "1 ноябр", "total": 160000,
                 "ad_text": "Дўконимиз очилди!"}
        ai = lambda *a, **k: {"kind": "ad", "reply": "Заказ Озод Жамолга етказилди", "order": order}
        A.handle(db, m, api, T0, ai=ai)
        to_owner = [(meth, p) for meth, p in api.calls if p.get("chat_id") == OWNER]
        self.assertTrue(any("ЗАКАЗ РЕКЛАМЫ" in p.get("text", "") and "160 000" in p.get("text", "") for _, p in to_owner))
        self.assertTrue(any(meth == "sendPhoto" and p["photo"] == "P1" for meth, p in to_owner))
        n = len(api.calls)
        A.handle(db, msg("раҳмат"), api, T0 + dt.timedelta(minutes=5), ai=ai)
        self.assertFalse(any(m2 == "sendPhoto" for m2, _ in api.calls[n:]))      # повторно не шлём
