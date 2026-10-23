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
        self.assertEqual(dt.datetime.fromisoformat(d["greeting"]["at"]), at("05:00", FRI))   # 17.10: день начинается в 05:00 с «Хайрли тонг»
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
        ch = CFG["channels"]["davra"]
        cap = morning.greeting_caption(ch, morning.opts(ch), FRI)
        # 17.10: шаблоны владельца (12 вариантов, у каналов разные в один день); юзернейм НАД хуком
        body, hook = morning.template_pick(ch, FRI)
        self.assertTrue(cap.startswith("#ЖУМА_МУБОРАК\n" + body.split("\n")[0]))   # 23.10: пятница — Жума
        self.assertTrue(cap.endswith("🎉 @kattadavrauz\n" + hook))
        self.assertNotIn("{", cap)
        self.assertLessEqual(len(cap), 1024)
        for k in range(12):                                         # три канала в один день — три разных текста
            d = FRI + dt.timedelta(days=k)
            firsts = {morning.template_pick(CFG["channels"][c], d)[0] for c in ("davra", "xojaobod", "paparazzi")}
            self.assertEqual(len(firsts), 3)
        day0 = next(FRI + dt.timedelta(days=k) for k in range(12)
                    if morning.template_pick(ch, FRI + dt.timedelta(days=k))[0].startswith("🌅 Ассалому"))
        self.assertIn(f"📅 Бугун, {day0.day} {morning.MONTHS_UZ[day0.month - 1]}", morning.template_pick(ch, day0)[0])
        ai_ch = {**ch, "morning": {**ch["morning"], "ai_greeting": True}}      # старый путь (ИИ) — по флагу
        cap = morning.greeting_caption(ai_ch, morning.opts(ai_ch), FRI)
        self.assertTrue(cap.startswith("#ЖУМА_МУБОРАК\n🕌🤲 ЖУМА ТОНГИ МУБОРАК БЎЛСИН!"))
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
            hits = {"hits": []}                                     # 23.10: Pixabay не используется — только пул
            morning.pool_dir().mkdir(parents=True, exist_ok=True)
            for k in ("p1", "p2", "p3", "p4"):
                __import__("shutil").copyfile(src, morning.pool_dir() / f"{k}.mp4")
                self.db.execute("INSERT INTO morning_pool(key,file,status,weekday,season,quality,views) "
                                "VALUES (?,?,'ok',NULL,'autumn',4,10)", (k, f"{k}.mp4"))
            self.db.commit()
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
        kbs = [str(p[1]["reply_markup"]) for p in previews]
        self.assertFalse(any("mo:a:" in k for k in kbs))                # 20.10: ✅ не нужен никому — утро выходит само
        self.assertEqual(sum("Выйдет сам" in k for k in kbs), 6)        # оба утренних поста — автопилот с вето 🗑
        self.assertTrue(all("mo:x:" in k for k in kbs))
        # «Бугун — … куни» без ✅ не выходит: в Хўжаободе не одобряем — пропуск с напоминанием
        for r in self.db.execute("SELECT id, channel FROM fixed_posts WHERE day=?", (FRI.isoformat(),)).fetchall():
            if r["channel"] != "xojaobod":
                hub.callback(Bot(), self.db, CFG, {42}, {"id": "1", "from": {"id": 42}, "data": f"mo:a:{r['id']}",
                                                       "message": {"chat": {"id": 42}, "message_id": 5}})
        vids = {r["source"] for r in self.db.execute("SELECT source FROM fixed_posts WHERE key='greeting' AND day=?", (FRI.isoformat(),))}
        self.assertEqual(len(vids), 3)                             # разные видео в разных каналах
        # утро: публикация
        pb, acc = Pub(), Acc()
        res = asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("05:00", FRI) + dt.timedelta(seconds=30), log=lambda s: None))
        self.assertEqual(res["morning"], 3)                        # Давра, Paparazzi и Хўжаобод (без намаза — 05:00) — сами
        self.assertEqual({c for c, _, _ in pb.sent}, {"@kattadavrauz", "@ozodjamoll"})   # Paparazzi: утро в канале
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:11", FRI), log=lambda s: None))
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:31", FRI), log=lambda s: None))
        greet = [s for s in pb.sent if s[2]]
        self.assertEqual(len(greet), 2)
        self.assertTrue(all(s[1].startswith("#ЖУМА_МУБОРАК") for s in greet))   # 23.10: пятница
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:35", FRI), log=lambda s: None))
        asyncio.run(service.tick(self.db, CFG, ENV, {"bot": pb, "account": acc}, now=at("06:55", FRI), log=lambda s: None))
        x = self.rows("xojaobod")
        self.assertEqual(x["greeting"]["status"], "done")                    # «Хайрли тонг» вышел сам (цикл как в Хўжаободе)
        self.assertEqual(x["day"]["status"], "done")                         # 20.10: «Бугун — … куни» тоже сам, без ✅
        self.assertFalse(any("не одобрен" in e for e in service.ERRORS))

    def test_no_pool_video_no_pixabay(self):
        """23.10: в пуле пусто — никаких Pixabay-шаблонов: ошибка подготовки (владелец увидит), а не дешёвка."""
        morning.ensure_day(self.db, CFG, "davra", FRI, at("18:00", THU))
        r = self.rows("davra")["greeting"]
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(RuntimeError):
            morning.prepare_one(Bot(), self.db, CFG, ENV, r, at("22:00", THU), Path(tmp) / "w",
                                fetch=lambda u: self.fail("Pixabay не должен вызываться"),
                                upload=lambda *a: self.fail("загрузки быть не должно"))

    def test_video_goes_as_is(self):
        """23.10: готовое видео из пула уходит как есть — без надписи и метки (тот же файл)."""
        morning.pool_dir().mkdir(parents=True, exist_ok=True)
        (morning.pool_dir() / "v.mp4").write_bytes(b"ORIGINAL-VIDEO")
        self.db.execute("INSERT INTO morning_pool(key,file,status,weekday,season,quality,views) VALUES "
                        "('v','v.mp4','ok',NULL,'autumn',5,10)")
        morning.ensure_day(self.db, CFG, "davra", THU, at("04:00", THU - dt.timedelta(days=1)))
        r = self.rows("davra", THU)["greeting"]
        got = []

        def upload(tok, chat, path, cap):
            got.append(path.read_bytes()); return {"message_id": 1}
        from genplan import media
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(media, "watermark_video", side_effect=AssertionError("метки быть не должно")):
            morning.prepare_one(Bot(), self.db, CFG, ENV, r, at("22:00", THU - dt.timedelta(days=1)), Path(tmp) / "w",
                                upload=upload)
        self.assertEqual(got, [b"ORIGINAL-VIDEO"])

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
            CFG["channels"]["davra"]["morning"]["ai_greeting"] = True        # этот тест проверяет путь с ИИ
            self.addCleanup(CFG["channels"]["davra"]["morning"].pop, "ai_greeting", None)
            with mock.patch.object(ai, "generate", side_effect=gen):
                r = self.rows("davra")["greeting"]
                note = morning.prepare_one(Bot(), self.db, CFG, ENV, r, at("22:40"), Path(tmp) / "w", upload=upload)
            self.assertIn("Готовое видео (Жума)", note)
            self.assertIn("ЖУМА ТОНГИ МУБОРАК", seen[0])             # образец больших каналов передан ИИ
            self.assertIn("Жума куни муборак бўлсин, азизлар", seen[0])   # подпись этого же видео — главный ориентир
            self.assertNotIn("@begona", seen[0])
            self.assertTrue(uploads[0][1].startswith("#ЖУМА_МУБОРАК\n🕌 ЖУМА ТОНГИ МУБОРАК!"))
            self.assertTrue(uploads[0][1].endswith("🎉 @kattadavrauz"))
            self.assertEqual(self.rows("davra")["greeting"]["source"], "pool:b")
            # 23.10: свежего нет — давно не выходившее видео (повтор лучше дешёвого шаблона Pixabay)
            self.assertIsNotNone(morning.pool_pick(self.db, FRI + dt.timedelta(days=7)))
            self.assertEqual(morning.pool_pick(self.db, FRI)["key"], "b")    # 23.10: но в ту же Жуму — и в другие каналы

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
        self.assertIn("УТВЕРЖДЕНО", str(bot.calls[-2][1]["reply_markup"]))
        hub.callback(bot, self.db, CFG, {42}, {**cq, "data": f"mo:r:{rid}"})
        r = morning.get(self.db, rid)
        self.assertEqual((r["status"], r["prepared"], r["redo"]), ("pending", 0, 1))

    def test_evening_approval_reminder(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        self.db.execute("UPDATE fixed_posts SET prepared=1"); self.db.commit()
        self.assertIsNone(morning.approval_reminder(self.db, CFG, at("21:00")))
        # 20.10 владелец: утро — протокол, выходит само; напоминаний «одобрите» больше нет
        self.assertIsNone(morning.approval_reminder(self.db, CFG, at("22:05")))

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
        self.assertTrue(cap.startswith("#ХАЙРЛИ_ТОНГ\n🗣 ЖУМА АЙЁМИНГИЗ МУБОРАК БЎЛСИН!"))
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
        self.assertTrue(d["text"].startswith("#БУГУН\n📅 16-октябр · Жума\n\n🌿 Жума тонги муборак!"))
        self.assertNotIn("@begona", p["text"])
        self.assertTrue(p["text"].rstrip().endswith("⭐ @ozodjamoll"))
        self.assertEqual((d["prepared"], d["approved"]), (1, 0))

    def test_drop_wrong_dates(self):
        t = "🌿 ХАЙРЛИ ТОНГ!\n15 сентябрь — сешанба куни барчамиз учун омадли ўтсин! 🤲\nЖума куни муборак!\nЭНГ ЯҚИНЛАРГА УЛАШИБ ҚЎЙИНГ."
        out = morning.drop_wrong_dates(t, FRI)
        self.assertNotIn("сентябрь", out)
        self.assertIn("Жума куни муборак!", out)
        self.assertIn("ЭНГ ЯҚИНЛАРГА", out)
        self.assertIn("Душанба", morning.drop_wrong_dates("Душанба тонги", dt.date(2026, 10, 19)))
        self.assertEqual(morning.drop_wrong_dates("Шанба тонги", FRI), "")

    def test_overview(self):
        morning.ensure_all(self.db, CFG, at("22:40"))
        t = morning.overview(self.db, CFG, at("22:40"))
        self.assertIn("16.10 · Жума", t)
        self.assertIn("КАТТА ДАВРА: Хайрли тонг — готовится", t)


if __name__ == "__main__":
    unittest.main()


class TestAccountHealth(unittest.TestCase):
    def run_check(self, acc):
        from genplan.__main__ import account_health
        return asyncio.run(account_health(acc, CFG, ENV))

    def test_states(self):
        class P:
            def __init__(self, admin): self.is_admin, self.is_creator = admin, False

        class Acc:
            def __init__(self, auth=True, admin=True, exc=None): self.auth, self.admin, self.exc = auth, admin, exc
            async def is_user_authorized(self):
                if self.exc: raise self.exc
                return self.auth
            async def get_permissions(self, to, who): return P(self.admin)

        class AuthKeyUnregisteredError(Exception): pass
        self.assertIsNone(self.run_check(Acc()))
        self.assertIn("отключён", self.run_check(Acc(auth=False)))
        self.assertIn("нет прав админа", self.run_check(Acc(admin=False)))
        self.assertIn("отключён", self.run_check(Acc(exc=AuthKeyUnregisteredError("x"))))


class TestHashtags(unittest.TestCase):
    def test_clean_and_tag(self):
        from genplan import text as T
        src = "Бугун #Байрам_муборак куни барчага табрик!\nЯнгилик #tezkor #uzbekiston\n#reklama #news"
        out = T.finalize(src, "🎉 @kattadavrauz", tag="#ЯНГИЛИКЛАР")
        self.assertTrue(out.startswith("#ЯНГИЛИКЛАР\nБугун Байрам муборак куни барчага табрик!"))
        self.assertNotIn("#tezkor", out); self.assertNotIn("#reklama", out); self.assertNotIn("#news", out)
        self.assertIn("Янгилик", out)
        self.assertEqual(out.count("#"), 1)

    def test_publish_uses_rubric_tag(self):
        from genplan import service
        db = store.connect(":memory:")
        mid = store.add_material(db, -100777, 5, "Кулгили видео #prikol", False)
        store.update(db, mid, channel="davra", rubric="Ҳажвия", status="queued", scheduled_at=at("09:00").isoformat())
        sent = []

        class P:
            def publish(self, chat, text, *a, **k):
                sent.append(text); return 1
        asyncio.run(service.publish_one(db, CFG, ENV, {"bot": P(), "account": P()}, "davra", store.get(db, mid), "09:00",
                                        "2026-10-15", log=lambda s: None))
        self.assertTrue(sent[0].startswith("#ҲАЖВИЯ\nКулгили видео"))
        self.assertNotIn("#prikol", sent[0])


class TestPromo(unittest.TestCase):
    def test_foreign_tail_removed(self):
        from genplan import text as T
        src = ("⚡ Миллийлик руҳи ёшларни тарбиялашда катта аҳамиятга эга.\n\n"
               "⚡ ДУНЁ🌐УЗ - ТВ ДА КЎРСАТМАЙДИГАН ХАБАРЛАР КАНАЛИ!")
        out = T.finalize(src, "🎉 @kattadavrauz", tag="#ҚИЗИҚАРЛИ")
        self.assertNotIn("КАНАЛИ", out)
        self.assertIn("Миллийлик руҳи", out)
        self.assertTrue(out.endswith("🎉 @kattadavrauz"))

    def test_body_kept_when_single_paragraph(self):
        from genplan import text as T
        self.assertIn("Бугун ҳаво илиқ", T.finalize("Бугун ҳаво илиқ бўлади.", "x"))


class TestPoolEconomy(unittest.TestCase):
    """Экономия Gemini: кадры проверяем, только пока запаса не хватает на 3 дня, и не больше лимита в сутки."""

    def setUp(self):
        self.db = store.connect(":memory:")
        self.day = dt.date(2026, 10, 17)            # суббота
        self.now = dt.datetime(2026, 10, 16, 14, 0, tzinfo=plan.TZ)

    def add(self, key, status, weekday=None):
        self.db.execute("INSERT INTO morning_pool(key,file,status,weekday) VALUES (?,?,?,?)", (key, key + ".mp4", status, weekday))
        self.db.commit()

    def test_checks_when_stock_is_low(self):
        self.add("n1", "new")
        self.assertTrue(morning.pool_checking(self.db, CFG, self.day, self.now))

    def test_stops_when_enough_for_three_days(self):
        self.add("n1", "new")
        need = sum(1 for c in CFG["channels"].values() if morning.opts(c)) * morning.AHEAD_DAYS
        for i in range(need):
            self.add(f"ok{i}", "ok")
        self.assertTrue(morning.pool_enough(self.db, CFG, self.day))
        self.assertFalse(morning.pool_checking(self.db, CFG, self.day, self.now))

    def test_far_weekday_waits(self):
        wd = morning.WEEKDAY[(self.day + dt.timedelta(days=4)).weekday()]
        self.add("far", "new", wd)                  # видео под день через 4 дня — пока не тратим Gemini
        self.assertFalse(morning.pool_checking(self.db, CFG, self.day, self.now))

    def test_daily_cap(self):
        self.add("n1", "new")
        store.kv_set(self.db, f"pool_checks_{self.now.date().isoformat()}", str(morning.DAILY_CAP))
        self.assertFalse(morning.pool_checking(self.db, CFG, self.day, self.now))


class OwnBotMorning(unittest.TestCase):
    """18.10 (владелец): каждый бот — свой сектор. У PaparazziUZ свой бот-пульт — утро публикует он, не главный."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = mock.patch.dict(os.environ, {"PAPA_GENPLAN_STATE": tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.db = store.connect(":memory:")
        service.ERRORS.clear()

    def test_own_bot_uploads_greeting(self):
        from genplan import bots, fabrika
        now = at("05:00", FRI) + dt.timedelta(seconds=30)
        morning.ensure_day(self.db, CFG, "paparazzi", FRI, now)
        rid = self.db.execute("SELECT id FROM fixed_posts WHERE channel='paparazzi' AND key='greeting'").fetchone()["id"]
        morning.update(self.db, rid, prepared=1, approved=1, hub_msg=5, text="#ХАЙРЛИ_ТОНГ\nсалом")
        f = morning.own_file(rid)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"mp4")
        main, own = Pub(), Pub()
        calls = []
        with mock.patch.dict(bots.TOKENS, {"paparazzi": "own-token"}), \
                mock.patch.object(fabrika, "upload_video", lambda tok, chat, p, cap, kb=None: calls.append((tok, chat, cap)) or {"message_id": 9}):
            n = asyncio.run(service.tick_morning(self.db, CFG, ENV, {"bot": main, "account": Pub(), "bot:paparazzi": own},
                                                 now, log=lambda s: None))
        self.assertEqual(n, 1)
        self.assertEqual(calls, [("own-token", "@ozodjamoll", "#ХАЙРЛИ_ТОНГ\nсалом")])
        self.assertEqual(main.sent, [])                         # главный бот в PaparazziUZ не публикует
        self.assertFalse(f.exists())
        self.assertEqual(morning.get(self.db, rid)["status"], "done")

    def test_own_bot_without_file_fails_loudly(self):
        now = at("05:00", FRI) + dt.timedelta(seconds=30)
        morning.ensure_day(self.db, CFG, "paparazzi", FRI, now)
        rid = self.db.execute("SELECT id FROM fixed_posts WHERE channel='paparazzi' AND key='greeting'").fetchone()["id"]
        morning.update(self.db, rid, prepared=1, approved=1, hub_msg=5, text="x")
        asyncio.run(service.tick_morning(self.db, CFG, ENV, {"bot": Pub(), "account": Pub(), "bot:paparazzi": Pub()},
                                         now, log=lambda s: None))
        self.assertEqual(morning.get(self.db, rid)["status"], "failed")
        self.assertTrue(any("PaparazziUZ" in e for e in service.ERRORS))


class Juma2310(unittest.TestCase):
    """23.10 (владелец): Жума — во всех трёх каналах; штаб грузит утро в хаб; предпросмотр — в пульт своего канала;
    вручную поставленное время не сбрасывается."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        env = mock.patch.dict(os.environ, {"PAPA_GENPLAN_STATE": tmp.name, "POOL_VISION_GAP": "0"})
        env.start()
        self.addCleanup(env.stop)
        self.db = store.connect(":memory:")
        morning.setup(self.db)
        service.ERRORS.clear()

    def test_friday_text_and_tag_in_all_channels(self):
        texts = set()
        for c in ("davra", "paparazzi", "xojaobod"):
            ch = CFG["channels"][c]
            cap = morning.greeting_caption(ch, morning.opts(ch), FRI)
            self.assertTrue(cap.startswith("#ЖУМА_МУБОРАК\n"), c)
            self.assertIn("ЖУМА МУБОРАК", cap.upper())
            self.assertNotIn("{", cap)
            self.assertLessEqual(len(cap), 1024)
            texts.add(morning.template_pick(ch, FRI)[0])
        self.assertEqual(len(texts), 3)                          # три канала — три разных пятничных текста
        ch = CFG["channels"]["davra"]
        self.assertTrue(morning.greeting_caption(ch, morning.opts(ch), THU).startswith("#ХАЙРЛИ_ТОНГ\n"))

    def test_one_juma_video_goes_to_every_channel_today(self):
        self.db.execute("INSERT INTO morning_pool(key,file,status,weekday,season,quality,views) VALUES "
                        "('j','j.mp4','ok','Жума','autumn',5,10), ('g','g.mp4','ok',NULL,'autumn',5,10)")
        fri = FRI
        picks = []
        for i, c in enumerate(("davra", "paparazzi", "xojaobod")):     # готовится накануне вечером, канал за каналом
            morning.ensure_day(self.db, CFG, c, fri, at("18:00", THU))
            k = morning.pool_pick(self.db, fri, salt=i)["key"]
            self.db.execute("UPDATE fixed_posts SET source=? WHERE channel=? AND day=? AND key='greeting'",
                            (f"pool:{k}", c, fri.isoformat()))
            picks.append(k)
        self.assertEqual(picks, ["j", "j", "j"])               # не «первому каналу — Жума, остальным — обычное»
        sat = fri + dt.timedelta(days=1)
        self.assertEqual(morning.pool_pick(self.db, sat)["key"], "g")   # в другой день правило старое

    def test_pinned_time_is_not_reset(self):
        now = at("04:00", FRI)
        morning.ensure_day(self.db, CFG, "paparazzi", FRI, now)
        r = self.db.execute("SELECT * FROM fixed_posts WHERE channel='paparazzi' AND key='greeting'").fetchone()
        new = at("05:35", FRI).isoformat()
        morning.update(self.db, r["id"], at=new, pinned=1)
        morning.ensure_day(self.db, CFG, "paparazzi", FRI, now)
        self.assertEqual(morning.get(self.db, r["id"])["at"], new)
        morning.update(self.db, r["id"], pinned=0)
        morning.ensure_day(self.db, CFG, "paparazzi", FRI, now)
        self.assertNotEqual(morning.get(self.db, r["id"])["at"], new)   # без закрепления — как раньше, по расписанию

    def test_thursday_check_warns_once_without_juma_video(self):
        self.assertIsNone(morning.juma_check(self.db, at("17:00", THU)))
        msg = morning.juma_check(self.db, at("18:05", THU))
        self.assertIn("Жума", msg)
        self.assertIsNone(morning.juma_check(self.db, at("19:00", THU)))   # один раз
        self.assertIsNone(morning.juma_check(self.db, at("18:05", FRI)))

    def test_thursday_check_quiet_when_video_ready(self):
        (morning.pool_dir()).mkdir(parents=True, exist_ok=True)
        (morning.pool_dir() / "j.mp4").write_bytes(b"x")
        self.db.execute("INSERT INTO morning_pool(key,file,status,weekday) VALUES ('j','j.mp4','ok','Жума')")
        self.assertIsNone(morning.juma_check(self.db, at("18:05", THU)))

    def test_preview_goes_to_own_channel_pult(self):
        from genplan import bots, fabrika
        morning.ensure_day(self.db, CFG, "paparazzi", FRI, at("04:00", FRI))
        rid = self.db.execute("SELECT id FROM fixed_posts WHERE channel='paparazzi' AND key='greeting'").fetchone()["id"]
        morning.update(self.db, rid, prepared=1, hub_msg=5, text="#ЖУМА_МУБОРАК\nсалом")
        f = morning.own_file(rid); f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b"mp4")
        main, own = Bot(), Bot()

        def no_hub(m, **p):                                       # пульт PaparazziUZ не видит PAPA HUB
            if m == "copyMessage":
                raise RuntimeError("copyMessage: chat not found")
            return own(m, **p)
        ups = []
        with mock.patch.dict(bots.REG, {"main": main, "paparazzi": no_hub}, clear=True), \
                mock.patch.dict(bots.TOKENS, {"main": "t", "paparazzi": "own-token"}, clear=True), \
                mock.patch.object(fabrika, "upload_video", lambda tok, chat, p, cap, kb=None: ups.append((tok, chat)) or {"message_id": 1}):
            morning.preview(main, self.db, CFG, ENV, rid)
        self.assertEqual(main.calls, [])                          # пульт КАТТА ДАВРА чужое утро не показывает
        self.assertEqual(ups, [("own-token", 42)])               # видео — файлом из своего пульта

    def test_shtab_uploads_and_main_bot_ignores_it_in_hub(self):
        from genplan import bots
        self.db.execute("INSERT INTO morning_pool(key,file,status,weekday,season,quality,views) VALUES "
                        "('j','j.mp4','ok','Жума','autumn',5,10)")
        (morning.pool_dir()).mkdir(parents=True, exist_ok=True)
        (morning.pool_dir() / "j.mp4").write_bytes(b"x")
        morning.ensure_day(self.db, CFG, "davra", FRI, at("04:00", THU))
        r = self.db.execute("SELECT * FROM fixed_posts WHERE channel='davra' AND key='greeting'").fetchone()
        tokens = []

        def upload(tok, chat, path, cap):
            tokens.append(tok); return {"message_id": 321}
        from genplan import media
        with mock.patch.dict(bots.SHTAB, {"bot": Bot(), "token": "shtab-token"}, clear=True), \
                mock.patch.object(media, "text_logo", lambda *a, **k: self.tmp / "l.png"), \
                mock.patch.object(media, "watermark_video", lambda src, logo, dst, **k: (dst.parent.mkdir(parents=True, exist_ok=True), dst.write_bytes(b"v"), dst)[2]), \
                mock.patch.object(morning, "used_on", lambda *a: False):  # noqa
            morning.prepare_one(Bot(), self.db, CFG, ENV, r, at("22:00", THU), self.tmp / "w", upload=upload)
        self.assertEqual(tokens, ["shtab-token"])
        self.assertTrue(hub.is_morning_upload(self.db, 321, wait=0))
        self.assertFalse(hub.is_morning_upload(self.db, 999, wait=0))


