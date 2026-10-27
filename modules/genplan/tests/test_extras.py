"""20.10: перенос из GENPLAN 5 — ☀️ погода и курс 07:00, 🌙 Якуний пост 22:00 каждый день, 📣 реклама на N дней."""
import asyncio
import datetime as dt
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import extras, hub, plan, service, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
for _c in CFG["channels"].values():   # 25.10: здесь — прежняя сетка рубрик (PaparazziUZ); часовая — test_hourly.py
    _c.pop("hourly", None)
CFG["channels"]["xojaobod"]["mode"] = "live"
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}
TZ = plan.TZ


def at(hm, day=dt.date(2026, 10, 21)):
    h, m = map(int, hm.split(":"))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)


class Acc:
    def __init__(self):
        self.sent = []

    async def publish(self, chat, body, hub_chat=None, hub_msg=None, has_media=False):
        self.sent.append((chat, body, hub_chat, hub_msg, has_media)); return 77

    async def publish_album(self, chat, hub_chat, ids, body):
        self.sent.append((chat, body, hub_chat, ids)); return 78

    async def publish_file(self, chat, path, body, duration=15):
        if getattr(self, "fail_file", False):
            from genplan.publish import PublishError
            raise PublishError("FILE_PARTS_INVALID")
        self.sent.append((chat, body, "FILE", Path(path).name)); return 79


class BotPub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, body, hub_chat=None, hub_msg=None, has_media=False, button=None):
        self.sent.append((chat, body)); return 5


W = {"Хўжаобод": {"t": 10, "code": 0, "night": False}}
R = {"USD": {"rate": 12044.72}, "EUR": {"rate": 13525.02}}


