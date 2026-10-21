import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import json  # noqa: E402
from genplan import hub, menu, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
CFG["channels"]["xojaobod"].pop("mode", None)   # 20.10 группа в работе; эти тесты проверяют режим теста
CFG["auto_place"] = False          # эти тесты проверяют ручной выбор рубрики
CFG["auto_channels"] = ["davra"]   # и канал по умолчанию
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}


class FakeBot:
    def __init__(self):
        self.calls = []

    def __call__(self, method, **p):
        self.calls.append((method, p))
        return {"message_id": 900 + len(self.calls)}


def post(mid, text="Янгилик @bugungi_gap", photo=True):
    p = {"message_id": mid, "chat": {"id": -100777}, "caption" if photo else "text": text}
    if photo:
        p["photo"] = [{}]
    return {"channel_post": p}


def cb(data, uid=42):
    return {"callback_query": {"id": "q", "from": {"id": uid}, "data": data, "message": {"chat": {"id": 42}, "message_id": 5}}}


TZ = plan.TZ
MON = dt.date(2026, 10, 19)


def at(hhmm, day=MON):
    return plan.slot_time(day, hhmm)


def dm(mid, text="", photo_uid=None, gid=None, audio=False):
    m = {"message_id": mid, "from": {"id": 42}, "chat": {"id": 42, "type": "private"}}
    if photo_uid:
        m["photo"] = [{"file_id": "f" + photo_uid, "file_unique_id": photo_uid}]
        m["caption"] = text
    elif audio:
        m["audio"] = {"file_id": "a", "file_unique_id": "au"}
    else:
        m["text"] = text
    if gid:
        m["media_group_id"] = gid
    return {"message": m}


