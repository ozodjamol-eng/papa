import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xotira import bot as B, core  # noqa: E402

TODAY = lambda: dt.date(2026, 10, 18)  # noqa: E731


class Parse(unittest.TestCase):
    def test_two_people_like_channel(self):
        p = core.parse("Қосимов Қўчқарвой 1942-2005\nҚосимова Мўътабархон 1942–2026", TODAY())
        self.assertEqual(core.caption(p, "@XOTIRAXOJAOBOD"),
                         "Қосимов Қўчқарвой 1942-2005-63 ёш\n\nҚосимова Мўътабархон 1942-2026-84 ёш\n\n@XOTIRAXOJAOBOD")

    def test_latin_lower_and_dates(self):
        p = core.parse("qosimov qo'chqarvoy 12.03.1942 - 05.06.2005", TODAY())
        self.assertEqual(p[0]["name"], "Қосимов Қўчқарвой")
        self.assertEqual(p[0]["age"], 63)

    def test_bad(self):
        for t in ("Ахмедов 2005-1942", "1942-2005", "Ахмедов Али 1942", "Ахмедов 1800-2005", "А 1942-2005\nБ 1940-2000\nВ 1930-2001"):
            with self.assertRaises(core.BadInput, msg=t):
                core.parse(t, TODAY())

    def test_future_year(self):
        with self.assertRaises(core.BadInput):
            core.parse("Ахмедов Али 1950-2030", TODAY())


class Api:
    def __init__(self):
        self.calls = []

    def __call__(self, m, **p):
        self.calls.append((m, p))
        return {"message_id": 500 + len(self.calls)}


