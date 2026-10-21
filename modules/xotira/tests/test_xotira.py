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
                         "Қосимов Қўчқарвой\n1942-2005-63 ёш\n\nҚосимова Мўътабархон\n1942-2026-84 ёш\n\n@XOTIRAXOJAOBOD")

    def test_latin_lower_and_dates(self):
        p = core.parse("qosimov qo'chqarvoy 12.03.1942 - 05.06.2005", TODAY())
        self.assertEqual(p[0]["name"], "Қосимов Қўчқарвой")
        self.assertEqual(p[0]["age"], 63)

    def test_bad(self):
        for t in ("Ахмедов 2005-1942", "1942-2005", "Ахмедов Али 1942", "Ахмедов 1800-2005", "А 1942-2005\nБ 1940-2000\nВ 1930-2001"):
            with self.assertRaises(core.BadInput, msg=t):
                core.parse(t, TODAY())

    def test_no_name_blocked(self):
        # 19.10: пост №52 ушёл в канал как «Йош 1979-2020-41 ёш» — без имени. Такое не пропускаем.
        for t in ("Йош 1979-2020", "ёш 1979-2020", "Марҳум 1950-2010", "1979-2020 41 ёш", "Ота 1940-2000",
                  "Қосимов 1942-2005", "Хожи ота 1930-2001"):
            with self.assertRaises(core.BadInput, msg=t) as cm:
                core.parse(t, TODAY())
            self.assertIn("исм-фамилия", str(cm.exception))
        p = core.parse("Марҳум Қосимов Қўчқарвой ёш 1942-2005", TODAY())
        self.assertEqual(p[0]["name"], "Қосимов Қўчқарвой")
        self.assertEqual(core.parse("Қосимов Қўчқарвой ота 1942-2005", TODAY())[0]["name"], "Қосимов Қўчқарвой")

    def test_titles_removed_two_on_one_line(self):
        # 19.10: заявка №61 — «хожи дада/эна», возраст и два человека в одной строке → только ФИО, годы под именем
        p = core.parse("Муминов Абдунаби хожи дада 1906-2000-94 Муминова Хайринисо хожи эна 1924-2010-86 ёш", TODAY())
        self.assertEqual([(x["name"], x["born"], x["died"], x["age"]) for x in p],
                         [("Муминов Абдунаби", 1906, 2000, 94), ("Муминова Хайринисо", 1924, 2010, 86)])
        self.assertEqual(core.caption(p, "@X"), "Муминов Абдунаби\n1906-2000-94 ёш\n\nМуминова Хайринисо\n1924-2010-86 ёш\n\n@X")

    def test_name_line_then_years_line(self):
        p = core.parse("Қосимов Қўчқарвой ота\n1942-2005", TODAY())
        self.assertEqual(p[0]["name"], "Қосимов Қўчқарвой")
        p = core.parse("Hoji dada Qosimov Qo'chqarvoy 1942-2005", TODAY())
        self.assertEqual(p[0]["name"], "Қосимов Қўчқарвой")

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
        self.assertEqual(ch[0]["caption"], "Қосимов Қўчқарвой\n1942-2005-63 ёш\n\n@XOTIRAXOJAOBOD")
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
        B.index_post(self.db, 77, "Қосимов Қўчқарвой\n1942-2005-63 ёш\n\nҚосимова Мўътабархон\n1942-2026-84 ёш\n\n@XOTIRAXOJAOBOD")

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
        self.assertEqual(kb["inline_keyboard"], [[{"text": "❌ Рад этиш", "callback_data": "o:no:1"}]])
        self.assertEqual(self.bot.handle(cb("o:ok:1", uid=42)), "blocked")        # старая кнопка — не публикует
        n_user = len([1 for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == 7])
        self.assertEqual(self.bot.handle(cb("o:no:1", uid=42)), "rejected")       # заявка закрыта
        self.assertEqual(len([1 for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == 7]), n_user)
        self.assertFalse(any(m == "sendPhoto" and p["chat_id"] == "@XOTIRAXOJAOBOD" for m, p in self.api.calls))

    def test_clean_report(self):
        self.assertEqual(self.go("Ахмедов Али 1950-2020"), "sent")
        cap = self.owner_caps()[-1]
        self.assertIn("Проверено постов канала: 1", cap)
        self.assertIn("✅ Повторов нет", cap)
        self.assertIn("Ждёт вашего одобрения", cap)

    def test_namesake_other_years_only_flagged(self):
        self.assertEqual(self.go("Қосимов Қўчқарвой 1950-2019"), "sent")
        self.assertIn("🔎 Похоже", self.owner_caps()[-1])

    def test_similar_has_polite_exists_button(self):
        self.assertEqual(self.go("Қосимов Қўчқарвой 1950-2019"), "sent")
        kb = [p for m, p in self.api.calls if m == "sendPhoto" and p["chat_id"] == 42][-1]["reply_markup"]
        self.assertIn({"text": "🙏 Уже есть в канале — вежливо отказать", "callback_data": "o:has:1"},
                      [b for row in kb["inline_keyboard"] for b in row])
        self.assertEqual(self.bot.handle(cb("o:has:1", uid=7)), "denied")
        self.assertEqual(self.bot.handle(cb("o:has:1", uid=42)), "exists")
        user = [p["text"] for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == 7][-1]
        self.assertIn("аллақачон жойлаштирилган", user)
        self.assertIn("t.me/XOTIRAXOJAOBOD/77", user)
        self.assertEqual(self.bot.handle(cb("o:has:1", uid=42)), "dup")
        self.assertFalse(any(m == "sendPhoto" and p["chat_id"] == "@XOTIRAXOJAOBOD" for m, p in self.api.calls))

    def test_clean_report_has_no_exists_button(self):
        self.go("Ахмедов Али 1950-2020")
        kb = [p for m, p in self.api.calls if m == "sendPhoto" and p["chat_id"] == 42][-1]["reply_markup"]
        self.assertNotIn("o:has:1", str(kb))

    def test_pending_repeat_and_channel_index(self):
        self.go("Ахмедов Али 1950-2020")
        self.assertEqual(self.go("Ахмедов Али 1950-2020", uid=8), "sent")       # нет ссылки на канал — не «уже есть»
        self.assertIn("уже ждёт одобрения", self.owner_caps()[-1])
        r = self.bot.handle({"channel_post": {"message_id": 90, "chat": {"username": "XOTIRAXOJAOBOD"},
                                              "caption": "🕊 ХОТИРА\n\nМарҳум: Каримов Бобур\nТуғилган сана: 1960\nВафот этган сана: 2021\n"}})
        self.assertEqual(r, "indexed:1")
        self.assertEqual(self.go("Каримов Бобур 1960-2021", uid=9), "duplicate")