def cb(data, uid=42):
    return {"callback_query": {"id": "q", "from": {"id": uid}, "data": data, "message": {"chat": {"id": 42}, "message_id": 5}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.db, self.bot = store.connect(":memory:"), FakeBot()
        hub.ALBUMS.clear()

    def h(self, u):
        return hub.handle(self.bot, self.db, CFG, ENV, u)

    def tap(self, data, now, confirm=True):
        """Нажатие владельца. 21.10: выбор вступает в силу после «✅ Утверждаю» — тест жмёт его следом (confirm=False — нет)."""
        r = hub.callback(self.bot, self.db, CFG, {42}, cb(data)["callback_query"], now)
        if r == "confirm" and confirm:
            return hub.callback(self.bot, self.db, CFG, {42}, cb("ok:" + data)["callback_query"], now)
        return r

    def last_card(self):
        return [p for m, p in self.bot.calls if m in ("sendMessage", "editMessageText")][-1]


class TestIntake(Base):
    def test_one_tap_smart_time(self):
        self.assertEqual(self.h(dm(10, "Янги қўшиқ чиқди! 🎧 Тинглаб кўринг", photo_uid="u1")), "material")
        self.assertEqual(self.bot.calls[0][0], "sendMessage")                 # 16.10: без хаба — сразу карточка
        m = store.get(self.db, 1)
        self.assertEqual((m["channel"], m["rubric"], m["status"]), ("davra", "Мусиқа", "draft"))   # канал и рубрика — сами
        now = at("08:00")
        txt, kb = hub.card(self.db, CFG, 1, now)
        self.assertIn("Выберите рубрику", txt)
        flat = [b for row in kb["inline_keyboard"] for b in row]
        music = next(b for b in flat if b["text"] == "🎵 Музыка")              # экран групп как в Хўжаободе
        self.tap(music["callback_data"], now)
        sub = [b for row in self.last_card()["reply_markup"]["inline_keyboard"] for b in row]
        uz = next(b for b in sub if "ЎЗБЕК МУСИҚАСИ" in b["text"])
        self.tap(uz["callback_data"], now)                                     # одно нажатие: рубрика + хэштег + умное время
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], m["rubric"], m["tag"]), ("queued", "Мусиқа", "#ЎЗБЕК_МУСИҚАСИ"))
        self.assertEqual(dt.datetime.fromisoformat(m["scheduled_at"]), at("19:45"))   # музыка не раньше 10:00, слот «Мусиқа»
        self.assertIn("✅", self.last_card()["text"])

    def test_gap_and_next_slot(self):
        now = at("08:00")
        for i, mid in ((1, 20), (2, 21)):
            self.h(dm(mid, f"Янги клип {i} чиқди, қўшиқ зўр", photo_uid=f"g{i}"))
            st = smart.smart_time(self.db, CFG, "davra", "Мусиқа", now, exclude=i)
            self.tap(f"sm:{i}:{int(st[0].timestamp())}", now)
        t = [dt.datetime.fromisoformat(store.get(self.db, i)["scheduled_at"]) for i in (1, 2)]
        self.assertEqual(t, [at("19:45"), at("21:30")])                       # второй — в слот, где «Мусиқа» запасная

    def test_stale_time_refreshes(self):
        now = at("08:00")
        self.h(dm(30, "Видео 1", photo_uid="s1")); self.h(dm(31, "Видео 2", photo_uid="s2"))
        t = int(smart.smart_time(self.db, CFG, "davra", "Видео", now, exclude=1)[0].timestamp())
        self.tap(f"sm:1:{t}", now)
        self.tap(f"sm:2:{t}", now)                                            # то же время уже занято
        self.assertEqual(store.get(self.db, 2)["status"], "draft")
        self.assertIn("Это время уже занято — показываю новое", self.last_card()["text"])   # 21.10: в карточке

    def test_tomorrow_when_today_full(self):
        self.h(dm(40, "Ҳажвия 😂 кулги", photo_uid="h1"))
        st = smart.smart_time(self.db, CFG, "davra", "Ҳажвия", at("21:00"))
        self.assertEqual(st[0], at("09:45", MON + dt.timedelta(days=1)))      # хороший пост — на завтра, не пропадает

    def test_window_and_other_times(self):
        ts = smart.other_times(self.db, CFG, "davra", "Видео", at("21:59"), n=3)
        self.assertTrue(all(dt.time(7, 0) <= t.time() <= dt.time(22, 0) for t in ts))
        self.assertEqual(ts[0], at("07:00", MON + dt.timedelta(days=1)))

    def test_duplicate_warning(self):
        self.h(dm(50, "Пост", photo_uid="same"))
        self.tap(f"ur:1", at("12:00"))
        self.h(dm(51, "Пост ещё раз", photo_uid="same"))
        txt, _ = hub.card(self.db, CFG, 2, at("12:05"))
        self.assertIn("Повтор можно", txt)

    def test_album_one_material(self):
        self.assertEqual(self.h(dm(60, "Альбом", photo_uid="a1", gid="G")), "album")
        self.assertEqual(self.h(dm(61, "", photo_uid="a2", gid="G")), "album")
        bot = lambda m, **p: (self.bot.calls.append((m, p)) or ([{"message_id": 700}, {"message_id": 701}] if m == "copyMessages" else {"message_id": 800}))
        self.assertEqual(hub.flush_albums(bot, self.db, CFG, ENV, now_ts=10**10), 1)
        m = store.get(self.db, 1)
        self.assertEqual(json.loads(m["hub_msgs"]), [60, 61])               # 16.10: альбом берётся прямо из чата с ботом
        self.assertEqual(len(json.loads(m["media"])), 2)
        self.assertEqual(m["text"], "Альбом")

    def test_change_channel_both_and_owner_only(self):
        self.h(dm(70, "Шоу янгилик", photo_uid="c1"))
        self.assertEqual(hub.callback(self.bot, self.db, CFG, {42}, cb("cs:1", uid=7)["callback_query"]), "denied")
        self.tap("ch:1:b", at("09:00"))
        rows = self.db.execute("SELECT channel, status FROM materials ORDER BY id").fetchall()
        self.assertEqual([tuple(r) for r in rows], [("davra", "draft"), ("paparazzi", "draft")])
        self.tap("del:2", at("09:00"))
        self.assertEqual(store.get(self.db, 2)["status"], "rejected")

    def test_manual_post_in_channel_counts(self):
        ts = int(at("12:00").timestamp())
        self.assertEqual(self.h({"channel_post": {"message_id": 1, "date": ts, "chat": {"id": -1, "username": "kattadavrauz"}}}), "pulse")
        busy = smart.occupied(self.db, "davra", at("11:50"))
        self.assertFalse(smart.is_free(CFG["channels"]["davra"], at("12:00"), busy))

    def test_rubric_change_and_back(self):
        self.h(dm(80, "Матн", photo_uid="r1"))
        i = hub.rubrics(CFG, "davra").index("Ҳажвия")
        self.tap(f"rb:1:{i}", at("09:00"))
        self.assertEqual((store.get(self.db, 1)["rubric"], store.get(self.db, 1)["guessed"]), ("Ҳажвия", 0))


class TestStock(Base):
    def test_stock_fills_empty_slot(self):
        self.h(dm(90, "Кулги видео 😂", photo_uid="k1"))
        i = hub.rubrics(CFG, "davra").index("Ҳажвия")
        self.tap("sr:1", at("07:00"))
        self.tap(f"sk:1:{i}", at("07:00"))
        m = store.get(self.db, 1)
        self.assertEqual((m["stock"], m["status"], m["scheduled_at"]), (1, "draft", None))
        self.assertIn("📦 В запасе", hub.card(self.db, CFG, 1, at("07:00"))[0])
        self.assertIn("📦 В запасе: Ҳажвия 1", smart.day_view(self.db, CFG, "davra", at("07:00")))
        self.assertEqual(smart.fill_from_stock(self.db, CFG, "davra", at("07:00")), [])      # 09:45 ещё далеко
        self.assertEqual(smart.fill_from_stock(self.db, CFG, "davra", at("08:30")), [1])     # слот «Ҳажвия» 09:45 пуст
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], dt.datetime.fromisoformat(m["scheduled_at"])), ("queued", at("09:45")))

    def test_stock_not_used_when_slot_busy(self):
        self.h(dm(91, "Ҳажвия 1", photo_uid="k2")); self.h(dm(92, "Ҳажвия 2", photo_uid="k3"))
        i = hub.rubrics(CFG, "davra").index("Ҳажвия")
        self.tap(f"rq:1:{i}", at("08:30"))                       # первый — в план на 09:45
        self.tap(f"sk:2:{i}", at("08:30"))                       # второй — в запас
        self.assertEqual(smart.fill_from_stock(self.db, CFG, "davra", at("08:30")), [])


