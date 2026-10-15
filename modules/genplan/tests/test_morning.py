import asyncio
import datetime as dt
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from genplan import ai, hub, morning, namaz, plan, service, smart, store  # noqa: E402

CFG = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
ENV = {"OWNER_IDS": "42", "HUB_CHAT_ID": "-100777", "TEST_GROUP_ID": "-100111", "TEST_CHANNEL_ID": "-100222",
       "GENPLAN_BOT_TOKEN": "t", "PIXABAY_API_KEY": "k"}
THU, FRI = dt.date(2026, 10, 15), dt.date(2026, 10, 16)


def at(hm, d=THU):
    return plan.slot_time(d, hm)


class Bot:
    def __init__(self):
        self.calls = []

    def __call__(self, m, **p):
        self.calls.append((m, p)); return {"message_id": len(self.calls)}


class Pub:
    def __init__(self):
        self.sent = []

    def publish(self, chat, text, hub_chat=None, hub_msg=None, has_media=False, button=None):
        self.sent.append((chat, text, hub_msg)); return 77


class Acc:
    def __init__(self):
        self.sent = []

    async def publish(self, chat, text, hub_chat=None, hub_msg=None, has_media=False):
        self.sent.append((chat, text, hub_msg)); return 88


def hit(i, tags="autumn, leaves, forest", dur=15, w=1280):
    return {"id": i, "tags": tags, "duration": dur, "pageURL": f"https://pixabay.com/videos/{i}/",
            "videos": {"small": {"url": f"https://cdn/{i}.mp4", "width": w, "height": 720}}}