class OwnerCardNoName(unittest.TestCase):
    def test_card_warns_without_name(self):
        b = B.Bot(api=lambda *a, **k: {}, db=B.connect(":memory:"), owners={1}, channel="@XOTIRAXOJAOBOD", today=TODAY)
        row = {"id": 52, "who": "x", "caption": "Йош 1979-2020-41 ёш\n\n@XOTIRAXOJAOBOD", "status": "pending", "report": ""}

        class R(dict):
            def keys(self):
                return super().keys()
        self.assertIn("НЕТ ИМЕНИ", b.owner_card(R(row)))
        row["caption"] = "Қосимов Қўчқарвой 1942-2005-63 ёш\n\n@XOTIRAXOJAOBOD"
        self.assertNotIn("НЕТ ИМЕНИ", b.owner_card(R(row)))


# ---------- 19.10: скриншоты и обрезка фото ----------
from xotira import photo as PH  # noqa: E402

try:
    import cv2
    import numpy as np
except Exception:  # noqa: BLE001
    cv2 = None


def screenshot(bg=0, w=540, h=1170):
    """Как присылают люди: экран телефона, в середине фото, сверху строка состояния, внизу кнопки."""
    rnd = np.random.default_rng(1)
    img = np.full((h, w, 3), bg, np.uint8)
    img[300:900, 40:500] = rnd.integers(30, 230, (600, 460, 3), dtype=np.uint8)      # само фото
    fg = 255 - bg
    cv2.putText(img, "21:02", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (fg,) * 3, 2)   # строка состояния
    for x, t in ((30, "CANCEL"), (220, "RESET"), (420, "CROP")):                       # кнопки редактора
        cv2.putText(img, t, (x, 1000), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (fg,) * 3, 2)
    return img