class FakeAcc:
    def __init__(self):
        self.sent = []

    async def publish(self, chat, body, hub_chat, hub_msg, has_media):
        self.sent.append((chat, body)); return 1

    async def publish_album(self, chat, hub_chat, hub_ids, caption):
        self.sent.append((chat, caption, hub_ids)); return 3


class FakeBotPub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, body, hub_chat, hub_msg, has_media, button=None):
        self.sent.append((chat, body, button)); return 2

    def publish_album(self, chat, media, caption):
        self.sent.append((chat, caption, media)); return 4


class TestService(Base):
    def setUp(self):
        super().setUp()
        self.pubs = {"account": FakeAcc(), "bot": FakeBotPub()}

    def queue(self, channel, rubric, when, urgent=False, hub_msg=None, locked=0):
        mid = store.add_material(self.db, -100777, hub_msg or (100 + len(self.db.execute("SELECT id FROM materials").fetchall())),
                                 "Матн @bugungi_gap", True)
        store.update(self.db, mid, channel=channel, rubric=rubric, status="queued", urgent=int(urgent),
                     scheduled_at=when.isoformat(), locked=locked)
        return mid

    def tick(self, now):
        return asyncio.run(service.tick(self.db, CFG, ENV, self.pubs, now, lambda *_: None))

    def test_due_publishes_once_live_and_shadow(self):
        self.queue("davra", "Видео", at("17:00"))
        self.queue("xojaobod", "Ҳажвия", at("16:30"))
        self.assertEqual(self.tick(at("16:59"))["published"], 1)              # Хўжаобод (16:30) — да, Давра (17:00) — ещё нет
        self.assertEqual(self.pubs["account"].sent[0][0], -100111)            # Хўжаобод — тест
        r = self.tick(at("17:00"))
        chat, body, button = self.pubs["bot"].sent[0]
        self.assertEqual(chat, "@kattadavrauz")                               # Давра — рабочий канал
        self.assertNotIn("bugungi", body)
        self.assertIn("@kattadavrauz", body.split("\n\n")[-1].splitlines()[0])   # текст → подпись с @юзернеймом → призыв
        self.assertEqual(button["text"], "📲 Дўстларга улашиш")
        self.assertEqual(self.tick(at("17:05"))["published"], 0)              # второй раз не публикует

    def test_urgent_now_shifts_neighbours(self):
        a = self.queue("davra", "Видео", at("17:10"))
        self.queue("davra", "Мусиқа", at("17:00"), urgent=True)
        self.tick(at("17:00"))
        moved = dt.datetime.fromisoformat(store.get(self.db, a)["scheduled_at"])
        self.assertGreaterEqual(moved - at("17:00"), dt.timedelta(minutes=40))  # сосед отодвинут на промежуток

    def test_locked_not_moved_and_album(self):
        a = self.queue("davra", "Видео", at("17:10"), locked=1)
        store.update(self.db, a, hub_msgs=json.dumps([5, 6]), media=json.dumps([{"type": "photo", "file_id": "x"}, {"type": "photo", "file_id": "y"}]))
        self.queue("davra", "Мусиқа", at("17:00"), urgent=True)
        self.tick(at("17:00"))
        self.assertEqual(dt.datetime.fromisoformat(store.get(self.db, a)["scheduled_at"]), at("17:10"))   # 🔒 не трогаем
        self.tick(at("17:10"))
        self.assertEqual(len(self.pubs["bot"].sent[-1][2]), 2)               # альбом — одним постом

    def test_late_is_rescheduled(self):
        a = self.queue("davra", "Видео", at("08:00"))
        r = self.tick(at("12:30"))
        self.assertEqual((r["published"], r["moved"]), (0, 1))
        self.assertGreater(dt.datetime.fromisoformat(store.get(self.db, a)["scheduled_at"]), at("12:30"))

    def test_legacy_queue_gets_time(self):
        mid = store.add_material(self.db, -100777, 9, "Эски", True)
        store.update(self.db, mid, channel="paparazzi", rubric="Қўшиқ", status="queued")
        self.assertEqual(service.reconcile(self.db, CFG, at("09:00")), 1)
        self.assertIsNotNone(store.get(self.db, mid)["scheduled_at"])

    def test_targets(self):
        self.assertEqual(service.target(CFG, ENV, "davra"), "@kattadavrauz")
        self.assertEqual(service.target(CFG, ENV, "paparazzi"), "@ozodjamoll")   # в работе с 16.10
        self.assertEqual(service.target(CFG, ENV, "xojaobod"), -100111)

    def test_today_text(self):
        self.queue("davra", "Мусиқа", at("13:30"))
        t = service.today_text(self.db, CFG, at("09:00"))
        self.assertIn("🟢 работа", t)
        self.assertIn("⏳ 13:30  Мусиқа", t)
        self.assertIn("⚠️ 10:30  Фойдали видео — нет материала", t)


class TestMenu(unittest.TestCase):
    def test_buttons(self):
        from genplan import menu
        db = store.connect(":memory:")
        self.assertIn("КАТТА ДАВРА", menu.reply(db, CFG, menu.B_DAVRA) or "") if "davra" in CFG["channels"] else None
        self.assertIn("📋", menu.reply(db, CFG, menu.B_QUEUE))
        self.assertIn("📊 Итог дня", menu.reply(db, CFG, menu.B_TODAY))
        self.assertIn("умное время", menu.reply(db, CFG, "/start"))
        self.assertIsNone(menu.reply(db, CFG, "просто текст"))
        self.assertFalse(menu.KEYBOARD["is_persistent"])