class TestMorning(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        service.ERRORS.clear()

    def rows(self, channel, day=FRI):
        return {r["key"]: r for r in self.db.execute("SELECT * FROM fixed_posts WHERE channel=? AND day=?",
                                                     (channel, day.isoformat()))}

    def test_times_fixed_and_from_bomdod(self):
        now = at("22:40")
        morning.ensure_all(self.db, CFG, now)
        d = self.rows("davra")
        self.assertEqual(dt.datetime.fromisoformat(d["day"]["at"]), at("06:00", FRI))
        self.assertEqual(dt.datetime.fromisoformat(d["greeting"]["at"]), at("06:30", FRI))
        x = self.rows("xojaobod")                                  # без времени намаза — запасное
        self.assertEqual(dt.datetime.fromisoformat(x["day"]["at"]), at("06:10", FRI))
        namaz.save(self.db, [(THU, {"bomdod": "05:46", "peshin": "12:45", "asr": "15:59", "shom": "17:44", "xufton": "19:09"})], now)
        morning.ensure_all(self.db, CFG, now)                      # время намаза ввели — пост сдвинулся
        x = self.rows("xojaobod")
        self.assertEqual(dt.datetime.fromisoformat(x["day"]["at"]), at("06:06", FRI))
        self.assertEqual(dt.datetime.fromisoformat(x["greeting"]["at"]), at("06:31", FRI))
        self.assertEqual(self.rows("davra", THU)["day"]["status"], "skipped")   # сегодняшнее утро уже прошло

    def test_occupied_includes_morning(self):
        now = at("22:40")
        morning.ensure_all(self.db, CFG, now)
        busy = smart.occupied(self.db, "davra", at("06:00", FRI))
        self.assertIn(at("06:30", FRI), busy)

    def test_calendar_and_creative_fallback(self):
        self.assertEqual(morning.calendar_day(FRI)["name"], "Бутунжаҳон озиқ-овқат куни")
        t, note = morning.day_text(self.db, "КАТТА ДАВРА", FRI)
        self.assertTrue(t.startswith("📅 БУГУН — БУТУНЖАҲОН ОЗИҚ-ОВҚАТ КУНИ!"))
        self.assertIn("шаблон", note)
        t2, _ = morning.day_text(self.db, "КАТТА ДАВРА", dt.date(2026, 10, 18))
        self.assertIn("КУНИГА АЙЛАНТИРАЙЛИК", t2)
        self.assertNotIn("халқаро", t2.lower())

    def test_day_text_ai_prompt_and_cache(self):
        os.environ["GEMINI_API_KEY"] = "x"
        seen = []
        with mock.patch.object(ai, "generate", side_effect=lambda db, s, u, http=None: seen.append(u) or "📅 БУГУН — ТЕСТ!"):
            t, note = morning.day_text(self.db, "КАТТА ДАВРА", FRI)
            t2, n2 = morning.day_text(self.db, "PaparazziUZ", FRI)
        self.assertEqual((t, t2, n2), ("📅 БУГУН — ТЕСТ!", "📅 БУГУН — ТЕСТ!", "из кэша"))
        self.assertEqual(len(seen), 1)                              # один вызов ИИ на дату для всех каналов
        self.assertIn("Бутунжаҳон озиқ-овқат куни", seen[0])

    def test_video_filter(self):
        self.assertTrue(morning.video_ok(hit(1)))
        self.assertFalse(morning.video_ok(hit(2, tags="autumn, woman, park")))
        self.assertFalse(morning.video_ok(hit(3, tags="calendar, autumn")))
        self.assertFalse(morning.video_ok(hit(4, dur=3)))
        self.assertFalse(morning.video_ok(hit(5, w=640)))

    def test_pick_video_no_repeat(self):
        data = {"hits": [hit(1), hit(2, tags="girl, autumn"), hit(3)]}
        a = morning.pick_video(self.db, "k", FRI, fetch=lambda u: data)
        b = morning.pick_video(self.db, "k", FRI, fetch=lambda u: data)
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual({a["id"], b["id"]}, {1, 3})
        with self.assertRaises(RuntimeError):
            morning.pick_video(self.db, "k", FRI, fetch=lambda u: data)

    def test_season_and_caption(self):
        self.assertEqual(morning.season(dt.date(2026, 11, 30)), "autumn")
        self.assertEqual(morning.season(dt.date(2026, 12, 1)), "winter")
        cap = morning.greeting_caption(CFG["channels"]["davra"], morning.opts(CFG["channels"]["davra"]), FRI)
        self.assertTrue(cap.startswith("#Хайрли_тонг\n🍂☀️ ХАЙРЛИ ТОНГ!"))
        self.assertIn("Жума тонги муборак", cap)
        self.assertTrue(cap.endswith("🎉 @kattadavrauz"))

    def test_prepare_waits_until_evening(self):
        bot = Bot()
        self.assertFalse(morning.prepare_next(bot, self.db, CFG, ENV, now=at("12:00")))

    def test_prepare_publish_cycle(self):
        bot = Bot()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=orange:s=1280x720:d=7",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)], check=True)
            hits = {"hits": [hit(i) for i in range(1, 6)]}
            for h in hits["hits"]:
                h["videos"]["small"]["url"] = src.as_uri()
            uploads = []

            def upload(token, chat, path, caption):
                self.assertGreater(path.stat().st_size, 1000)
                uploads.append(caption); return {"message_id": 500 + len(uploads)}
            now = at("22:40")
            n = 0
            while morning.prepare_next(bot, self.db, CFG, ENV, now=now, work_root=Path(tmp) / "w",
                                       fetch=lambda u: hits, upload=upload):
                n += 1
                self.assertLess(n, 20)
        self.assertEqual(len(uploads), 3)                          # по видео на каждый канал
        previews = [c for c in bot.calls if c[0] in ("copyMessage", "sendMessage")]
        self.assertEqual(len(previews), 6)
        self.assertIn("mo:r:", str(previews[0][1]["reply_markup"]))
        vids = {r["video_id"] for r in self.db.execute("SELECT video_id FROM fixed_posts WHERE key='greeting' AND day=?", (FRI.isoformat(),))}
        self.assertEqual(len(vids), 3)                             # разные видео в разных каналах
        # утро: публикация
        pb, acc = Pub(), Acc()
        res = asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:00", FRI) + dt.timedelta(seconds=30), log=lambda s: None))
        self.assertEqual(res["morning"], 2)                        # Давра и Paparazzi — 06:00
        self.assertEqual({c for c, _, _ in pb.sent}, {"@kattadavrauz", "@ozodjamoll"})   # Paparazzi: утро в канале
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:11", FRI), log=lambda s: None))
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:31", FRI), log=lambda s: None))
        greet = [s for s in pb.sent if s[2]]
        self.assertEqual(len(greet), 2)
        self.assertTrue(all(s[1].startswith("#Хайрли_тонг") for s in greet))
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:35", FRI), log=lambda s: None))
        self.assertEqual([c for c, _, _ in acc.sent], [-100111, -100111])   # Хўжаобод — в тестовую группу
        self.assertFalse(service.ERRORS)

    def test_not_prepared_is_skipped_and_reported(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": Pub(), "account": Acc()}, now=at("06:20", FRI), log=lambda s: None))
        self.assertEqual(self.rows("davra")["day"]["status"], "skipped")
        self.assertTrue(any("не успели подготовить" in e for e in service.ERRORS))

    def test_buttons_redo_and_cancel(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        rid = self.rows("davra")["day"]["id"]
        morning.update(self.db, rid, prepared=1, text="x", preview_sent=1)
        bot = Bot()
        cq = {"id": "1", "from": {"id": 42}, "data": f"mo:x:{rid}", "message": {"chat": {"id": 42}, "message_id": 5}}
        hub.callback(bot, self.db, CFG, {42}, cq)
        self.assertEqual(morning.get(self.db, rid)["status"], "cancelled")
        hub.callback(bot, self.db, CFG, {42}, {**cq, "data": f"mo:r:{rid}"})
        r = morning.get(self.db, rid)
        self.assertEqual((r["status"], r["prepared"], r["redo"]), ("pending", 0, 1))

    def test_overview(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        t = morning.overview(self.db, CFG, at("22:40"))
        self.assertIn("16.10 · Жума", t)
        self.assertIn("КАТТА ДАВРА: Хайрли тонг — готовится", t)


if __name__ == "__main__":
    unittest.main()
