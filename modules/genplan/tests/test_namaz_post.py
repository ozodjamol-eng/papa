"""22.10 владелец: готовый пост намаза на неделю (баннер + текст) → карточка ✅/✏️/❌ → каждое утро как есть."""
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
from genplan import fabrika, hub, menu, namaz, plan, service, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
CFG["channels"]["xojaobod"].pop("mode", None)
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}
THU, FRI, SAT = dt.date(2026, 10, 22), dt.date(2026, 10, 23), dt.date(2026, 10, 24)
CAP = ("🕌 Намоз вақтлари\n23–29 октябр 2026 йил\n🕔 Бомдод — 05:55\n🕑 Пешин — 12:45\n🕒 Аср — 15:50\n"
       "🕔 Шом — 17:35\n🕖 Хуфтон — 19:00\n🤲 Аллоҳ ибодатларимизни қабул қилсин!\n@XOJAOBODCITY24")


def at(hm, d=THU):
    return plan.slot_time(d, hm)


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, m, **p):
        self.calls.append((m, p))
        return {"message_id": 500 + len(self.calls)}


class Acc:
    def __init__(self):
        self.sent, self.photos = [], []

    async def publish(self, chat, body, hub_chat, hub_msg, has_media):
        self.sent.append((chat, body)); return 9

    async def publish_photo(self, chat, path, caption=""):
        self.photos.append((chat, path, caption)); return 10


def fake_download(bot, env, file_id, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"jpg")