class TestNextMandatoryBomdod(unittest.TestCase):
    """20.10: у Хўжаобода утро «bomdod-45|05:00» — ХАБ падал ValueError при подсказке ближайшего обязательного поста."""
    def test_bomdod_spec(self):
        import datetime as dt
        import tempfile
        import tomllib
        from pathlib import Path
        from genplan import plan, smart, store
        cfg = tomllib.loads((Path(__file__).resolve().parents[1] / "config.toml").read_text(encoding="utf-8"))
        db = store.connect(str(Path(tempfile.mkdtemp()) / "g.db"))
        now = dt.datetime(2026, 10, 20, 3, 0, tzinfo=plan.TZ)
        r = smart.next_mandatory(db, cfg, "xojaobod", now)
        self.assertIsNotNone(r)
        self.assertEqual(r[0].strftime("%H:%M"), "05:00")      # без времени намаза — запасное 05:00

if __name__ == "__main__":
    unittest.main()


class TestAutoPlace(unittest.TestCase):
    def test_dropped_post_is_placed_automatically(self):
        cfg = {**CFG, "auto_place": True}
        db = store.connect(":memory:")
        bot = Bot() if "Bot" in globals() else None
        calls = []

        def b(m, **p):
            calls.append((m, p)); return {"message_id": len(calls)}
        msg = {"message_id": 5, "caption": "Кулгили видео 😂 @begona", "video": {"file_id": "F", "file_unique_id": "U"}}
        hub.intake(b, db, cfg, {42}, -100777, [5], [msg])
        m = db.execute("SELECT * FROM materials").fetchone()
        self.assertEqual(m["status"], "queued")
        self.assertIsNotNone(m["scheduled_at"])
        self.assertIn("🤖 Поставил сам", calls[-1][1]["text"])


class TestGuessChannel(unittest.TestCase):
    def test_routes_by_meaning(self):
        cfg = {**CFG, "auto_channels": ["davra", "paparazzi", "xojaobod"]}
        self.assertEqual(smart.guess_channel(cfg, "Хўжаобод туманида янги йўл очилди"), "xojaobod")
        self.assertEqual(smart.guess_channel(cfg, "Юлдуз хонанданинг янги клипи премьераси"), "paparazzi")
        self.assertEqual(smart.guess_channel(cfg, "Валюта курси ўзгарди"), "davra")
        self.assertEqual(smart.guess_channel(cfg, "Ҳар қандай", has_audio=True), "paparazzi")
        self.assertEqual(smart.guess_channel({**CFG, "auto_channels": ["davra"]}, "Янги клип премьераси"), "davra")


class TestMultiBot(unittest.TestCase):
    def setUp(self):
        from genplan import bots
        self.bots = bots
        self.main, self.pap = [], []
        mk = lambda log: (lambda m, **p: log.append((m, p)) or {"message_id": len(log) + 100})
        self.cfg = {**CFG, "auto_place": True, "auto_channels": ["davra"],
                    "channels": {**CFG["channels"], "paparazzi": {**CFG["channels"]["paparazzi"], "bot_token_env": "PAP_TOK"}}}
        toks = iter([self.main, self.pap])
        bots.setup(self.cfg, {"GENPLAN_BOT_TOKEN": "m", "PAP_TOK": "p"}, lambda tok: mk(next(toks)))
        self.db = store.connect(":memory:")
        self.env = {**ENV, "HUB_CHAT_ID": "-100777", "OWNER_IDS": "42"}

    def tearDown(self):
        self.bots.REG.clear(); self.bots.TOKENS.clear()

    def test_post_into_channel_bot_goes_to_that_channel(self):
        b = self.bots.REG["paparazzi"]
        msg = {"message_id": 7, "from": {"id": 42}, "chat": {"id": 42, "type": "private"}, "text": "Янгилик: валюта курси ўзгарди"}
        hub.handle(b, self.db, self.cfg, self.env, {"message": msg})
        m = self.db.execute("SELECT * FROM materials").fetchone()
        self.assertEqual((m["channel"], m["via"]), ("paparazzi", "paparazzi"))   # не угадывание — бот канала решает
        self.assertTrue(self.pap and not self.main)                               # ответил бот-пульт канала

    def test_hub_post_taken_only_by_main_bot(self):
        post = {"message_id": 9, "chat": {"id": -100777}, "text": "Хабдаги пост"}
        self.assertIsNone(hub.handle(self.bots.REG["paparazzi"], self.db, self.cfg, self.env, {"channel_post": post}))
        self.assertEqual(self.db.execute("SELECT count(*) FROM materials").fetchone()[0], 0)

    def test_publisher_choice(self):
        pubs = {"bot": "MAIN", "bot:paparazzi": "PAP", "account": "ACC"}
        ch = self.cfg["channels"]["paparazzi"]
        self.assertEqual(service.pub_for(pubs, ch, "paparazzi", via="paparazzi", from_hub=False), "PAP")  # из чата пульта
        self.assertEqual(service.pub_for(pubs, ch, "paparazzi", via="paparazzi", from_hub=True), "MAIN")  # из хаба
        self.assertEqual(service.pub_for(pubs, ch, "paparazzi", via="main", from_hub=False), "MAIN")
        self.assertEqual(service.pub_for(pubs, self.cfg["channels"]["xojaobod"], "xojaobod"), "ACC")


