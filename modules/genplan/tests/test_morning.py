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
        # тесты не должны видеть настоящий запас сервера (/var/lib/papa-genplan/pool)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = mock.patch.dict(os.environ, {"PAPA_GENPLAN_STATE": tmp.name, "POOL_VISION_GAP": "0"})
        env.start()
        self.addCleanup(env.stop)
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
        self.assertEqual(dt.datetime.fromisoformat(d["greeting"]["at"]), at("06:00", FRI))   # день начинается с «Хайрли тонг»
        self.assertEqual(dt.datetime.fromisoformat(d["day"]["at"]), at("06:30", FRI))
        x = self.rows("xojaobod")                                  # без времени намаза — запасное
        self.assertEqual(dt.datetime.fromisoformat(x["day"]["at"]), at("06:10", FRI))
        namaz.save(self.db, [(THU, {"bomdod": "05:46", "peshin": "12:45", "asr": "15:59", "shom": "17:44", "xufton": "19:09"})], now)
        morning.ensure_all(self.db, CFG, now)                      # время намаза ввели — пост сдвинулся
        x = self.rows("xojaobod")
        self.assertEqual(dt.datetime.fromisoformat(x["day"]["at"]), at("06:06", FRI))
        self.assertEqual(dt.datetime.fromisoformat(x["greeting"]["at"]), at("05:01", FRI))   # до таблицы намаза (05:16)
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
        self.assertTrue(cap.startswith("#Хайрли_тонг\n🕌🤲 ЖУМА ТОНГИ МУБОРАК БЎЛСИН!"))
        self.assertGreater(len(cap), 350)                          # не сухо: несколько тёплых абзацев
        self.assertIn("🤲", cap)
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
        kb = str(previews[0][1]["reply_markup"])
        self.assertIn("mo:a:", kb); self.assertIn("mo:x:", kb)        # ✅ Одобрить и 🗑 Не публиковать
        # без ✅ не выходит: Хўжаобод не одобряем — пропуск с напоминанием
        for r in self.db.execute("SELECT id, channel FROM fixed_posts WHERE day=?", (FRI.isoformat(),)).fetchall():
            if r["channel"] != "xojaobod":
                hub.callback(Bot(), self.db, CFG, {42}, {"id": "1", "from": {"id": 42}, "data": f"mo:a:{r['id']}",
                                                       "message": {"chat": {"id": 42}, "message_id": 5}})
        vids = {r["source"] for r in self.db.execute("SELECT source FROM fixed_posts WHERE key='greeting' AND day=?", (FRI.isoformat(),))}
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
        self.assertEqual(acc.sent, [])                                       # Хўжаобод не одобрен — не вышел
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:55", FRI), log=lambda s: None))
        self.assertTrue(any("не одобрен" in e for e in service.ERRORS))
        self.assertEqual(self.rows("xojaobod")["greeting"]["error"], "не одобрен")

    def make_pool(self, tmp):
        root = Path(tmp) / "pool"
        root.mkdir()
        for k in ("a", "b", "c"):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=green:s=720x1280:d=6",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-shortest",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(root / f"{k}.mp4")], check=True)
        rows = [{"key": "a", "file": "a.mp4", "channel": "Катта канал", "views": 900, "duration": 6, "date": "2026-10-09", "weekday": "Жума"},
                {"key": "b", "file": "b.mp4", "channel": "Катта канал", "views": 800, "duration": 6, "date": "2026-10-09", "weekday": "Жума", "text": "🤲 Жума куни муборак бўлсин, азизлар! Барчага барака тилаймиз @begona"},
                {"key": "c", "file": "c.mp4", "channel": "Бошқа", "views": 700, "duration": 6, "date": "2026-10-10", "weekday": None}]
        (root / "index.jsonl").write_text("\n".join(__import__("json").dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        (root / "examples.json").write_text('[{"weekday": "Жума", "views": 5, "text": "🕌 ЖУМА ТОНГИ МУБОРАК! @begona #juma t.me/x"}]', encoding="utf-8")
        return root

    def test_pool_check_pick_and_prepare(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PAPA_GENPLAN_STATE": tmp, "GEMINI_API_KEY": "x"}):
            root = self.make_pool(tmp)
            self.assertEqual(morning.pool_import(self.db), 3)
            self.assertEqual(morning.pool_import(self.db), 0)
            answers = iter([{"date": True, "foreign": False, "people": False, "weekday": None, "season": "autumn", "quality": 5},
                            {"date": False, "foreign": False, "people": False, "weekday": "Жума", "season": "autumn", "quality": 4},
                            {"date": False, "foreign": True, "people": False, "weekday": None, "season": "neutral", "quality": 4}])
            with mock.patch.object(ai, "vision", side_effect=lambda *a, **k: next(answers)):
                self.assertTrue(morning.pool_check_one(self.db, FRI))
                self.assertTrue(morning.pool_check_one(self.db, FRI))
                self.assertTrue(morning.pool_check_one(self.db, FRI))
                self.assertFalse(morning.pool_check_one(self.db, FRI))
            st = {r["key"]: (r["status"], r["reason"]) for r in self.db.execute("SELECT * FROM morning_pool")}
            self.assertEqual(st["a"], ("rejected", "дата на видео"))
            self.assertEqual(st["b"], ("ok", None))
            self.assertEqual(st["c"][0], "rejected")                # чужой логотип — по умолчанию не берём
            self.assertFalse((root / "a.mp4").exists())              # отбракованное удаляется
            self.assertIn("ЖУМА ТОНГИ", morning.examples("Жума")[0])
            self.assertNotIn("@begona", morning.examples("Жума")[0])
            # подготовка: ИИ пишет текст, видео — из пула (с музыкой), с нашим @
            seen = []
            gen = lambda db, s, u, http=None: seen.append(u) or "🕌 ЖУМА ТОНГИ МУБОРАК!\n\n☀️ Ассалому алайкум!"
            uploads = []

            def upload(token, chat, path, caption):
                uploads.append((path.stat().st_size, caption)); return {"message_id": 900}
            morning.ensure_all(self.db, CFG, at("22:40"))
            with mock.patch.object(ai, "generate", side_effect=gen):
                r = self.rows("davra")["greeting"]
                note = morning.prepare_one(Bot(), self.db, CFG, ENV, r, at("22:40"), Path(tmp) / "w", upload=upload)
            self.assertIn("Готовое видео (Жума)", note)
            self.assertIn("ЖУМА ТОНГИ МУБОРАК", seen[0])             # образец больших каналов передан ИИ
            self.assertIn("Жума куни муборак бўлсин, азизлар", seen[0])   # подпись этого же видео — главный ориентир
            self.assertNotIn("@begona", seen[0])
            self.assertTrue(uploads[0][1].startswith("#Хайрли_тонг\n🕌 ЖУМА ТОНГИ МУБОРАК!"))
            self.assertTrue(uploads[0][1].endswith("🎉 @kattadavrauz"))
            self.assertEqual(self.rows("davra")["greeting"]["source"], "pool:b")
            self.assertIsNone(morning.pool_pick(self.db, FRI))      # одно видео не повторяется

    def test_pool_from_telegram_channel(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PAPA_GENPLAN_STATE": tmp, "GEMINI_API_KEY": "x"}):
            root = Path(tmp) / "pool"
            root.mkdir()
            (root / "index.jsonl").write_text(__import__("json").dumps(
                {"key": "pool_77", "pool_chat": -100555, "msg_id": 77, "source": "Катта канал", "views": 5, "duration": 8,
                 "date": "2026-10-09", "weekday": "Жума", "text": "Жума тонги муборак"}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(morning.pool_import(self.db), 1)
            got = []

            def fetch(row, dst):
                got.append((row["pool_chat"], row["msg_id"]))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=3",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dst)], check=True)
            ans = {"date": False, "foreign": False, "people": False, "greeting": True, "weekday": None, "season": "autumn", "quality": 4}
            with mock.patch.object(ai, "vision", return_value=ans):
                self.assertTrue(morning.pool_check_one(self.db, FRI, fetch_file=fetch))
            self.assertEqual(got, [(-100555, 77)])
            self.assertEqual(self.db.execute("SELECT status FROM morning_pool").fetchone()[0], "ok")
            self.assertTrue((root / "pool_77.mp4").exists())
            # бот: пересылка в хаб, удаление копии, getFile
            bot = Bot()
            calls = []

            def fake_bot(m, **p):
                calls.append(m)
                return {"forwardMessage": {"message_id": 5, "video": {"file_id": "F"}}, "getFile": {"file_path": "v/1.mp4"}}.get(m, {})
            with mock.patch("urllib.request.urlopen", return_value=__import__("io").BytesIO(b"x" * 20)):
                morning.tg_fetch(fake_bot, ENV, {"pool_chat": -100555, "msg_id": 77}, Path(tmp) / "f.mp4")
            self.assertEqual(calls, ["forwardMessage", "deleteMessage", "getFile"])
            ans2 = {**ans, "greeting": False}
            (root / "index.jsonl").write_text('{"key": "pool_78", "pool_chat": -100555, "msg_id": 78, "weekday": null}', encoding="utf-8")
            morning.pool_import(self.db)
            with mock.patch.object(ai, "vision", return_value=ans2):
                morning.pool_check_one(self.db, FRI, fetch_file=fetch)
            self.assertEqual(self.db.execute("SELECT reason FROM morning_pool WHERE key='pool_78'").fetchone()[0],
                             "не утреннее поздравление")

    def test_not_prepared_is_skipped_and_reported(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": Pub(), "account": Acc()}, now=at("06:50", FRI), log=lambda s: None))
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
        self.assertIn("НЕ ВЫЙДЕТ", str(bot.calls[-2][1]["reply_markup"]))
        hub.callback(bot, self.db, CFG, {42}, {**cq, "data": f"mo:u:{rid}"})
        self.assertEqual(morning.get(self.db, rid)["status"], "pending")
        hub.callback(bot, self.db, CFG, {42}, {**cq, "data": f"mo:a:{rid}"})
        self.assertEqual(morning.get(self.db, rid)["approved"], 1)
        self.assertIn("ОДОБРЕНО", str(bot.calls[-2][1]["reply_markup"]))
        hub.callback(bot, self.db, CFG, {42}, {**cq, "data": f"mo:r:{rid}"})
        r = morning.get(self.db, rid)
        self.assertEqual((r["status"], r["prepared"], r["redo"]), ("pending", 0, 1))

    def test_evening_approval_reminder(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        self.db.execute("UPDATE fixed_posts SET prepared=1"); self.db.commit()
        self.assertIsNone(morning.approval_reminder(self.db, CFG, at("21:00")))
        t = morning.approval_reminder(self.db, CFG, at("22:05"))
        self.assertIn("не одобрено постов: 6", t)
        self.assertIsNone(morning.approval_reminder(self.db, CFG, at("22:30")))     # раз в день

    def test_use_manual_pool_post(self):
        morning.ensure_all(self.db, CFG, at("00:20", FRI))
        calls = []

        def bot(m, **p):
            calls.append((m, p)); return {"message_id": 700 + len(calls)}
        done = morning.use_manual(bot, self.db, CFG, ENV, {"pool_chat": -100555, "msg_id": 9,
                                                          "text": "🗣 ЖУМА АЙЁМИНГИЗ МУБОРАК БЎЛСИН!\n\n@muslimuzportal t.me/x"},
                                  now=at("00:20", FRI))
        self.assertEqual(len(done), 3)
        cap = calls[0][1]["caption"]
        self.assertTrue(cap.startswith("🗣 ЖУМА АЙЁМИНГИЗ МУБОРАК БЎЛСИН!"))
        self.assertNotIn("muslimuzportal", cap)
        r = self.rows("davra")["greeting"]
        self.assertTrue(r["text"].rstrip().endswith("🎉 @kattadavrauz"))
        self.assertEqual((r["prepared"], r["approved"], r["preview_sent"]), (1, 0, 0))

    def test_use_sklad(self):
        morning.ensure_all(self.db, CFG, at("00:50", FRI))
        calls = []

        def bot(m, **p):
            calls.append((m, p)); return {"message_id": 800 + len(calls)}
        items = [{"chat": -100999, "msg_id": 1, "text": "🌿 Жума тонги муборак! @begona"},
                 {"chat": -100999, "msg_id": 2, "text": ""}, {"chat": -100999, "msg_id": 3, "text": ""}]
        done = morning.use_sklad(bot, self.db, CFG, ENV, items, now=at("00:50", FRI))
        self.assertEqual(len(done), 3)
        d, p, x = (self.rows(c)["day"] for c in ("davra", "paparazzi", "xojaobod"))
        self.assertEqual((d["source"], p["source"], x["source"]), ("sklad:1", "sklad:2", "sklad:3"))
        self.assertTrue(d["text"].startswith("📅 16-октябр · Жума\n\n🌿 Жума тонги муборак!"))
        self.assertNotIn("@begona", p["text"])
        self.assertTrue(p["text"].rstrip().endswith("⭐ @ozodjamoll"))
        self.assertEqual((d["prepared"], d["approved"]), (1, 0))

    def test_overview(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        t = morning.overview(self.db, CFG, at("22:40"))
        self.assertIn("16.10 · Жума", t)
        self.assertIn("КАТТА ДАВРА: Хайрли тонг — готовится", t)


if __name__ == "__main__":
    unittest.main()