class Shtab2310(unittest.TestCase):
    """23.10 (владелец): схема «штаб — общее, пульт — свой канал»."""

    def setUp(self):
        self.db = store.connect(":memory:")

    def test_shtab_overview_and_buttons(self):
        b = Bot()
        r = hub.shtab_handle(b, self.db, CFG, ENV, {"message": {"chat": {"id": 42, "type": "private"}, "from": {"id": 42},
                                                             "text": "/start"}})
        self.assertEqual(r, "overview")
        self.assertIn("Сегодня по всем каналам", b.calls[0][1]["text"])
        r = hub.shtab_handle(b, self.db, CFG, ENV, {"message": {"chat": {"id": 42, "type": "private"}, "from": {"id": 42},
                                                             "photo": [{"file_id": "x"}]}})
        self.assertEqual(r, "help")                                # пост в штаб — не публикуется, подсказка куда
        cq = {"id": "1", "from": {"id": 42}, "data": "ap:abc123:y",
              "message": {"chat": {"id": 42}, "message_id": 7, "text": "🤖 разрешить?"}}
        self.assertEqual(hub.shtab_handle(b, self.db, CFG, ENV, {"callback_query": cq}), "ap_y")
        self.assertEqual(store.kv_get(self.db, "autopilot_abc123"), "yes")
        self.assertIsNone(hub.shtab_handle(b, self.db, CFG, ENV, {"message": {"chat": {"id": -100777, "type": "channel"}}}))
        self.assertEqual(hub.shtab_handle(b, self.db, CFG, ENV, {"callback_query": {**cq, "from": {"id": 5}}}), "denied")

    def test_papa_hub_is_only_storage(self):
        self.assertIs(CFG.get("papa_hub_intake"), False)
        post = {"channel_post": {"chat": {"id": -100777, "title": "PAPA HUB"}, "message_id": 55, "text": "янги пост"}}
        from genplan import bots
        b = Bot()
        with mock.patch.dict(bots.REG, {"main": b}, clear=True):
            self.assertIsNone(hub.handle(b, self.db, CFG, ENV, post))
        self.assertEqual(self.db.execute("SELECT count(*) FROM materials").fetchone()[0], 0)

    def test_digest_preview_goes_to_own_pults(self):
        from genplan import bots, digest
        main, xo, sh = Bot(), Bot(), Bot()
        with mock.patch.dict(bots.REG, {"main": main, "xojaobod": xo}, clear=True), \
                mock.patch.dict(bots.SHTAB, {"bot": sh, "token": "s"}, clear=True):
            digest.preview(ENV, {"status": "READY", "news": 5}, main, {"status": "READY", "news": 4}, "ok")
        self.assertIn("выйдет сам", xo.calls[0][1]["text"])
        self.assertNotIn("КАТТА ДАВРА", xo.calls[0][1]["text"])
        self.assertIn("КАТТА ДАВРА", main.calls[0][1]["text"])
        self.assertIn("Ролики", sh.calls[0][1]["text"])