class T(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(str(Path(tempfile.mkdtemp()) / "g.db"))
        self.pubs = {"account": Acc(), "bot": BotPub()}
        service.ERRORS.clear()

    def tick(self, now, fetch=None):
        return asyncio.run(service.tick_extras(self.db, CFG, ENV, self.pubs, now, lambda *_: None, fetch=fetch))

    def test_info_text_like_genplan5(self):
        t = extras.info_text(CFG["channels"]["xojaobod"], W, R, dt.date(2026, 10, 21))
        self.assertTrue(t.startswith("#ОБ_ҲАВО"))
        self.assertIn("Хўжаобод: ҳозир +10°, очиқ ҳаво", t)
        self.assertIn("USD — 12 044,72 сўм | EUR — 13 525,02 сўм", t)
        w2 = {"Хўжаобод": {"t": 8, "code": 0, "night": False, "today": {"min": 7, "max": 21}}}
        self.assertIn("ҳозир +8°, кундузи +21° гача, очиқ ҳаво", extras.info_text(CFG["channels"]["xojaobod"], w2, R, dt.date(2026, 10, 21)))
        self.assertIn("@XOJAOBODCITY24", t)
        self.assertIsNone(extras.info_text(CFG["channels"]["xojaobod"], None, None, dt.date(2026, 10, 21)))

    def patch_data(self, video=None):
        from genplan import digest
        orig = (digest.weather, digest.rates, extras.weather_video)
        digest.weather, digest.rates = (lambda get: W), (lambda get: R)
        extras.weather_video = video or (lambda day: (_ for _ in ()).throw(ValueError("ролик не собран")))
        self.addCleanup(lambda: (setattr(digest, "weather", orig[0]), setattr(digest, "rates", orig[1]),
                                 setattr(extras, "weather_video", orig[2])))

    def fake_video(self, day):
        f = Path(tempfile.mkdtemp()) / f"xojaobod-weather-{day}.mp4"
        f.write_bytes(b"\0\0\0\x18ftypmp42" + b"0" * 300_000)
        self.vid = f
        return f

    def test_info_video_0700(self):
        self.patch_data(self.fake_video)
        self.assertEqual(self.tick(at("07:00")), 1)
        chat, body, kind, name = self.pubs["account"].sent[0]
        self.assertEqual((chat, kind, name), ("@xojaobodcity24", "FILE", "xojaobod-weather-2026-10-21.mp4"))
        self.assertIn("💱", body)                                      # подпись — прежний текст (погода + курс)
        self.assertFalse(self.vid.exists())                            # временный файл убран
        self.assertEqual(service.ERRORS, [])

    def test_info_video_missing_text_fallback(self):
        self.patch_data()                                              # ролик не собран → текст + сообщение владельцу
        self.assertEqual(self.tick(at("07:00")), 1)
        self.assertEqual(len(self.pubs["account"].sent[0]), 5)        # обычный publish
        self.assertTrue(any("ролик погоды не готов" in e for e in service.ERRORS))

    def test_info_video_send_fails_text_fallback(self):
        self.patch_data(self.fake_video)
        self.pubs["account"].fail_file = True
        self.assertEqual(self.tick(at("07:00")), 1)
        self.assertEqual(len(self.pubs["account"].sent[0]), 5)
        self.assertTrue(any("не отправился" in e for e in service.ERRORS))
        self.assertFalse(self.vid.exists())

    def test_weather_video_checks(self):
        d = dt.date(2026, 10, 21)
        with self.assertRaises(ValueError):
            extras.weather_video(d, get=lambda u: b"404: Not Found")
        seen = []
        f = extras.weather_video(d, get=lambda u: seen.append(u) or b"\0\0\0\x18ftypmp42" + b"0" * 300_000,
                                 folder=tempfile.mkdtemp())
        self.assertTrue(seen[0].endswith("/motion/xojaobod-weather-2026-10-21.mp4"))
        self.assertTrue(f.exists())

    def test_info_published_0700_by_account(self):
        self.patch_data()
        self.assertEqual(self.tick(at("06:59")), 0)
        self.assertEqual(self.tick(at("07:00")), 1)
        chat, body, *_ = self.pubs["account"].sent[0]
        self.assertEqual(chat, "@xojaobodcity24")
        self.assertIn("💱", body)
        self.assertEqual(self.tick(at("07:05")), 0)                   # один раз в день

    def test_no_false_missed_on_start(self):
        self.tick(at("15:00"))                                         # служба запущена днём — 07:00 не «пропущен»
        self.assertEqual(service.ERRORS, [])

    def test_final_post_every_day_until_replaced(self):
        mid = store.add_material(self.db, -100777, 55, "#муфтий_минбари\n\nТарози босувчи икки калима", True)
        store.update(self.db, mid, channel="xojaobod")
        extras.final_set(self.db, "xojaobod", store.get(self.db, mid))
        self.assertEqual(store.get(self.db, mid)["status"], "rejected")     # не ждёт обычной публикации
        for day in (dt.date(2026, 10, 21), dt.date(2026, 10, 22)):
            self.assertEqual(self.tick(at("22:00", day)), 1)
        self.assertEqual(len(self.pubs["account"].sent), 2)
        chat, body, hub_chat, hub_msg, media = self.pubs["account"].sent[1]
        self.assertEqual((chat, hub_chat, hub_msg, media), ("@xojaobodcity24", -100777, 55, True))
        self.assertTrue(body.startswith("#МУФТИЙ_МИНБАРИ\n"))
        self.assertEqual(body.count("#"), 1)                                   # 22.10: один хэштег

    def test_final_post_cleaned_and_signed(self):
        """22.10 аудит: Якуний пост — с юзернеймом канала, рубрика кириллицей, чужой призыв убран."""
        src = "#muftiy_minbari\n\nRahmonning bandalari\n🎙 Shayx Nuriddin Xoliqnazar hazratlari\n\n📲 OBUNA BO'LING ✅ VA ULASHING"
        mid = store.add_material(self.db, -100777, 56, src, True)
        store.update(self.db, mid, channel="xojaobod")
        extras.final_set(self.db, "xojaobod", store.get(self.db, mid))
        self.assertEqual(self.tick(at("22:00")), 1)
        body = self.pubs["account"].sent[0][1]
        self.assertTrue(body.startswith("#МУФТИЙ_МИНБАРИ\n"), body)
        self.assertIn("Раҳмоннинг бандалари", body)
        self.assertNotIn("muftiy", body)
        self.assertIn("@XOJAOBODCITY24", body.upper())
        self.assertEqual(body.count("#"), 1)

    def test_ad_package_daily_same_time(self):
        mid = store.add_material(self.db, -100777, 60, "🔥 ЎТИНЛАР СОТИЛАДИ!", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        c = extras.campaign_from(self.db, store.get(self.db, mid), 3)
        self.assertIn("Ср–Пт · 3 дня · каждый день 17:30 (21.10–23.10)", extras.campaign_note(c))
        self.assertEqual(extras.ensure_campaigns(self.db, at("08:00")), [])          # день 1 — сам исходный пост
        for d in (22, 23):
            made = extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, d)))
            self.assertEqual(len(made), 1)
            m = store.get(self.db, made[0])
            self.assertEqual((m["status"], m["rubric"], m["hub_msg"], m["locked"]), ("queued", "Реклама", 60, 1))
            self.assertEqual(m["scheduled_at"][11:16], "17:30")
            self.assertEqual(extras.ensure_campaigns(self.db, at("09:00", dt.date(2026, 10, d))), [])   # не дублирует
        self.assertEqual(extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 24))), [])    # пакет кончился
        self.assertEqual(self.db.execute("SELECT status FROM ad_campaigns").fetchone()[0], "done")

    def test_pult_buttons(self):
        mid = store.add_material(self.db, -100777, 61, "Реклама матни", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        _, kb = hub.card(self.db, CFG, mid, at("08:00"))
        flat = [b for row in kb["inline_keyboard"] for b in row]
        self.assertEqual([b["text"] for b in flat[:2]], ["✅ Разовая", "📅 Несколько дней"])
        self.assertNotIn("кун", json.dumps(kb, ensure_ascii=False))
        days = [b["text"] for row in hub.kb_days(store.get(self.db, mid))["inline_keyboard"] for b in row]
        self.assertEqual(days[:6], ["до Чт · 2 дня", "до Пт · 3 дня", "до Сб · 4 дня", "до Вс · 5 дней",
                                    "до Пн · 6 дней", "до Вт · 7 дней"])
        self.assertIn("Якуний пост", hub.rubrics(CFG, "xojaobod"))

    def test_once_cancels_package(self):
        mid = store.add_material(self.db, -100777, 62, "Реклама матни", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        extras.campaign_from(self.db, store.get(self.db, mid), 4)
        _, kb = hub.card(self.db, CFG, mid, at("08:00"))
        flat = [b["text"] for row in kb["inline_keyboard"] for b in row]
        self.assertEqual(flat[:2], ["Разовая", "✅ 📅 до Сб · 4 дня"])
        made = extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 22)))
        self.assertEqual(extras.campaign_stop(self.db, mid), 1)
        self.assertEqual(store.get(self.db, made[0])["status"], "rejected")
        self.assertEqual(extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 23))), [])
        self.assertIn("✅ Разовая", hub.card(self.db, CFG, mid, at("08:00"))[0])

    def test_once_button_answers_when_already_once(self):
        mid = store.add_material(self.db, -100777, 65, "Реклама", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())

        class Bot:
            calls = []

            def __call__(self, method, **p):
                self.calls.append((method, p))
                if method == "editMessageText":
                    raise RuntimeError("Bad Request: message is not modified")
                return {}
        b = Bot()
        q = {"id": "q", "from": {"id": 42}, "data": f"p1:{mid}", "message": {"chat": {"id": 42}, "message_id": 5}}
        self.assertEqual(hub.callback(b, self.db, CFG, {42}, q, at("08:00")), "p1")
        q["data"] = f"p1y:{mid}"
        self.assertEqual(hub.callback(b, self.db, CFG, {42}, q, at("08:00")), "p1y")
        self.assertIn("✅ Утверждено", [p for m, p in b.calls if m == "editMessageText"][-1]["text"])   # в карточке
        self.assertEqual(b.calls[-1], ("answerCallbackQuery", {"callback_query_id": "q"}))          # без всплывашки
        _, kb = hub.card(self.db, CFG, mid, at("08:00"))
        self.assertEqual(kb["inline_keyboard"][0][0]["text"], "✅ Разовая · утверждено")
        q["data"] = f"bk:{mid}"
        self.assertEqual(hub.callback(b, self.db, CFG, {42}, q, at("08:00")), "bk")   # «не изменилось» не ломает

    def test_days_need_approve(self):
        mid = store.add_material(self.db, -100777, 66, "Реклама", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        bot = lambda method, **p: {}  # noqa: E731
        q = {"id": "q", "from": {"id": 42}, "data": f"pk:{mid}:4", "message": {"chat": {"id": 42}, "message_id": 5}}
        hub.callback(bot, self.db, CFG, {42}, q, at("08:00"))
        self.assertIsNone(extras.campaign_of(self.db, mid))                  # без «Утверждаю» пакета нет
        q["data"] = f"pky:{mid}:4"
        hub.callback(bot, self.db, CFG, {42}, q, at("08:00"))
        self.assertEqual(extras.campaign_of(self.db, mid)["days"], 4)
        _, kb = hub.card(self.db, CFG, mid, at("08:00"))
        self.assertEqual(kb["inline_keyboard"][0][1]["text"], "✅ 📅 до Сб · 4 дня · утверждено")

    def test_busy_day_moves_to_ad_window(self):
        mid = store.add_material(self.db, -100777, 63, "Реклама", True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at("17:30").isoformat())
        extras.campaign_from(self.db, store.get(self.db, mid), 2)
        other = store.add_material(self.db, -100777, 64, "Бошқа пост", True)
        store.update(self.db, other, channel="xojaobod", rubric="Янгилик", status="queued",
                     scheduled_at=at("17:30", dt.date(2026, 10, 22)).isoformat())
        made = extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 22)), CFG)
        self.assertEqual(store.get(self.db, made[0])["scheduled_at"][11:16], "15:10")   # 17:40 вплотную к посту — ближайшее свободное окно