@unittest.skipIf(cv2 is None, "нет OpenCV")
class Photo(unittest.TestCase):
    def test_dark_and_light_screenshot_cropped_to_photo(self):
        for bg in (0, 255):
            img = screenshot(bg)
            x, y, w, h = PH.region(img)
            self.assertLess(abs(x - 40) + abs(y - 300), 20, bg)
            self.assertLess(abs(w - 460) + abs(h - 600), 30, bg)
            out = PH.decode(PH.auto(PH.encode(img)))
            self.assertLess(abs(out.shape[0] - 600), 20)

    def test_normal_photo_untouched(self):
        img = np.random.default_rng(2).integers(0, 255, (800, 600, 3), dtype=np.uint8)
        self.assertIsNone(PH.auto(PH.encode(img)))
        self.assertIsNone(PH.face(PH.encode(img)))                   # лица нет — честно «нет»


class FileApi(Api):
    """Фейковый Telegram с файлами: download отдаёт скриншот, upload возвращает новый file_id."""
    def __init__(self, data):
        super().__init__()
        self.data, self.ups = data, []

    def download(self, fid):
        return self.data if fid in ("SHOT", "PH") or fid.startswith("CUT") else b"bad"

    def upload(self, m, field, data, **p):
        self.ups.append((m, p))
        self.calls.append((m, p))
        return {"message_id": 700 + len(self.ups), "photo": [{"file_id": f"CUT{len(self.ups)}"}]}


@unittest.skipIf(cv2 is None, "нет OpenCV")
class PhotoFlow(unittest.TestCase):
    def setUp(self):
        self.api = FileApi(PH.encode(screenshot()))
        q, PH.quality = PH.quality, lambda data: None              # здесь проверяем обрезку, не качество
        self.addCleanup(setattr, PH, "quality", q)
        self.bot = B.Bot(self.api, B.connect(":memory:"), {42}, "@XOTIRAXOJAOBOD", today=TODAY)

    def channel(self):
        return [p for m, p in self.api.calls if m == "sendPhoto" and p["chat_id"] == "@XOTIRAXOJAOBOD"]

    def submit(self):
        h = self.bot.handle
        h(msg(photo="SHOT"))
        self.assertTrue(any("скриншот" in p["text"] for m, p in self.api.calls if m == "sendMessage"))
        h(msg(text="Аскарова Гулмирахон 1975-2026"))
        self.assertEqual(h(cb("u:send")), "sent")

    def test_screenshot_auto_cropped_and_published(self):
        self.submit()
        card = self.api.ups[0][1]
        self.assertIn("обрезано автоматически", card["caption"])
        texts = [b["text"] for row in card["reply_markup"]["inline_keyboard"] for b in row]
        self.assertIn("👤 По лицу", texts)
        self.assertEqual(self.bot.handle(cb("o:ok:1", uid=42)), "published")
        self.assertEqual(self.channel()[0]["photo"], "CUT1")            # в канал ушло обрезанное

    def test_original_and_own_photo(self):
        self.submit()
        self.assertEqual(self.bot.handle(cb("o:orig:1", uid=42)), "orig")
        self.assertEqual(self.bot.handle(cb("o:orig:1", uid=42)), "same")
        self.assertEqual(self.bot.handle(cb("o:crop:1", uid=42)), "crop")
        self.assertEqual(self.bot.handle(cb("o:face:1", uid=7)), "denied")
        self.assertEqual(self.bot.handle(cb("o:own:1", uid=42)), "wait")
        self.assertEqual(self.bot.handle(msg(uid=42, photo="MINE")), "replaced")
        self.bot.handle(cb("o:ok:1", uid=42))
        self.assertEqual(self.channel()[0]["photo"], "MINE")
        self.assertEqual(self.bot.handle(cb("o:crop:1", uid=42)), "dup")  # после публикации не трогаем

    def test_reply_photo_to_card(self):
        self.submit()
        mid = json.loads(self.bot.db.execute("SELECT owner_msgs FROM subs").fetchone()[0])["42"]
        m = msg(uid=42, photo="R")
        m["message"]["reply_to_message"] = {"message_id": mid}
        self.assertEqual(self.bot.handle(m), "replaced")

    def test_broken_file_does_not_break_flow(self):
        h = self.bot.handle
        h(msg(photo="X"))                                               # download → b"bad"
        h(msg(text="Ахмедов Али 1950-2020"))
        self.assertEqual(h(cb("u:send")), "sent")
        self.assertEqual(h(cb("o:face:1", uid=42)), "none")