class TestNamazPost(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.tmp = tempfile.TemporaryDirectory()
        self.old_state, fabrika.STATE = fabrika.STATE, Path(self.tmp.name)
        self.old_now, hub._now = hub._now, (lambda: at("22:40"))

    def tearDown(self):
        fabrika.STATE, hub._now = self.old_state, self.old_now
        self.tmp.cleanup()

    def msg(self, cap=CAP, mid=77):
        return {"message_id": mid, "chat": {"id": 42}, "caption": cap, "photo": [{"file_id": "a"}, {"file_id": "big"}]}

    def cq(self, data, card):
        return {"id": "q", "from": {"id": 42}, "data": data, "message": {"chat": {"id": 42}, "message_id": card, "text": ""}}

    def draft(self, bot):
        r = hub.namaz_draft(bot, self.db, ENV, self.msg(), CAP, download=fake_download, cfg=CFG)
        self.assertEqual(r, "namaz_draft")
        return json.loads(store.kv_get(self.db, "namaz_draft"))

    def test_start_date_and_times_from_text(self):
        self.assertEqual(namaz.start_date(CAP, THU), FRI)                   # пост на неделю, брошенный в четверг, — с пятницы
        self.assertEqual(namaz.start_date(CAP, SAT), SAT)                   # дата прошла — с сегодняшнего дня
        self.assertEqual(namaz.start_date("Бомдод 05:55", THU), THU)
        self.assertEqual(namaz.start_date("23.10.2026 й", THU), FRI)
        day, t = namaz.parse_post(CAP, THU)
        self.assertEqual((day, t), (FRI, {"bomdod": "05:55", "peshin": "12:45", "asr": "15:50",
                                          "shom": "17:35", "xufton": "19:00"}))

    def test_card_has_three_buttons_and_nothing_changes_before_ok(self):
        bot = Bot()
        d = self.draft(bot)
        _, p = bot.calls[-1]
        labels = [b["text"] for row in p["reply_markup"]["inline_keyboard"] for b in row]
        self.assertEqual(labels, ["✅ Утверждаю", "✏️ Изменить", "❌ Отказ"])
        self.assertIn("05:25", p["text"])                                   # за 30 мин до Бомдода 05:55
        self.assertIsNone(namaz.schedule_for(self.db, FRI))                 # без ✅ ничего не сохранено
        self.assertTrue(Path(d["photo"]).exists())

    def test_ok_replaces_and_posts_exactly_as_is(self):
        bot = Bot()
        namaz.save(self.db, namaz.parse("Бомдод 05:45\nПешин 12:45\nАср 16:00\nШом 17:45\nХуфтон 19:10", THU), at("08:00"))
        d = self.draft(bot)
        self.assertEqual(hub.namaz_callback(bot, self.db, CFG, self.cq("nz:ok", d["card"])), "namaz_ok")
        self.assertIn("✅ Принято", bot.calls[-1][1]["text"])
        self.assertEqual(namaz.schedule_for(self.db, THU)["bomdod"], "05:45")   # сегодня — по-старому
        s = namaz.schedule_for(self.db, SAT)
        self.assertEqual((s["day"], s["bomdod"], s["caption"]), (FRI.isoformat(), "05:55", CAP))
        namaz.ensure_day(self.db, CFG, "xojaobod", SAT, at("22:40"))
        rows = {r["key"]: r for r in self.db.execute("SELECT * FROM namaz_posts WHERE day=?", (SAT.isoformat(),))}
        self.assertEqual(rows["table"]["text"], CAP)                         # никаких лишних слов
        self.assertEqual(rows["table"]["at"], at("05:25", SAT).isoformat())
        self.assertTrue(Path(rows["table"]["photo"]).exists())
        self.assertEqual(rows["alert_bomdod"]["at"], at("05:45", SAT).isoformat())   # напоминание за 10 мин
        self.assertIsNone(rows["alert_bomdod"]["photo"])

    def test_tick_publishes_banner_photo(self):
        bot = Bot()
        d = self.draft(bot)
        hub.namaz_callback(bot, self.db, CFG, self.cq("nz:ok", d["card"]))
        acc = Acc()
        r = asyncio.run(service.tick(self.db, CFG, ENV, {"account": acc, "bot": None}, at("05:25", SAT), lambda *_: None))
        self.assertEqual(r["namaz"], 1)
        chat, path, caption = acc.photos[0]
        self.assertEqual((chat, caption), (-100111, CAP))
        self.assertEqual(acc.sent, [])

    def test_edit_waits_for_new_post_and_cancel(self):
        bot = Bot()
        d = self.draft(bot)
        self.assertEqual(hub.namaz_callback(bot, self.db, CFG, self.cq("nz:ed", d["card"])), "namaz_edit")
        self.assertTrue(hub.namaz_waiting(self.db))
        cap2 = CAP.replace("05:55", "05:50")
        hub.namaz_draft(bot, self.db, ENV, self.msg(cap2, 78), cap2, download=fake_download, cfg=CFG)
        d2 = json.loads(store.kv_get(self.db, "namaz_draft"))
        self.assertEqual(d2["times"]["bomdod"], "05:50")
        self.assertFalse(Path(d["photo"]).exists())                         # картинка прежнего черновика убрана
        self.assertEqual(hub.namaz_callback(bot, self.db, CFG, self.cq("nz:ok", d["card"])), "namaz_stale")   # старая карточка
        self.assertEqual(hub.namaz_callback(bot, self.db, CFG, self.cq("nz:no", d2["card"])), "namaz_no")
        self.assertIsNone(namaz.schedule_for(self.db, SAT))
        self.assertFalse(Path(d2["photo"]).exists())

    def test_ordinary_photo_post_not_taken(self):
        cap = "Бугун бозорда янги маҳсулотлар! Бомдоддан кейин очилади."
        self.assertEqual(hub.namaz_draft(Bot(), self.db, ENV, self.msg(cap), cap, download=fake_download, cfg=CFG), "not_namaz")

    def test_text_schedule_drops_banner(self):
        bot = Bot()
        d = self.draft(bot)
        hub.namaz_callback(bot, self.db, CFG, self.cq("nz:ok", d["card"]))
        namaz.save(self.db, [(FRI, {"bomdod": "05:56", "peshin": "12:45", "asr": "15:50", "shom": "17:35", "xufton": "19:00"})],
                   at("23:00"))
        self.assertIsNone(namaz.schedule_for(self.db, FRI)["photo"])

    def test_settings_button(self):
        kb = menu.panel_markup(CFG, "xojaobod", menu.P_SETTINGS)
        self.assertEqual(kb["inline_keyboard"][0][0]["callback_data"], "nz:set")
        self.assertIs(menu.panel_markup(CFG, "xojaobod", menu.P_TODAY), menu.PANEL)
        self.assertIn("Намоз:", menu.panel_reply(self.db, CFG, "xojaobod", menu.P_SETTINGS, at("22:40")))


if __name__ == "__main__":
    unittest.main()