class Campaigns(unittest.TestCase):
    """23.10 владелец: «верни старую схему — ставишь кампанию, знаешь, какая стоит, название»."""
    def setUp(self):
        self.db = store.connect(str(Path(tempfile.mkdtemp()) / "g.db"))
        self.calls = []

    def bot(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}

    def ad(self, hub_msg, text, hm="17:30", day=dt.date(2026, 10, 21)):
        mid = store.add_material(self.db, -100777, hub_msg, text, True)
        store.update(self.db, mid, channel="xojaobod", rubric="Реклама", status="queued", scheduled_at=at(hm, day).isoformat())
        return mid

    def q(self, data):
        return {"id": "q", "from": {"id": 42}, "data": data, "message": {"chat": {"id": 42}, "message_id": 5}}

    def last_text(self):
        return [p for m, p in self.calls if m in ("editMessageText", "sendMessage")][-1]["text"]

    def test_name_numbering_and_card(self):
        a = self.ad(70, "🔥 ИЖАРАГА УЙ БЕРИЛАДИ\nТел 90 123")
        b = self.ad(71, "Утин сотилади", "18:30")
        self.assertIn("🏷 Название: не задано", hub.card(self.db, CFG, a, at("08:00"))[0])
        self.assertEqual(extras.ad_name_set(self.db, a, "  ижара "), (13, "ижара"))
        self.assertEqual(extras.ad_name_set(self.db, b, "ЎТИН"), (14, "ЎТИН"))
        self.assertEqual(extras.ad_name_set(self.db, a, "ИЖАРА"), (13, "ИЖАРА"))     # переименование — № тот же
        t, kb = hub.card(self.db, CFG, a, at("08:00"))
        self.assertIn("🏷 Кампания: №13 · ИЖАРА", t)
        flat = [x["text"] for row in kb["inline_keyboard"] for x in row]
        self.assertIn("🏷 Название", flat)
        self.assertIn("📢 Мои кампании", flat)

    def test_auto_name_on_approve(self):
        a = self.ad(72, "#РЕКЛАМА\n🔥 Янги дўкон очилди! Марҳамат")
        hub.callback(self.bot, self.db, CFG, {42}, self.q(f"p1y:{a}"), at("08:00"))
        self.assertEqual(extras.ad_name(self.db, a), (13, "ЯНГИ ДЎКОН ОЧИЛДИ!"))
        self.assertIn("№13 · ЯНГИ ДЎКОН ОЧИЛДИ!", self.last_text())

    def test_typed_name_is_taken_only_when_waiting(self):
        a = self.ad(73, "Реклама матни")
        hub.callback(self.bot, self.db, CFG, {42}, self.q(f"an:{a}"), at("08:00"))
        self.assertEqual(hub.name_waiting(self.db, at("08:05")), a)
        self.assertFalse(hub.looks_like_name("Узун\nкўп қаторли пост"))
        r = hub.take_name(self.bot, self.db, CFG, a, "ИЖАРА", 42, at("08:05"))
        self.assertEqual(r, "ad_name")
        self.assertIn("🏷 Название: №13 · ИЖАРА", self.last_text())
        self.assertIsNone(hub.name_waiting(self.db, at("08:06")))
        hub.name_wait(self.db, a, at("08:00"))
        self.assertIsNone(hub.name_waiting(self.db, at("08:20")))                  # забытое ожидание истекает

    def test_list_stop_extend(self):
        a = self.ad(74, "Ижара", "17:30")
        extras.campaign_from(self.db, store.get(self.db, a), 4)
        extras.ad_name_set(self.db, a, "ИЖАРА")
        b = self.ad(75, "Утин", "18:30", dt.date(2026, 10, 22))
        extras.ad_name_set(self.db, b, "ЎТИН")
        t, kb = hub.ads_screen(self.db, CFG, "xojaobod", at("08:00"))
        self.assertIn("№13 ИЖАРА · 17:30 · день 1 из 4 (до Сб 24.10)", t)
        self.assertIn("№14 ЎТИН · 18:30 · разовая", t)
        self.assertNotIn("⚠️", t)
        # ➕ день — только после «Утверждаю»
        self.assertEqual(hub.ads_callback(self.bot, self.db, CFG, self.q(f"ax:{a}"), at("08:00")), "ax")
        self.assertEqual(extras.campaign_of(self.db, a)["days"], 4)
        hub.ads_callback(self.bot, self.db, CFG, self.q(f"axy:{a}"), at("08:00"))
        self.assertEqual(extras.campaign_of(self.db, a)["days"], 5)
        hub.ads_callback(self.bot, self.db, CFG, self.q(f"axy:{b}"), at("08:00"))      # разовая → 2 дня
        self.assertEqual(extras.campaign_of(self.db, b)["days"], 2)
        # ⏸ Стоп — показы убраны, пакет больше не создаёт новых
        made = extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 22)))
        hub.ads_callback(self.bot, self.db, CFG, self.q(f"as:{a}"), at("09:00", dt.date(2026, 10, 22)))
        self.assertEqual(extras.campaign_of(self.db, a)["status"], "active")           # без «Утверждаю» не трогаем
        hub.callback(self.bot, self.db, CFG, {42}, self.q(f"asy:{a}"), at("09:00", dt.date(2026, 10, 22)))
        self.assertIn("✅ Остановлено: «№13 · ИЖАРА»", self.last_text())
        self.assertEqual(store.get(self.db, made[0])["status"], "rejected")
        nxt = extras.ensure_campaigns(self.db, at("08:00", dt.date(2026, 10, 23)))      # только ЎТИН (день 2)
        self.assertEqual([extras.ad_source(self.db, x) for x in nxt], [b])
        t, _ = hub.ads_screen(self.db, CFG, "xojaobod", at("09:00", dt.date(2026, 10, 22)))
        self.assertNotIn("ИЖАРА", t)
        self.assertIn("ЎТИН", t)

    def test_same_time_warning(self):
        a = self.ad(76, "Бир", "17:30")
        extras.campaign_from(self.db, store.get(self.db, a), 3)
        self.ad(77, "Икки", "17:30", dt.date(2026, 10, 22))
        t, _ = hub.ads_screen(self.db, CFG, "xojaobod", at("08:00"))
        self.assertIn("⚠️ Две рекламы на одно время", t)

    def test_panel_button_shows_list(self):
        from genplan import menu
        a = self.ad(78, "Ижара")
        extras.ad_name_set(self.db, a, "ИЖАРА")
        t = menu.panel_reply(self.db, CFG, "xojaobod", menu.P_ADS, at("08:00"))
        self.assertIn("➕ Новая кампания", t)
        self.assertIn("📢 Мои кампании", t)
        self.assertIn("№13 ИЖАРА", t)
        kb = menu.panel_markup(CFG, "xojaobod", menu.P_ADS, db=self.db, now=at("08:00"))
        self.assertEqual(kb["inline_keyboard"][0][2]["callback_data"], f"as:{a}")
        empty = store.connect(str(Path(tempfile.mkdtemp()) / "e.db"))
        self.assertEqual(menu.panel_markup(CFG, "xojaobod", menu.P_ADS, db=empty), menu.PANEL)

    def test_published_card_has_name(self):
        a = self.ad(79, "Ижара")
        extras.ad_name_set(self.db, a, "ИЖАРА")
        store.update(self.db, a, status="published")
        self.assertIn("Реклама «№13 · ИЖАРА» — опубликовано", hub.card(self.db, CFG, a, at("18:00"))[0])