class TestNoHub(Base):
    def test_move_to_group_copies_into_hub(self):
        self.h(dm(80, "Хўжаобод янгилиги", photo_uid="h1"))
        m = store.get(self.db, 1)
        self.assertEqual(m["hub_chat"], 42)                                    # лежит в чате с ботом
        self.tap("ch:1:" + hub.REV["xojaobod"], at("09:00"))
        m = store.get(self.db, 1)
        self.assertEqual(m["hub_chat"], 42)                                    # 21.10: и для группы — без копии в хаб
        self.assertEqual(m["channel"], "xojaobod")


class TestPanel(Base):
    """Панель пульта как в GENPLAN 5: ➕ ПОСТ / 🚨 СРОЧНО / 📅 СЕГОДНЯ / 📣 РЕКЛАМА / 📁 КОНТЕНТ / ⚙️ НАСТРОЙКИ."""

    def test_every_button_answers_about_own_channel(self):
        now = at("09:00")
        for b in menu.PANEL_BUTTONS:
            for chan in ("davra", "paparazzi"):
                ans = menu.panel_reply(self.db, CFG, chan, b, now)
                self.assertTrue(ans, (b, chan))
                if b != menu.P_TODAY:
                    self.assertIn(CFG["channels"][chan]["title"], ans)

    def test_button_is_command_not_post(self):
        self.assertEqual(self.h(dm(70, menu.P_CONTENT)), "panel:" + menu.P_CONTENT)
        self.assertEqual(self.db.execute("SELECT count(*) FROM materials").fetchone()[0], 0)

    def test_urgent_button_never_publishes_blind(self):
        # 17.10 владелец: брошенный пост ВСЕГДА с карточкой выбора; срочно — только кнопкой на карточке
        self.h(dm(71, menu.P_URGENT))
        self.assertEqual(self.h(dm(72, "Шошилинч янгилик", photo_uid="u1")), "material")
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], m["urgent"]), ("draft", 0))

    def test_ad_gets_rubric_and_tag(self):
        self.h(dm(74, menu.P_ADS))
        self.assertEqual(self.h(dm(75, "Скидка 50%! Тел +998901234567", photo_uid="a1")), "ad")
        self.assertEqual(store.get(self.db, 1)["rubric"], "Реклама")


class TestAdButton(Base):
    """21.10 владелец: «📣 Реклама» прямо на карточке (только Хўжаобод); альбом после 📣 РЕКЛАМА — тоже реклама."""

    def flat(self, kb):
        return [b for row in kb["inline_keyboard"] for b in row]

    def test_card_has_ad_button_only_where_ads(self):
        self.h(dm(90, "Скидка! Тел +998901234567", photo_uid="z1"))
        now = at("09:00")
        store.update(self.db, 1, channel="xojaobod")
        _, kb = hub.card(self.db, CFG, 1, now)
        self.assertIn("📣 Реклама", [b["text"] for b in self.flat(kb)])
        store.update(self.db, 1, channel="davra")
        _, kb = hub.card(self.db, CFG, 1, now)
        self.assertNotIn("📣 Реклама", [b["text"] for b in self.flat(kb)])

    def test_ad_button_then_ad_window(self):
        self.h(dm(91, "Скидка! Тел +998901234567", photo_uid="z2"))
        store.update(self.db, 1, channel="xojaobod")
        now = at("09:00")
        self.tap("ad:1", now)
        self.assertEqual(store.get(self.db, 1)["rubric"], "Реклама")
        c = self.last_card()
        self.assertIn("📣 Реклама — когда выпустить?", c["text"])
        btns = self.flat(c["reply_markup"])
        self.assertEqual([b["text"] for b in btns][1:], ["🕐 Другое время", "✍️ Своё время", "⬅️ Отмена"])
        self.assertEqual(btns[0]["text"], "🧠 Умное время · 09:40")          # ближайшее рекламное окно
        self.tap(btns[0]["callback_data"], now)
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], m["rubric"], dt.datetime.fromisoformat(m["scheduled_at"])), ("queued", "Реклама", at("09:40")))

    def test_other_time_list(self):
        self.h(dm(95, "Скидка!", photo_uid="z5"))
        store.update(self.db, 1, channel="xojaobod")
        now = at("09:00")
        self.tap("ad:1", now); self.tap("ao:1", now)
        btns = self.flat(self.last_card()["reply_markup"])
        self.assertTrue(btns[0]["text"].startswith("📣 "))
        self.assertEqual(btns[-1]["callback_data"], "ad:1")

    def test_own_time(self):
        self.h(dm(96, "Скидка!", photo_uid="z6"))
        store.update(self.db, 1, channel="xojaobod")
        now = at("09:00")
        self.tap("ad:1", now); self.tap("aw:1", now)
        self.assertEqual(hub.own_time(self.bot, self.db, CFG, 1, "25:99", 42, now), "own_time_bad")
        self.assertEqual(hub.own_time(self.bot, self.db, CFG, 1, "завтра 18:25", 42, now), "own_time")
        m = store.get(self.db, 1)
        self.assertEqual((m["status"], m["locked"]), ("queued", 1))
        self.assertEqual(dt.datetime.fromisoformat(m["scheduled_at"]), at("18:25", MON + dt.timedelta(days=1)))

    def test_parse_when(self):
        now = at("09:00")
        self.assertEqual(hub.parse_when("18 25", now), at("18:25"))
        self.assertEqual(hub.parse_when("Эртага 7.30", now), at("07:30", MON + dt.timedelta(days=1)))
        self.assertEqual(hub.parse_when("23.10 18:25", now), at("18:25", dt.date(2026, 10, 23)))
        self.assertIsNone(hub.parse_when("скоро", now))

    def test_album_after_panel_ads(self):
        self.h(dm(92, menu.P_ADS))
        self.assertEqual(self.h(dm(93, "Скидка!", photo_uid="z3", gid="g1")), "album")
        self.h(dm(94, "", photo_uid="z4", gid="g1"))
        hub.flush_albums(self.bot, self.db, CFG, ENV, now_ts=10**12)
        self.assertEqual(store.get(self.db, 1)["rubric"], "Реклама")


