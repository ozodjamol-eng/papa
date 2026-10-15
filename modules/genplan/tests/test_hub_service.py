import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import json  # noqa: E402
from genplan import hub, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
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
        self.assertEqual(self.bot.calls[0][0], "copyMessage")                 # копия — в хаб
        m = store.get(self.db, 1)
        self.assertEqual((m["channel"], m["rubric"], m["status"]), ("davra", "Мусиқа", "draft"))   # канал и рубрика — сами
        now = at("08:00")
        txt, kb = hub.card(self.db, CFG, 1, now)
        self.assertIn("🧠 УМНОЕ ВРЕМЯ: сегодня 13:30", txt)                  # музыка — не раньше 10:00, слот «Мусиқа»
        first = kb["inline_keyboard"][0][0]
        self.assertTrue(first["text"].startswith("🧠 Умное время · 13:30"))
        self.tap(first["callback_data"], now)
        m = store.get(self.db, 1)
        self.assertEqual(m["status"], "queued")
        self.assertEqual(dt.datetime.fromisoformat(m["scheduled_at"]), at("13:30"))
        self.assertIn("✅", self.last_card()["text"])

    def test_gap_and_next_slot(self):
        now = at("08:00")
        for i, mid in ((1, 20), (2, 21)):
            self.h(dm(mid, f"Янги клип {i} чиқди, қўшиқ зўр", photo_uid=f"g{i}"))
            st = smart.smart_time(self.db, CFG, "davra", "Мусиқа", now, exclude=i)
            self.tap(f"sm:{i}:{int(st[0].timestamp())}", now)
        t = [dt.datetime.fromisoformat(store.get(self.db, i)["scheduled_at"]) for i in (1, 2)]
        self.assertEqual(t, [at("13:30"), at("19:30")])                       # второй — в следующий слот рубрики

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
        self.assertEqual(st[0], at("12:00", MON + dt.timedelta(days=1)))      # хороший пост — на завтра, не пропадает

    def test_window_and_other_times(self):
        ts = smart.other_times(self.db, CFG, "davra", "Видео", at("21:59"), n=3)
        self.assertTrue(all(dt.time(7, 0) <= t.time() <= dt.time(22, 0) for t in ts))
        self.assertEqual(ts[0], at("07:00", MON + dt.timedelta(days=1)))

    def test_duplicate_warning(self):
        self.h(dm(50, "Пост", photo_uid="same"))
        self.tap(f"ur:1", at("12:00"))
        self.h(dm(51, "Пост ещё раз", photo_uid="same"))
        txt, _ = hub.card(self.db, CFG, 2, at("12:05"))
        self.assertIn("⚠️ Повтор", txt)

    def test_album_one_material(self):
        self.assertEqual(self.h(dm(60, "Альбом", photo_uid="a1", gid="G")), "album")
        self.assertEqual(self.h(dm(61, "", photo_uid="a2", gid="G")), "album")
        bot = lambda m, **p: (self.bot.calls.append((m, p)) or ([{"message_id": 700}, {"message_id": 701}] if m == "copyMessages" else {"message_id": 800}))
        self.assertEqual(hub.flush_albums(bot, self.db, CFG, ENV, now_ts=10**10), 1)
        m = store.get(self.db, 1)
        self.assertEqual(json.loads(m["hub_msgs"]), [700, 701])
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
        self.assertTrue(body.split("\n\n")[-1].startswith("🎉 @kattadavrauz"))   # текст → @юзернейм → призыв
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
        self.assertEqual(service.target(CFG, ENV, "paparazzi"), -100222)
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
        self.assertIn("Умное время", menu.reply(db, CFG, "/start"))
        self.assertIsNone(menu.reply(db, CFG, "просто текст"))
        self.assertFalse(menu.KEYBOARD["is_persistent"])




if __name__ == "__main__":
    unittest.main()
