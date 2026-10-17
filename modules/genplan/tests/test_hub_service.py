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

    def tap(self, data, now):
        return hub.callback(self.bot, self.db, CFG, {42}, cb(data)["callback_query"], now)

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
        self.assertEqual(self.bot.calls[-1][1].get("text"), "Это время уже занято — показываю новое")

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
        self.assertEqual(str(m["hub_chat"]), ENV["HUB_CHAT_ID"])               # для группы — скопирован в хаб
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