class TestAutopilotButton(Base):
    def test_owner_allows_once(self):
        q = cb("ap:abc123def:y")["callback_query"]
        q["message"]["text"] = "🤖 Автопилот просит разрешения"
        self.assertEqual(hub.callback(self.bot, self.db, CFG, {42}, q), "ap_y")
        self.assertEqual(store.kv_get(self.db, "autopilot_abc123def"), "yes")
        self.assertEqual(hub.callback(self.bot, self.db, CFG, {42}, q), "dup")      # второй раз не меняет

    def test_stranger_denied(self):
        q = cb("ap:abc123def:y", uid=7)["callback_query"]
        self.assertEqual(hub.callback(self.bot, self.db, CFG, {42}, q), "denied")
        self.assertIsNone(store.kv_get(self.db, "autopilot_abc123def"))


class TestCurator(Base):
    def fwd(self, mid, text, uname):
        u = dm(mid, text, photo_uid=f"c{mid}")
        u["message"]["forward_origin"] = {"type": "channel", "chat": {"id": -100555, "title": "Src", "username": uname}}
        return u

    def test_source_saved_and_shown(self):
        self.h(self.fwd(90, "Қизиқ янгилик", "daryo_uz"))
        self.assertEqual(store.get(self.db, 1)["source"], "@daryo_uz")
        self.assertIn("📡 Куратор нашёл · @daryo_uz", self.last_card()["text"])

    def test_evening_report(self):
        self.h(self.fwd(91, "Биринчи", "a_src"))
        self.h(self.fwd(92, "Иккинчи", "b_src"))
        store.update(self.db, 1, status="queued")
        day = dt.date.fromisoformat(store.get(self.db, 1)["created_at"][:10])
        rep = service.curator_report(self.db, CFG, plan.slot_time(day, "21:40"))
        self.assertIn("найдено 2, взято 1", rep)
        self.assertIn("@a_src 1/1", rep)
        self.assertIsNone(service.curator_report(self.db, CFG, plan.slot_time(day, "21:50")))   # раз в день


class TestChannelPolicy(unittest.TestCase):
    """Политика каналов (docs/CHANNELS.md): предупреждение, не перенос."""
    import tomllib as _t
    REAL = _t.load(open(Path(__file__).resolve().parents[1] / "config.toml", "rb"))

    def test_main_bot_keeps_davra(self):
        self.assertEqual(smart.guess_channel(self.REAL, "Юлдуз хонанданинг янги клипи премьераси"), "davra")
        self.assertEqual(smart.guess_channel(self.REAL, "Ҳар қандай", has_audio=True), "davra")

    def test_davra_warnings(self):
        n = smart.policy_note(self.REAL, "davra", "Президент парламентда нутқ сўзлади")
        self.assertIn("политика", n)
        self.assertIn("Хўжаобод", n)
        n = smart.policy_note(self.REAL, "davra", "Xonanda yangi klip premyerasini taqdim etdi")   # латиница
        self.assertIn("PaparazziUZ", n)
        self.assertEqual(smart.policy_note(self.REAL, "davra", "Уйда тез тайёрланадиган фойдали таом рецепти"), "")
        self.assertEqual(smart.policy_note(self.REAL, "davra", "OpenAI янги сунъий интеллект моделини чиқарди"), "")

    def test_paparazzi_and_xojaobod(self):
        self.assertEqual(smart.policy_note(self.REAL, "paparazzi", "Хонанданинг янги клипи"), "")
        self.assertIn("политика", smart.policy_note(self.REAL, "paparazzi", "Депутатлар сайлови бўлиб ўтди"))
        self.assertEqual(smart.policy_note(self.REAL, "xojaobod", "Президент парламентда нутқ сўзлади"), "")


def hub_post(mid, title, chat=-100555, text="Янги клип чиқди! Тинглаб кўринг", gid=None):
    p = {"message_id": mid, "chat": {"id": chat, "type": "channel", "title": title}, "date": 1,
         "caption": text, "photo": [{"file_id": f"f{mid}", "file_unique_id": f"u{mid}"}]}
    if gid:
        p["media_group_id"] = gid
    return {"channel_post": p}


