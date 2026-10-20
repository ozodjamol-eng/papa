import asyncio
import datetime as dt
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import hub, namaz, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
CFG["channels"]["xojaobod"].pop("mode", None)   # 20.10 группа в работе; эти тесты проверяют режим теста
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222"}
THU, FRI = dt.date(2026, 10, 15), dt.date(2026, 10, 16)
BLOCK = "Намоз вақтлари: 15.10.2026\nБомдод 05:45\nПешин 12:45\nАср 16:00\nШом 17:45\nХуфтон 19 10"


def at(hm, d=THU):
    return plan.slot_time(d, hm)


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, m, **p):
        self.calls.append((m, p)); return {"message_id": len(self.calls)}


class Acc:
    def __init__(self):
        self.sent = []

    async def publish(self, chat, body, hub_chat, hub_msg, has_media):
        self.sent.append((chat, body)); return 9


class TestNamaz(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")

    def test_parse_any_separator_and_errors(self):
        (d, t), = namaz.parse(BLOCK, THU)
        self.assertEqual((d, t["xufton"], t["bomdod"]), (THU, "19:10", "05:45"))     # «19 10» принято, дата — только для показа
        for bad, why in (("Бомдод 05:45\nПешин 12:45\nАср 16:00\nШом 17:45", "Хуфтон"),
                         ("Бомдод 05:45\nПешин 12:45\nАср 16:00\nШом 17:45\nХуфтон 25:10", "неверное"),
                         ("Бомдод 15:45\nПешин 12:45\nАср 16:00\nШом 17:45\nХуфтон 19:10", "порядку")):
            with self.assertRaises(ValueError) as e:
                namaz.parse(bad, THU)
            self.assertIn(why, str(e.exception))

    def test_week_input(self):
        items = namaz.parse("16.10\nБомдод 0546\nПешин 12.45\nАср 15:59\nШом 17-44\nХуфтон 19:09\n"
                            "📅 17.10 Шанба\nБомдод 05:47\nПешин 12:44\nАср 15:58\nШом 17:43\nХуфтон 19:08", THU)
        self.assertEqual([d for d, _ in items], [FRI, dt.date(2026, 10, 17)])

    def test_posts_like_genplan5(self):
        namaz.save(self.db, namaz.parse(BLOCK, THU), at("04:00"))
        namaz.ensure_day(self.db, CFG, "xojaobod", THU, at("04:00"))
        rows = {r["key"]: r for r in self.db.execute("SELECT * FROM namaz_posts")}
        self.assertEqual(rows["table"]["at"], at("05:15").isoformat())             # за 30 мин до Бомдода
        self.assertEqual(rows["alert_xufton"]["at"], at("19:00").isoformat())      # за 10 мин
        self.assertIn("Хуфтон намозига 10 дақиқа қолди (19:10)", rows["alert_xufton"]["text"])
        self.assertIn("@XOJAOBODCITY24", rows["table"]["text"])
        self.assertNotIn("juma", rows)                                             # четверг
        self.assertEqual(namaz.ensure_day(self.db, CFG, "xojaobod", THU, at("04:00")), 0)   # повтор — ничего нового
        self.assertEqual(namaz.ensure_day(self.db, CFG, "davra", THU, at("04:00")), 0)      # у Давры намаза нет

    def test_friday_juma_and_quiet_lock(self):
        namaz.save(self.db, namaz.parse(BLOCK, FRI), at("04:00", FRI))
        namaz.ensure_day(self.db, CFG, "xojaobod", FRI, at("04:00", FRI))
        juma = self.db.execute("SELECT at FROM namaz_posts WHERE key='juma'").fetchone()[0]
        self.assertEqual(juma, at("12:00", FRI).isoformat())                       # за 45 мин до Пешина
        self.assertTrue(smart.blocked(self.db, "xojaobod", at("12:40", FRI)))     # тихое окно
        self.assertFalse(smart.blocked(self.db, "xojaobod", at("13:30", FRI)))
        ts = smart.other_times(self.db, CFG, "xojaobod", "Видео", at("12:20", FRI), n=3)
        self.assertTrue(all(not (at("12:25", FRI) <= t <= at("13:20", FRI)) for t in ts))

    def test_late_not_published(self):
        namaz.save(self.db, namaz.parse(BLOCK, THU), at("04:00"))
        namaz.ensure_day(self.db, CFG, "xojaobod", THU, at("16:30"))              # сервер стартовал в 16:30
        st = {r["key"]: r["status"] for r in self.db.execute("SELECT key, status FROM namaz_posts")}
        self.assertEqual((st["table"], st["alert_asr"], st["alert_shom"]), ("skipped", "skipped", "pending"))

    def test_tick_publishes_to_test_group(self):
        namaz.save(self.db, namaz.parse(BLOCK, THU), at("04:00"))
        acc = Acc()
        pubs = {"account": acc, "bot": None}
        r = asyncio.run(service.tick(self.db, CFG, ENV, pubs, at("17:35"), lambda *_: None))
        self.assertEqual(r["namaz"], 1)
        self.assertEqual(acc.sent[0][0], -100111)                                  # Хўжаобод в тесте → тестовая группа
        self.assertIn("Шом намозига", acc.sent[0][1])
        asyncio.run(service.tick(self.db, CFG, ENV, pubs, at("17:36"), lambda *_: None))
        self.assertEqual(len(acc.sent), 1)                                         # один раз

    def test_content_avoids_namaz_times(self):
        namaz.save(self.db, namaz.parse(BLOCK, THU), at("04:00"))
        namaz.ensure_day(self.db, CFG, "xojaobod", THU, at("04:00"))
        busy = smart.occupied(self.db, "xojaobod", at("17:00"))
        self.assertFalse(smart.is_free(CFG["channels"]["xojaobod"], at("17:40"), busy))   # рядом с напоминанием Шом

    def test_owner_message_saves_and_reminder(self):
        bot = Bot()
        u = {"message": {"message_id": 1, "from": {"id": 42}, "chat": {"id": 42, "type": "private"}, "text": BLOCK}}
        self.assertEqual(hub.handle(bot, self.db, CFG, ENV, u), "namaz")
        self.assertIn("✅ Намоз вақтлари сақланди", bot.calls[-1][1]["text"])
        self.assertIsNone(namaz.reminder(self.db, CFG, dt.datetime.now(plan.TZ).replace(hour=21)))   # свежее — не напоминает
        db2 = store.connect(":memory:")
        self.assertIn("киритилмаган", namaz.reminder(db2, CFG, at("20:30")))
        self.assertIsNone(namaz.reminder(db2, CFG, at("20:40")))                   # раз в день
        old = store.connect(":memory:")
        namaz.save(old, namaz.parse(BLOCK, dt.date(2026, 10, 1)), at("04:00"))
        self.assertIn("не обновлялось", namaz.reminder(old, CFG, at("20:30")))

    def test_long_post_mentioning_prayers_is_content(self):
        bot = Bot()
        txt = "Рамазон ойида бомдод, пешин ва аср намозлари ҳақида фойдали маълумот. Шом ва хуфтон ҳам муҳим."
        u = {"message": {"message_id": 2, "from": {"id": 42}, "chat": {"id": 42, "type": "private"}, "text": txt}}
        self.assertEqual(hub.handle(bot, self.db, CFG, ENV, u), "material")


if __name__ == "__main__":
    unittest.main()
