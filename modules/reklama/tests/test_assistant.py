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

    def test_personal_gets_greeting_menu(self):
        self.assertEqual(A.handle(self.db, msg("Ozod aka, qalaysiz?"), self.api, T0), "personal")
        r = self.sent(555)[0]
        self.assertIn("ва раҳматуллоҳи ва барокатуҳ", r["text"])
        self.assertIn("ИИ-ёрдамчисиман", r["text"])
        self.assertEqual(len(r["reply_markup"]["inline_keyboard"]), 3)     # 3 кнопки меню
        self.assertNotIn("50 000", r["text"])

    def test_always_answers(self):
        A.handle(self.db, msg("салом"), self.api, T0)
        self.assertEqual(A.handle(self.db, msg("салом"), self.api, T0 + dt.timedelta(hours=2)), "personal")
        self.assertEqual(len(self.sent(555)), 2)                    # 30.10: отвечает всегда
        self.assertIn("етказдим", self.sent(555)[1]["text"])        # второй раз — коротко, без меню
        self.assertNotIn("reply_markup", self.sent(555)[1])

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
        r = A.handle(self.db, msg("Жума муборак!"), self.api, T0, ai=self.ai("congrats", "Жумангиз муборак бўлсин!"))
        self.assertEqual(r, "congrats")
        self.assertIn("Жумангиз муборак", self.sent(555)[0])          # сначала ответное поздравление
        self.assertIn("ИИ-ёрдамчисиман", self.sent(555)[1])           # потом приветствие + меню
        A.handle(self.db, msg("Реклама қанча?"), self.api, T0 + dt.timedelta(minutes=2),
                 ai=self.ai("ad", "50 000 сўм, XO'JAOBOD CITY 24 да."))
        self.assertEqual(len(self.sent(555)), 3)                  # разговор продолжается, не глохнет
        self.assertNotIn("барокатуҳ", self.sent(555)[2])          # второй раз не здоровается
        self.assertEqual(self.seen[1][0][-1][0], "ai")            # ИИ видит свою прошлую реплику
        self.assertIn("📣 РЕКЛАМА", self.sent(OWNER)[-1])

    def test_known_contact_also_answered(self):
        A.handle(self.db, msg("салом", uid=OWNER), self.api, T0)
        self.assertEqual(A.handle(self.db, msg("Хорменг ака"), self.api, T0 + dt.timedelta(minutes=40),
                                  ai=self.ai("greeting", "Ваалайкум")), "greeting")
        self.assertIn("ИИ-ёрдамчисиман", self.sent(555)[0])         # 30.10: знакомым тоже приветствие + меню
        self.assertTrue(self.seen[-1][2])                          # ИИ знает, что это знакомый
        for i in range(5):                                         # хоть 5 раз — всегда ответ
            A.handle(self.db, msg(f"ака {i}"), self.api, T0 + dt.timedelta(minutes=41 + i), ai=self.ai("personal", f"Етказаман {i}"))
        self.assertEqual(len(self.sent(555)), 6)
        self.assertTrue(self.seen[-1][2])                          # ИИ знает, что это знакомый

    def test_owner_wrote_ai_silent(self):
        A.handle(self.db, msg("ассалом", uid=OWNER), self.api, T0)
        self.assertEqual(A.handle(self.db, msg("реклама?"), self.api, T0 + dt.timedelta(minutes=5), ai=self.ai("ad", "x")), "quiet")
        self.assertEqual(self.sent(555), [])

    def test_ai_failure_falls_back_to_template(self):
        def bad(*a):
            raise RuntimeError("gemini 500")
        self.assertEqual(A.handle(self.db, msg("салом"), self.api, T0, ai=bad), "personal")
        self.assertIn("ИИ-ёрдамчисиман", self.sent(555)[0])         # шаблон тоже с приветствием и меню

    def test_daily_limit(self):
        f = self.ai("other", "ок")
        for i in range(A.AI_PER_CHAT_DAY):
            A.handle(self.db, msg(f"м{i}"), self.api, T0 + dt.timedelta(minutes=i), ai=f)
        A.handle(self.db, msg("ещё"), self.api, T0 + dt.timedelta(minutes=50), ai=f)
        self.assertIn("етказдим", self.sent(555)[-1])              # предел ИИ — всё равно короткий ответ


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