class TestChannelHub(Base):
    """18.10: свой ХАБ у каждого канала — пост оттуда сразу в 📦 запас своего канала, через своего бота."""

    def test_davra_hub_goes_to_stock(self):
        self.assertEqual(self.h(hub_post(7, "КАТТА ДАВРА · ХАБ")), "material")
        m = store.get(self.db, 1)
        self.assertEqual((m["channel"], m["stock"], m["status"], m["hub_chat"]), ("davra", 1, "draft", -100555))
        self.assertIn("Из ХАБа", self.last_card()["text"])
        self.assertEqual(store.kv_get(self.db, "hub_davra"), "-100555")
        # дальше узнаём по id, даже если хаб переименовали
        self.assertEqual(self.h(hub_post(8, "Другое имя", text="Бошқа янги клип")), "material")

    def test_foreign_hub_ignored_by_main_bot(self):
        self.assertIsNone(self.h(hub_post(7, "PAPARAZZI · ХАБ", chat=-100666)))   # чужой хаб — не мой сектор
        self.assertEqual(self.db.execute("SELECT count(*) FROM materials").fetchone()[0], 0)

    def test_paparazzi_bot_takes_its_hub(self):
        from genplan import bots
        pb = FakeBot()
        bots.REG.clear(); bots.REG.update({"main": self.bot, "paparazzi": pb})
        self.addCleanup(bots.REG.clear)
        r = hub.handle(pb, self.db, CFG, ENV, hub_post(9, "PAPARAZZI · ХАБ", chat=-100666))
        self.assertEqual(r, "material")
        m = store.get(self.db, 1)
        self.assertEqual((m["channel"], m["stock"], m["via"]), ("paparazzi", 1, "paparazzi"))
        self.assertEqual(self.bot.calls, [])                                   # главный бот молчит
        self.assertIsNone(hub.handle(pb, self.db, CFG, ENV, hub_post(10, "КАТТА ДАВРА · ХАБ")))

    def test_xojaobod_bot_takes_its_hub_and_copies_to_papa_hub(self):
        # 20.10 владелец: каждый бот — своё; аккаунт PAPA в ХАБ группы не добавляем — бот группы сам кладёт копию в PAPA HUB
        from genplan import bots
        xb = FakeBot()
        bots.REG.clear(); bots.REG.update({"main": self.bot, "xojaobod": xb})
        self.addCleanup(bots.REG.clear)
        r = hub.handle(xb, self.db, CFG, ENV, hub_post(9, "ХЎЖАОБОД · ХАБ", chat=-100888, text="Хўжаободда янги боғ очилди"))
        self.assertEqual(r, "material")
        m = store.get(self.db, 1)
        # 21.10 владелец: PAPA HUB — не свалка. Материал остаётся в ХАБе группы, в PAPA HUB при броске ничего не кладём
        self.assertEqual((m["channel"], m["stock"], str(m["hub_chat"])), ("xojaobod", 1, "-100888"))
        self.assertFalse(any(c[0] in ("copyMessage", "copyMessages") for c in xb.calls))
        self.assertEqual(self.bot.calls, [])                                   # главный бот молчит
        # секундная копия в PAPA HUB во время публикации — не новый материал для главного бота
        store.kv_set(self.db, "hub_staging", "1")
        self.assertIsNone(self.h({"channel_post": {"message_id": 555, "chat": {"id": int(ENV["HUB_CHAT_ID"]), "type": "channel"},
                                                   "date": 1, "caption": "Хўжаободда янги боғ очилди", "photo": [{"file_id": "z", "file_unique_id": "z"}]}}))
        self.assertEqual(self.db.execute("SELECT count(*) FROM materials").fetchone()[0], 1)

    def test_main_bot_takes_only_davra_hub(self):
        # 20.10 владелец: каждый бот — своё. Главный бот (пульт Давры) ХАБ Хўжаобода НЕ берёт
        self.assertEqual(self.h(hub_post(7, "КАТТА ДАВРА · ХАБ")), "material")
        self.assertIsNone(self.h(hub_post(8, "ХЎЖАОБОД · ХАБ", chat=-100888, text="Хўжаободда янги боғ очилди")))
        self.assertIsNone(self.h(hub_post(9, "XЎЖAОБОД · XАБ", chat=-100889, text="Хўжаободда янги боғ")))
        self.assertEqual(store.get(self.db, 1)["channel"], "davra")
        self.assertIsNone(store.get(self.db, 2))

    def test_hub_album_one_material(self):
        self.assertEqual(self.h(hub_post(11, "КАТТА ДАВРА · ХАБ", gid="g1")), "album")
        self.assertEqual(self.h(hub_post(12, "КАТТА ДАВРА · ХАБ", text="", gid="g1")), "album")
        hub.flush_albums(self.bot, self.db, CFG, ENV, now_ts=10 ** 10)
        m = store.get(self.db, 1)
        self.assertEqual((m["channel"], m["stock"], json.loads(m["hub_msgs"])), ("davra", 1, [11, 12]))

    def test_stock_from_hub_fills_slot(self):
        self.h(hub_post(7, "КАТТА ДАВРА · ХАБ"))
        m = store.get(self.db, 1)
        now = at("08:00")
        ids = []
        for h in range(8, 23):
            ids += smart.fill_from_stock(self.db, CFG, "davra", plan.slot_time(now.date(), f"{h:02d}:00"))
            if ids:
                break
        self.assertEqual(ids, [1])
        self.assertEqual(store.get(self.db, 1)["status"], "queued")
        self.assertTrue(m["rubric"])