if __name__ == "__main__":
    unittest.main()


class HubCopyCleanup(unittest.TestCase):
    """21.10 владелец: служебная копия в PAPA HUB после выхода поста группы — удаляется (кроме рекламы/пакетов/Якуний)."""
    def setUp(self):
        self.db = store.connect(str(Path(tempfile.mkdtemp()) / "g.db"))
        extras.setup(self.db)
        self.calls = []
        outer = self

        class P:
            def http(self, method, payload):
                outer.calls.append((method, payload)); return {"ok": True}
        self.pubs = {"bot": P(), "bot:xojaobod": P()}

    def mat(self, hub_msg=501):
        mid = store.add(self.db, channel="xojaobod", text="т", hub_chat=-100777, hub_msg=hub_msg, has_media=1) \
            if hasattr(store, "add") else None
        return mid

    def row(self, mid=1, hub_msg=501, via="xojaobod"):
        return {"id": mid, "hub_chat": -100777, "hub_msg": hub_msg, "hub_msgs": json.dumps([hub_msg]), "via": via}

    class R(dict):
        def keys(self):
            return super().keys()

    def test_deletes_own_copy(self):
        store.kv_set(self.db, "hubcopy_501", "1")
        n = service.cleanup_hubcopy(self.db, ENV, self.pubs, self.R(self.row()), lambda *_: None)
        self.assertEqual(n, 1)
        self.assertEqual(self.calls, [("deleteMessages", {"chat_id": -100777, "message_ids": [501]})])
        self.assertIsNone(store.kv_get(self.db, "hubcopy_501"))

    def test_keeps_owner_material_in_papa_hub(self):
        self.assertEqual(service.cleanup_hubcopy(self.db, ENV, self.pubs, self.R(self.row()), lambda *_: None), 0)
        self.assertEqual(self.calls, [])

    def test_keeps_final_post(self):
        store.kv_set(self.db, "hubcopy_501", "1")
        store.kv_set(self.db, "final_xojaobod", json.dumps({"material_id": 9, "hub_msg": 501}))
        self.assertEqual(service.cleanup_hubcopy(self.db, ENV, self.pubs, self.R(self.row()), lambda *_: None), 0)