def msg(uid=7, text=None, photo=None, caption=None):
    m = {"message_id": 1, "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "first_name": "Али"}}
    if text is not None:
        m["text"] = text
    if photo:
        m["photo"] = [{"file_id": "small"}, {"file_id": photo}]
        if caption:
            m["caption"] = caption
    return {"message": m}


def cb(data, uid=7):
    return {"callback_query": {"id": "q", "data": data, "from": {"id": uid, "first_name": "Али"},
                               "message": {"chat": {"id": uid}, "message_id": 9}}}


class Flow(unittest.TestCase):
    def setUp(self):
        self.api = Api()
        self.bot = B.Bot(self.api, B.connect(":memory:"), {42}, "@XOTIRAXOJAOBOD", today=TODAY)

    def sent(self, method):
        return [p for m, p in self.api.calls if m == method]

    def test_full_flow_publish(self):
        h = self.bot.handle
        self.assertEqual(h(msg(text="/start")), "start")
        self.assertEqual(h(msg(photo="PH")), "photo")
        self.assertEqual(h(msg(text="Қосимов Қўчқарвой 1942-2005")), "preview")
        self.assertEqual(h(cb("u:send")), "sent")
        card = [p for p in self.sent("sendPhoto") if p["chat_id"] == 42][0]
        self.assertIn("№1", card["caption"])
        self.assertEqual(h(cb("o:ok:1", uid=7)), "denied")          # не владелец
        self.assertEqual(h(cb("o:ok:1", uid=42)), "published")
        ch = [p for p in self.sent("sendPhoto") if p["chat_id"] == "@XOTIRAXOJAOBOD"]
        self.assertEqual(ch[0]["caption"], "Қосимов Қўчқарвой 1942-2005-63 ёш\n\n@XOTIRAXOJAOBOD")
        self.assertEqual(ch[0]["photo"], "PH")
        self.assertTrue(any("t.me/XOTIRAXOJAOBOD/" in p["text"] for p in self.sent("sendMessage") if p["chat_id"] == 7))
        self.assertEqual(h(cb("o:ok:1", uid=42)), "dup")             # второй раз не публикует
        self.assertEqual(len([p for p in self.sent("sendPhoto") if p["chat_id"] == "@XOTIRAXOJAOBOD"]), 1)

    def test_text_first_and_caption(self):
        h = self.bot.handle
        h(msg(text="/start"))
        self.assertEqual(h(msg(text="Ахмедов Махаммадхўжа 1952-2024")), "text")
        self.assertEqual(h(msg(photo="P2")), "preview")
        h(msg(text="/start"))
        self.assertEqual(h(msg(photo="P3", caption="Ахмедов Махаммадхўжа 1952-2024")), "preview")

    def test_reject_and_cancel(self):
        h = self.bot.handle
        h(msg(photo="P"))
        h(msg(text="Ахмедов Али 1950-2020"))
        h(cb("u:send"))
        self.assertEqual(h(cb("o:no:1", uid=42)), "rejected")
        self.assertFalse([p for p in self.sent("sendPhoto") if p["chat_id"] == "@XOTIRAXOJAOBOD"])
        h(msg(photo="P"))
        self.assertEqual(h(cb("u:cancel")), "cancel")
        self.assertEqual(h(cb("u:send")), "stale")

    def test_bad_text_and_document(self):
        h = self.bot.handle
        self.assertEqual(h(msg(text="Ахмедов 2020-1950")), "bad")
        d = msg()
        d["message"]["document"] = {"file_id": "x"}
        self.assertEqual(h(d), "need_photo")

    def test_old_buttons_restart(self):
        self.assertEqual(self.bot.handle(cb("memory:start")), "start")


if __name__ == "__main__":
    unittest.main()


class Duplicates(unittest.TestCase):
    def setUp(self):
        self.api = Api()
        self.db = B.connect(":memory:")
        self.bot = B.Bot(self.api, self.db, {42}, "@XOTIRAXOJAOBOD", today=TODAY)
        B.index_post(self.db, 77, "Қосимов Қўчқарвой 1942-2005-63 ёш\n\nҚосимова Мўътабархон 1942-2026-84 ёш\n\n@XOTIRAXOJAOBOD")

    def go(self, text, uid=7):
        h = self.bot.handle
        h(msg(uid=uid, photo="P"))
        h(msg(uid=uid, text=text))
        return h(cb("u:send", uid=uid))

    def owner_caps(self):
        return [p["caption"] for m, p in self.api.calls if m == "sendPhoto" and p["chat_id"] == 42]

    def test_exact_repeat_answers_person_and_reports_owner(self):
        self.assertEqual(self.go("Kosimov Qo'chqarvoy 1942-2005"), "duplicate")
        user = [p["text"] for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == 7][-1]
        self.assertIn("t.me/XOTIRAXOJAOBOD/77", user)
        cap = self.owner_caps()[-1]
        self.assertIn("ПОВТОР", cap)
        kb = [p for m, p in self.api.calls if m == "sendPhoto" and p["chat_id"] == 42][-1]["reply_markup"]
        self.assertIn("Всё равно", kb["inline_keyboard"][0][0]["text"])
        self.assertEqual(self.bot.handle(cb("o:ok:1", uid=42)), "published")      # владелец решил — можно

    def test_clean_report(self):
        self.assertEqual(self.go("Ахмедов Али 1950-2020"), "sent")
        cap = self.owner_caps()[-1]
        self.assertIn("Проверено постов канала: 1", cap)
        self.assertIn("✅ Повторов нет", cap)
        self.assertIn("Ждёт вашего одобрения", cap)

    def test_namesake_other_years_only_flagged(self):
        self.assertEqual(self.go("Қосимов Қўчқарвой 1950-2019"), "sent")
        self.assertIn("🔎 Похоже", self.owner_caps()[-1])

    def test_pending_repeat_and_channel_index(self):
        self.go("Ахмедов Али 1950-2020")
        self.assertEqual(self.go("Ахмедов Али 1950-2020", uid=8), "sent")       # нет ссылки на канал — не «уже есть»
        self.assertIn("уже ждёт одобрения", self.owner_caps()[-1])
        r = self.bot.handle({"channel_post": {"message_id": 90, "chat": {"username": "XOTIRAXOJAOBOD"},
                                              "caption": "🕊 ХОТИРА\n\nМарҳум: Каримов Бобур\nТуғилган сана: 1960\nВафот этган сана: 2021\n"}})
        self.assertEqual(r, "indexed:1")
        self.assertEqual(self.go("Каримов Бобур 1960-2021", uid=9), "duplicate")