class TestPapaHubClean(Base):
    """21.10 владелец: PAPA HUB — не свалка. Пост группы попадает туда только на секунды публикации."""

    class Http:
        def __init__(self):
            self.calls = []

        def http(self, method, p):
            self.calls.append((method, p))
            if method == "copyMessage":
                return {"ok": True, "result": {"message_id": 7001}}
            return {"ok": True, "result": True}

    class Acc:
        def __init__(self):
            self.sent = []

        async def publish(self, to, body, hub_chat, hub_msg, media):
            self.sent.append((hub_chat, hub_msg, media))
            return 1

    def test_group_post_staged_then_deleted(self):
        self.h(dm(70, "Хўжаободда янги боғ очилди", photo_uid="k1"))
        store.update(self.db, 1, channel="xojaobod", via="xojaobod", status="queued",
                     scheduled_at=at("09:00").isoformat(), rubric="Янгилик")
        xb, acc = self.Http(), self.Acc()
        pubs = {"account": acc, "bot": self.Http(), "bot:xojaobod": xb}
        ok = asyncio.run(service.publish_one(self.db, CFG, ENV, pubs, "xojaobod", store.get(self.db, 1), "09:00",
                                             MON.isoformat(), log=lambda *_: None, now=at("09:00")))
        self.assertTrue(ok)
        self.assertEqual(acc.sent, [(-100777, 7001, True)])                     # аккаунт взял секундную копию
        self.assertEqual(xb.calls[0][0], "copyMessage")
        self.assertEqual(xb.calls[0][1]["from_chat_id"], 42)                     # из чата пульта
        self.assertIn(("deleteMessages", {"chat_id": -100777, "message_ids": [7001]}), xb.calls)   # и сразу убрал
        self.assertEqual(store.kv_get(self.db, "hub_staging", ""), "")

    def test_drop_card_needs_approve(self):
        self.h(dm(71, "Ажойиб видео", photo_uid="k2"))
        now = at("08:00")
        st = smart.smart_time(self.db, CFG, "davra", store.get(self.db, 1)["rubric"], now, exclude=1)
        data = f"sm:1:{int(st[0].timestamp())}"
        self.assertEqual(self.tap(data, now, confirm=False), "confirm")
        self.assertEqual(store.get(self.db, 1)["status"], "draft")              # без «✅ Утверждаю» не встаёт в план
        kb = self.last_card()["reply_markup"]["inline_keyboard"]
        self.assertEqual(kb[0][0], {"text": "✅ Утверждаю", "callback_data": "ok:" + data})
        self.assertIn("Утверждаете?", self.last_card()["text"])
        self.tap("ok:" + data, now, confirm=False)
        self.assertEqual(store.get(self.db, 1)["status"], "queued")
        self.assertIn("✅ Принято", self.last_card()["text"])                    # итог остаётся в карточке
        self.assertEqual(self.bot.calls[-1], ("answerCallbackQuery", {"callback_query_id": "q"}))   # без всплывашки


    def test_hub_clean_once(self):
        # старые служебные копии: одна нужна (пост в плане), одна — Якуний, одна — мусор после публикации
        for x in (501, 502, 503):
            store.kv_set(self.db, f"hubcopy_{x}", "1")
        a = store.add_material(self.db, -100777, 501, "План", True)
        store.update(self.db, a, channel="xojaobod", status="queued", via="xojaobod", scheduled_at=at("20:00").isoformat())
        store.kv_set(self.db, "final_xojaobod", json.dumps({"material_id": 99, "text": "Муфтий", "hub_chat": -100777,
                                                             "hub_msg": 502, "hub_msgs": [], "has_media": True}))
        xb = self.Http()
        n = iter(range(8001, 8100))
        xb.http = lambda m, p, c=xb.calls: (c.append((m, p)), {"ok": True, "result": {"message_id": next(n)}}
                                            if m == "copyMessage" else {"ok": True, "result": True})[1]
        out = service.hub_clean_once(self.db, CFG, ENV, {"bot": self.Http(), "bot:xojaobod": xb}, log=lambda *_: None)
        self.assertEqual((out["moved"], out["deleted"], out["errors"]), (2, 3, 0))
        m = store.get(self.db, a)
        self.assertEqual((m["hub_chat"], m["hub_msg"]), (42, 8001))               # теперь хранится в чате пульта
        f = json.loads(store.kv_get(self.db, "final_xojaobod"))
        self.assertEqual((f["hub_chat"], f["hub_msg"], f["via"]), (42, 8002, "xojaobod"))
        dels = [p["message_ids"] for mm, p in xb.calls if mm == "deleteMessages"]
        self.assertEqual(dels, [[501, 502, 503]])
        self.assertEqual(service.hub_clean_once(self.db, CFG, ENV, {"bot:xojaobod": xb}), {"moved": 0, "deleted": 0, "errors": 0})