@unittest.skipIf(cv2 is None, "нет OpenCV")
class Enhance(PhotoFlow):
    def test_enhance_once_then_orig(self):
        self.submit()
        self.assertEqual(self.bot.handle(cb("o:enh:1", uid=42)), "enh")
        self.assertEqual(self.bot.handle(cb("o:enh:1", uid=42)), "same")      # дважды не улучшаем
        self.assertEqual(self.bot.handle(cb("o:orig:1", uid=42)), "orig")
        self.bot.handle(cb("o:ok:1", uid=42))
        self.assertEqual(self.channel()[0]["photo"], "SHOT")

    def test_enhance_keeps_size(self):
        img = screenshot()
        out = PH.decode(PH.enhance(PH.encode(img)))
        self.assertEqual(out.shape, img.shape)


@unittest.skipIf(cv2 is None, "нет OpenCV")
class Quality(unittest.TestCase):
    def test_detail_sharp_vs_blur(self):
        img = np.random.default_rng(3).integers(0, 255, (200, 200, 3), dtype=np.uint8)
        self.assertGreater(PH.detail(img), PH.SHARP)
        self.assertLess(PH.detail(cv2.GaussianBlur(img, (0, 0), 3)), PH.SHARP)

    def test_no_face(self):
        self.assertEqual(PH.quality(PH.encode(screenshot())), "noface")