class MenuTest(unittest.TestCase):
    """30.10: приветствие + меню из 3 кнопок, выбор кнопкой или цифрой."""
    def setUp(self):
        self.db, self.api = A.connect(":memory:"), Api()
        A.handle(self.db, {"business_connection": {"id": "BC", "user": {"id": OWNER}, "user_chat_id": OWNER, "is_enabled": True}},
                 self.api, T0)
        self.api.calls.clear()

    def sent(self, chat):
        return [p for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == chat]

    def test_salom_gets_menu_only(self):
        ai = lambda *a, **k: {"kind": "greeting", "reply": "Ваалайкум ассалом! Қандай ёрдам керак?"}
        self.assertEqual(A.handle(self.db, msg("Салом"), self.api, T0, ai=ai), "greeting")
        out = self.sent(555)
        self.assertEqual(len(out), 1)                              # без дубля «чем помочь»
        self.assertIn("reply_markup", out[0])

    def test_clear_request_greeting_plus_answer(self):
        ai = lambda *a, **k: {"kind": "ad", "reply": "1 кун — 50 000 сўм. Нимани реклама қиласиз?"}
        A.handle(self.db, msg("reklama narxi?"), self.api, T0, ai=ai)
        t = self.sent(555)[0]["text"]
        self.assertTrue(t.startswith("Ассалому алайкум ва раҳматуллоҳи"))
        self.assertIn("50 000", t)

    def test_button_press(self):
        A.handle(self.db, msg("салом"), self.api, T0)
        q = {"callback_query": {"id": "q1", "data": "m:ad", "from": {"id": 555, "first_name": "Ali"},
                                "message": {"business_connection_id": "BC", "chat": {"id": 555, "type": "private"}}}}
        self.assertEqual(A.handle(self.db, q, self.api, T0 + dt.timedelta(minutes=1)), "pick_ad")
        self.assertIn("Хўжаобод Сити 24", self.sent(555)[-1]["text"])
        self.assertIn("Реклама бўйича · Ali", self.sent(OWNER)[-1]["text"])
        self.assertTrue(any(m == "answerCallbackQuery" for m, _ in self.api.calls))
        self.assertEqual(A.handle(self.db, q, self.api, T0 + dt.timedelta(minutes=1)), "pick_dup")   # двойное нажатие

    def test_buttons_fail_numbers_work(self):
        calls = []

        def api(method, **p):
            if p.get("reply_markup"):
                raise RuntimeError("sendMessage: Bad Request: BUTTON_TYPE_INVALID")
            calls.append(p)
            return {}
        A.handle(self.db, msg("салом"), api, T0)
        self.assertIn("1️⃣ Реклама бўйича", calls[0]["text"])
        self.assertEqual(A.handle(self.db, msg("3"), api, T0 + dt.timedelta(minutes=1)), "pick_me")
        self.assertIn("албатта етказаман", [p for p in calls if p["chat_id"] == 555][-1]["text"])

    def test_album_answered_once(self):
        for i in range(3):
            m = msg(""); m["business_message"].pop("text"); m["business_message"]["photo"] = [{"file_id": f"p{i}"}]
            m["business_message"]["media_group_id"] = "G1"
            A.handle(self.db, m, self.api, T0)
        self.assertEqual(len(self.sent(555)), 1)

    def test_owner_quiet_only_30_min(self):
        A.handle(self.db, msg("ассалом", uid=OWNER), self.api, T0)
        self.assertEqual(A.handle(self.db, msg("ака"), self.api, T0 + dt.timedelta(minutes=10)), "quiet")
        self.assertEqual(A.handle(self.db, msg("ака"), self.api, T0 + dt.timedelta(minutes=31)), "personal")

    def test_number_without_menu_is_ordinary(self):
        self.assertEqual(A.handle(self.db, msg("2"), self.api, T0), "personal")


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