@unittest.skipIf(cv2 is None, "нет OpenCV")
class QualityFlow(unittest.TestCase):
    def setUp(self):
        self.api = FileApi(b"x")
        self.why = "blur"
        q, PH.quality = PH.quality, lambda data: self.why
        self.addCleanup(setattr, PH, "quality", q)
        self.bot = B.Bot(self.api, B.connect(":memory:"), {42}, "@XOTIRAXOJAOBOD", today=TODAY)

    def last(self, chat):
        return [p for m, p in self.api.calls if p.get("chat_id") == chat][-1]

    def test_doubtful_photo_owner_decides(self):
        # 20.10: бот сам человеку не отказывает — понятная карточка владельцу, 3 кнопки
        h = self.bot.handle
        self.assertEqual(h(msg(photo="PH", caption="Ахмедов Али 1950-2020")), "bad_photo")
        self.assertIn("кутинг", self.last(7)["text"])                   # человеку — «ждите», не отказ
        self.assertIsNone(self.bot.user(7)["photo"])
        card = self.last(42)
        self.assertIn("Прислал: Али", card["caption"])
        self.assertIn("За кого: Ахмедов Али 1950-2020", card["caption"])
        self.assertIn("фото размытое", card["caption"])
        self.assertNotIn("id", card["caption"])
        btn = [b["callback_data"] for r in card["reply_markup"]["inline_keyboard"] for b in r]
        self.assertEqual(btn, ["o:pok:7", "o:pnew:7", "o:pno:7"])
        self.assertEqual(h(cb("o:pok:7", uid=7)), "denied")
        self.assertEqual(h(cb("o:pok:7", uid=42)), "preview")             # принять → сразу предпросмотр
        self.assertEqual(self.bot.user(7)["photo"], "PH")
        ed = [p for m, p in self.api.calls if m == "editMessageCaption"][-1]
        self.assertIn("ПРИНЯТО", ed["caption"])
        self.assertEqual(ed["reply_markup"], {"inline_keyboard": []})
        self.assertEqual(h(cb("o:pno:7", uid=42)), "stale")

    def test_ask_new_and_refuse(self):
        h = self.bot.handle
        h(msg(photo="PH"))
        self.assertIn("пока не написал", self.last(42)["caption"])
        self.assertEqual(h(cb("o:pnew:7", uid=42)), "ask_new")
        self.assertIn("хира", self.last(7)["text"])
        h(msg(photo="PH"))
        self.assertEqual(h(cb("o:pno:7", uid=42)), "refused")
        self.assertIn("катта раҳмат", self.last(7)["text"])
        self.assertIn("Вежливо отказано", [p for m, p in self.api.calls if m == "editMessageCaption"][-1]["caption"])

    def test_good_photo_after_doubt(self):
        h = self.bot.handle
        h(msg(photo="PH"))
        self.why = None
        self.assertEqual(h(msg(photo="PH")), "photo")
        self.assertIn("сам прислал", [p for m, p in self.api.calls if m == "editMessageCaption"][-1]["caption"])
        self.assertEqual(h(cb("o:pok:7", uid=42)), "stale")

    def test_owner_button_bad_photo(self):
        h = self.bot.handle
        self.why = None
        h(msg(photo="PH"))
        h(msg(text="Ахмедов Али 1950-2020"))
        self.assertEqual(h(cb("u:send")), "sent")
        kb = [p for m, p in self.api.calls if m == "sendPhoto" and p["chat_id"] == 42][-1]["reply_markup"]
        self.assertEqual(kb["inline_keyboard"][1][0]["callback_data"], "o:bad:1")
        self.assertEqual(h(cb("o:bad:1", uid=42)), "bad_photo")
        txt = [p["text"] for m, p in self.api.calls if m == "sendMessage" and p["chat_id"] == 7][-1]
        self.assertIn("катта раҳмат", txt)
        self.assertIn("Фақат янги расмни", txt)
        self.assertEqual(h(cb("o:ok:1", uid=42)), "dup")
        self.assertEqual(h(msg(photo="PH")), "preview")                 # ФИО и годы сохранены — сразу предпросмотр


# ---------- 21.10: обход проверки — другое написание, другие годы, то же фото ----------
class NameTricks(unittest.TestCase):
    def cmp(self, a, b):
        return core.compare(a, b)

    def test_tricks(self):
        P = lambda n, b, d: {"name": n, "born": b, "died": d}  # noqa: E731
        self.assertEqual(self.cmp(P("Рахмов Эргашбой", 1939, 2007), P("Раҳмонов Эргашбой ота", 1933, 2004)), "similar")
        self.assertEqual(self.cmp(P("Эргашбой Раҳмонов", 1933, 2006), P("Раҳмонов Эргашбой", 1933, 2006)), "same")
        self.assertEqual(self.cmp(P("Эргашбой Раҳмонов", 1930, 2001), P("Раҳмонов Эргашбой", 1933, 2006)), "similar")
        self.assertEqual(self.cmp(P("Rahmonov Ergashboy", 1950, 2010), P("Раҳмонов Эргашбой", 1933, 2006)), "similar")
        self.assertEqual(self.cmp(P("Тошматов Эргашбой", 1933, 2006), P("Раҳмонов Эргашбой", 1933, 2006)), "similar")
        self.assertIsNone(self.cmp(P("Тошматов Эргашбой", 1940, 2010), P("Раҳмонов Эргашбой", 1933, 2006)))
        self.assertIsNone(self.cmp(P("Абдураимов Абдулла", 1950, 2010), P("Абдуллаев Абдулла", 1950, 2011)))
        self.assertIsNone(self.cmp(P("Каримов Бобур", 1960, 2021), P("Ахмедов Али", 1950, 2020)))


def picture(seed=3, w=500, h=600):
    """Фото «как настоящее»: фигуры с углами и переходами — есть за что зацепиться."""
    rnd = np.random.default_rng(seed)
    img = np.full((h, w, 3), 120, np.uint8)
    for _ in range(40):
        c = tuple(int(v) for v in rnd.integers(0, 255, 3))
        if rnd.random() < 0.5:
            x, y = (int(v) for v in rnd.integers(0, (w, h)))
            cv2.rectangle(img, (x, y), (x + int(rnd.integers(20, 120)), y + int(rnd.integers(20, 120))), c, -1)
        else:
            cv2.circle(img, tuple(int(v) for v in rnd.integers(0, (w, h))), int(rnd.integers(10, 60)), c, -1)
    return cv2.GaussianBlur(img, (3, 3), 0)


@unittest.skipIf(cv2 is None, "нет OpenCV")
class PhotoRepeat(unittest.TestCase):
    def setUp(self):
        q, PH.quality = PH.quality, lambda data: None
        self.addCleanup(setattr, PH, "quality", q)
        orig = picture()
        shot = np.full((1170, 540, 3), 15, np.uint8)
        shot[300:900, 20:520] = cv2.resize(orig, (500, 600))
        cv2.putText(shot, "21:02", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240,) * 3, 2)
        self.files = {"OLD": PH.encode(orig), "SHOT": PH.encode(shot), "OTHER": PH.encode(picture(9))}
        api = FileApi(b"")
        api.download = lambda fid: self.files.get(fid, b"bad")
        self.api = api
        self.db = B.connect(":memory:")
        self.bot = B.Bot(api, self.db, {42}, "@XOTIRAXOJAOBOD", today=TODAY)
        self.assertEqual(self.bot.handle({"channel_post": {"message_id": 30, "chat": {"username": "XOTIRAXOJAOBOD"},
                                                           "photo": [{"file_id": "OLD"}],
                                                           "caption": "Раҳмонов Эргашбой\n1933-2006-73 ёш"}}), "indexed:1")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM prints").fetchone()[0], 1)

    def go(self, photo, text):
        h = self.bot.handle
        h(msg(photo=photo))
        h(msg(text=text))
        h(cb("u:send"))
        return [p for m, p in self.api.calls if m == "sendPhoto" and p.get("chat_id") == 42][-1]  # карточка владельцу

    def test_same_photo_other_name_caught(self):
        card = self.go("SHOT", "Тошматов Алишер 1950-2015")              # имя и годы — совсем другие
        self.assertIn("ЭТО ФОТО уже было", card["caption"])
        self.assertIn("t.me/XOTIRAXOJAOBOD/30", card["caption"])
        self.assertIn("o:has:1", str(card["reply_markup"]))
        self.assertNotIn("Повторов нет", card["caption"])

    def test_other_photo_clean(self):
        card = self.go("OTHER", "Тошматов Алишер 1950-2015")
        self.assertNotIn("ЭТО ФОТО", card["caption"])
        self.assertIn("Повторов нет", card["caption"])
