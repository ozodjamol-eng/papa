"""03.11: Хўжаобод Юкла — ҳавола → обуна → видео; хотира (file_id); MP3; пульт: ҳисобот, реклама, рассылка ✅ билан."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from yukla import bot as B, texts as T  # noqa: E402

OWNER = 1638232


class Api:
    def __init__(self, member="member", fail_member=False):
        self.calls, self.member, self.fail_member = [], member, fail_member

    def __call__(self, method, **p):
        self.calls.append((method, p))
        if method == "getChatMember":
            if self.fail_member:
                raise RuntimeError("getChatMember: member list is inaccessible")
            return {"status": self.member}
        return {"message_id": len(self.calls)}

    def to(self, chat):
        return [(m, p) for m, p in self.calls if p.get("chat_id") == chat]


class DL:
    def __init__(self, ok=True):
        self.ok, self.n = ok, 0

    def fetch(self, url, audio=False):
        self.n += 1
        if not self.ok:
            return None
        d = Path(tempfile.mkdtemp())
        f = d / ("a.mp3" if audio else "v.mp4")
        f.write_bytes(b"x" * 100)
        return f


def upload_fake(store):
    def up(method, chat, field, path, caption, kb):
        store.append((method, chat, field, caption, kb))
        return {field: {"file_id": f"FID-{field}-{len(store)}"}}
    return up


def msg(text=None, uid=42, **kw):
    m = {"message_id": 7, "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "first_name": "Али"}}
    if text is not None:
        m["text"] = text
    m.update(kw)
    return {"message": m}


def cb(data, uid=42):
    return {"callback_query": {"id": "q", "data": data, "from": {"id": uid}, "message": {"chat": {"id": uid}, "message_id": 1}}}


class T1(unittest.TestCase):
    def mk(self, **kw):
        self.api = Api(**{k: v for k, v in kw.items() if k in ("member", "fail_member")})
        self.ups = []
        self.dl = kw.get("dl") or DL()
        self.b = B.Bot(B.connect(":memory:"), self.api, [OWNER], downloader=self.dl, upload=upload_fake(self.ups), sync=True)
        return self.b

    def test_keys_and_platforms(self):
        self.assertEqual(B.norm_key("https://www.instagram.com/reel/DfPdNZNN75p/?xtok=anJs"), "ig:DfPdNZNN75p")
        self.assertEqual(B.norm_key("https://instagram.com/p/DfPdNZNN75p"), "ig:DfPdNZNN75p")
        self.assertEqual(B.norm_key("https://youtu.be/abcdefgh123?si=zz"), "yt:abcdefgh123")
        self.assertEqual(B.norm_key("https://www.youtube.com/watch?v=abcdefgh123&t=4"), "yt:abcdefgh123")
        self.assertEqual(B.platform_of("https://vm.tiktok.com/ZM123/"), "tiktok")
        self.assertEqual(B.platform_of("https://www.facebook.com/share/r/1Abc/"), "facebook")
        self.assertEqual(B.platform_of("https://fb.watch/abc123/"), "facebook")
        self.assertIsNone(B.platform_of("https://evil.com/instagram.com/reel/x"))

    def test_download_then_cache(self):
        b = self.mk()
        self.assertEqual(b.handle(msg("/start")), "start")
        self.assertEqual(b.handle(msg("https://www.instagram.com/reel/AAA111/?igsh=x")), "job")
        self.assertEqual(self.ups[0][0], "sendVideo")
        self.assertIn("a:", str(self.ups[0][4]))                                   # MP3 тугмаси
        self.assertEqual(b.handle(msg("https://instagram.com/reel/AAA111", uid=43)), "cache")   # бошқа одам — хотирадан
        self.assertEqual(self.dl.n, 1)                                              # Instagram'га қайта бормади
        self.assertIn(("sendVideo", "FID-video-1"), [(m, p.get("video")) for m, p in self.api.calls])

    def test_mp3_from_button_cached(self):
        b = self.mk()
        b.handle(msg("https://www.tiktok.com/@a/video/123"))
        kb = self.ups[0][4]["inline_keyboard"]
        rid = next(x["callback_data"] for row in kb for x in row if x.get("callback_data", "").startswith("a:"))
        self.assertEqual(b.handle(cb(rid)), "mp3")
        self.assertEqual(self.ups[-1][0], "sendAudio")
        b.handle(cb(rid, uid=44))
        self.assertIn("sendAudio", [m for m, p in self.api.calls])                 # иккинчиси — file_id билан

    def test_subscription_gate(self):
        b = self.mk(member="left")
        self.assertEqual(b.handle(msg("https://youtu.be/abcdefgh123")), "need_sub")
        self.assertEqual(self.ups, [])
        self.assertEqual(b.handle(cb("chk")), "not_yet")
        self.api.member = "member"
        self.assertEqual(b.handle(cb("chk")), "job")                               # обунадан кейин — ўша ҳавола
        self.assertEqual(len(self.ups), 1)

    def test_sub_check_unavailable_lets_through_and_warns_owner_once(self):
        b = self.mk(fail_member=True)
        self.assertEqual(b.handle(msg("https://youtu.be/abcdefgh123")), "job")
        b.handle(msg("https://youtu.be/zzzzzzzz999"))
        warns = [p for m, p in self.api.to(OWNER) if "админ" in (p.get("text") or "")]
        self.assertEqual(len(warns), 2)                                   # 2 канал — ҳар бирига бир марта

    def test_fail_and_bad_link(self):
        b = self.mk(dl=DL(ok=False))
        self.assertEqual(b.handle(msg("салом")), "bad")
        b.handle(msg("https://www.instagram.com/reel/BBB/"))
        self.assertTrue(any(T.FAIL in (p.get("text") or "") for m, p in self.api.calls))
        self.assertIn("❌ 1", b.stats())

    def test_downloader_crash_still_answers(self):
        """04.11: yt-dlp не запустился (PermissionError) — человек получает «не удалось», а не тишину."""
        class Boom(DL):
            def fetch(self, url, audio=False):
                raise PermissionError("yt-dlp")
        b = self.mk(dl=Boom())
        b.handle(msg("https://www.instagram.com/reel/CCC/"))
        self.assertTrue(any(T.FAIL in (p.get("text") or "") for m, p in self.api.calls))

    def test_real_downloader_missing_binary_returns_none(self):
        from yukla.bot import Downloader
        self.assertIsNone(Downloader("/nonexistent/yt-dlp").fetch("https://www.instagram.com/reel/X/"))

    def test_bottom_four_buttons(self):
        """04.11 владелец: «4 кнопки сверху, внизу эти двое» — пастда Chaqqon тугмалари + Намоз."""
        b = self.mk()
        b.handle(msg("/start"))
        kb = [p.get("reply_markup") for m, p in self.api.calls if m == "sendMessage"][-1]
        texts = [x["text"] for row in kb["keyboard"] for x in row]
        self.assertEqual(texts[:4], [T.GROUP_BTN, T.DESC_BTN, T.MP3_BTN, T.SAVE_BTN])
        self.assertIn(T.NAMAZ_BTN, texts)
        self.assertEqual(b.handle(msg(T.MP3_BTN)), "need_last")
        self.assertEqual(b.handle(msg(T.GROUP_BTN)), "group_how")
        b.handle(msg("https://www.instagram.com/reel/EEE/"))
        self.assertEqual(b.handle(msg(T.MP3_BTN)), "mp3")
        self.assertEqual(b.handle(msg(T.SAVE_BTN)), "save")
        self.assertEqual(b.handle(msg(T.DESC_BTN)), "desc")

    def test_owner_ad_and_broadcast_needs_confirm(self):
        b = self.mk()
        b.handle(msg("/start", uid=50)); b.handle(msg("/start", uid=51))
        self.assertEqual(b.handle(msg(T.O_AD, uid=OWNER)), "o_ad")
        self.assertEqual(b.handle(msg("Реклама: Шодиёна мебель @x", uid=OWNER)), "o_ad_set")
        b.handle(msg("https://www.instagram.com/reel/CCC/", uid=50))
        self.assertTrue(any("Шодиёна" in (p.get("text") or "") for m, p in self.api.calls if m == "sendMessage"))   # 04.11: реклама — отдельным сообщением после видео (как Chaqqon)
        self.assertEqual(b.handle(msg(T.O_SEND, uid=OWNER)), "o_send")
        self.assertEqual(b.handle(msg("Янгилик!", uid=OWNER)), "o_bc_preview")
        sent_before = [p for m, p in self.api.calls if m == "copyMessage" and p["chat_id"] in (50, 51)]
        self.assertEqual(sent_before, [])                                           # ✅ сиз ҳеч кимга кетмади
        self.assertIsNone(b.handle(cb("bc_yes", uid=50)))                           # бегона тасдиқлай олмайди
        b.broadcast = lambda oc, fc, mid: B.Bot.broadcast(b, oc, fc, mid, pause=0)
        self.assertEqual(b.handle(cb("bc_yes", uid=OWNER)), "bc_yes")
        sent = [p["chat_id"] for m, p in self.api.calls if m == "copyMessage" and p["chat_id"] != OWNER]
        self.assertEqual(sorted(set(sent)), [42, 50, 51] if 42 in sent else [50, 51])
        self.assertIn("📊", b.stats())

    def test_subs_default_two_channels_and_join_count(self):
        b = self.mk(member="left")
        b.handle(msg("https://youtu.be/abcdefgh123"))
        gate = [p for m, p in self.api.to(42) if "обуна" in (p.get("text") or "")][-1]
        links = [r[0].get("url") for r in gate["reply_markup"]["inline_keyboard"] if r[0].get("url")]
        self.assertEqual(links, ["https://t.me/kattadavrauz", "https://t.me/xojaobodcity24"])
        self.api.member = "member"
        b.handle(cb("chk"))
        joins = {r["chat"]: r["joins"] for r in b.q("SELECT * FROM subs")}
        self.assertEqual(joins, {"@kattadavrauz": 1, "@xojaobodcity24": 1})          # бот келтирган обуначи

    def test_owner_adds_sponsor_for_days_and_it_expires(self):
        b = self.mk()
        b.bot_id = 999
        self.assertEqual(b.handle(msg(T.O_SUBS, uid=OWNER)), "o_subs")
        self.assertEqual(b.handle(cb("sa", uid=OWNER)), "o_sub_ask")
        self.api.member = "left"                                          # бот админ эмас — қўшилмайди
        self.assertEqual(b.handle(msg("@homiy_kanal 3", uid=OWNER)), "o_sub_not_admin")
        self.api.member = "administrator"
        b.handle(cb("sa", uid=OWNER))
        self.assertEqual(b.handle(msg("@homiy_kanal 3", uid=OWNER)), "o_subs")
        r = b.q("SELECT * FROM subs WHERE chat='@homiy_kanal'", one=True)
        self.assertIsNotNone(r["until"])
        self.assertTrue(any("кўп" in (p.get("text") or "") for m, p in self.api.to(OWNER)))   # 3 канал — огоҳлантириш
        b.q("UPDATE subs SET until='2000-01-01' WHERE chat='@homiy_kanal'")
        self.assertEqual([x["chat"] for x in b.active_subs()], ["@kattadavrauz", "@xojaobodcity24"])
        self.assertTrue(any("муддати тугади" in (p.get("text") or "") for m, p in self.api.to(OWNER)))
        self.assertEqual(b.handle(cb("sd:@xojaobodcity24", uid=OWNER)), "o_subs")
        self.assertEqual([x["chat"] for x in b.active_subs()], ["@kattadavrauz"])
        self.assertIsNone(b.handle(cb("sd:@kattadavrauz", uid=42)))                   # бегона ўчира олмайди

    def test_owner_preview_as_user_and_sponsor_report(self):
        b = self.mk(member="left")
        self.assertEqual(b.handle(msg(T.O_PREVIEW, uid=OWNER)), "o_preview")
        self.assertEqual(b.handle(msg("https://youtu.be/abcdefgh123", uid=OWNER)), "need_sub")   # владелец — как все
        self.assertEqual(b.handle(msg(T.O_STATS, uid=OWNER)), "bad")                               # пульт ўчиқ
        self.assertEqual(b.handle(msg(T.O_BACK, uid=OWNER)), "o_panel")
        self.assertEqual(b.handle(msg(T.O_STATS, uid=OWNER)), "o_stats")
        b.q("UPDATE subs SET joins=1240 WHERE chat='@kattadavrauz'")
        self.assertEqual(b.handle(cb("sr:@kattadavrauz", uid=OWNER)), "o_sponsor_report")
        self.assertIn("1 240", self.api.to(OWNER)[-1][1]["text"])
        self.assertIsNone(b.handle(cb("sr:@kattadavrauz", uid=42)))

    def test_namaz_button(self):
        import datetime as dt, json as js
        f = Path(tempfile.mkdtemp()) / "n.json"
        f.write_text(js.dumps({"schedule": [{"day": "2026-10-29", "bomdod": "06:00", "peshin": "12:45", "asr": "15:40",
                                              "shom": "17:25", "xufton": "18:55"}]}), encoding="utf-8")
        t = B.namaz_text(f, dt.datetime(2026, 11, 3, 14, 0, tzinfo=B.TZ))
        self.assertIn("15:40", t); self.assertIn("➡️ 🌤 Аср", t); self.assertIn("Сешанба", t)
        self.assertIsNone(B.namaz_text(Path("/nope.json")))
        b = self.mk()
        b.namaz = lambda: t
        b.handle(msg("/start"))
        kb = self.api.to(42)[-1][1]["reply_markup"]["keyboard"]
        self.assertEqual(kb[-1], [{"text": T.NAMAZ_BTN}])                          # яшил тугма — пастда (04.11: устида 4 та Chaqqon тугмаси)
        self.assertEqual(b.handle(msg(T.NAMAZ_BTN)), "namaz")
        last = self.api.to(42)[-1][1]
        self.assertIn("15:40", last["text"])
        self.assertIn("XOJAOBODCITY24BOT", last["reply_markup"]["inline_keyboard"][0][0]["url"])

    def test_namaz_album_5_oboi_then_cached(self):
        d = Path(tempfile.mkdtemp())
        files = []
        for i in range(5):
            f = d / f"{i}.jpg"; f.write_bytes(b"x"); files.append(f)
        b = self.mk()
        b.oboi = lambda: ("2026-10-29_x", files, "🕌 ХЎЖАОБОД ТУМАНИ — НАМОЗ ВАҚТЛАРИ")
        sent = []
        b.upload_group = lambda chat, fs, cap: sent.append((chat, len(fs), cap)) or [
            {"photo": [{"file_id": f"s{i}", "file_size": 1}, {"file_id": f"L{i}", "file_size": 9}]} for i in range(5)]
        self.assertEqual(b.handle(msg(T.NAMAZ_BTN)), "namaz_oboi")
        self.assertEqual(sent[0][1], 5)
        self.assertEqual(b.handle(msg(T.NAMAZ_BTN, uid=43)), "namaz_oboi")       # иккинчиси — file_id, юкламасдан
        self.assertEqual(len(sent), 1)
        grp = [p for m, p in self.api.calls if m == "sendMediaGroup"][-1]
        self.assertEqual([x["media"] for x in grp["media"]], ["L0", "L1", "L2", "L3", "L4"])
        self.assertIn("НАМОЗ", grp["media"][0]["caption"])

    def test_group_link_downloads_other_text_ignored(self):
        """04.11: «👥 Гуруҳда ишлатиш» — гуруҳдаги ҳавола юкланади (обунасиз), оддий гапга жим."""
        b = self.mk(member="left")
        g = lambda t: {"message": {"message_id": 3, "chat": {"id": -5, "type": "supergroup"}, "from": {"id": 1}, "text": t}}
        self.assertIsNone(b.handle(g("салом ҳаммага")))
        self.assertEqual(b.handle(g("https://youtu.be/abcdefgh123")), "job")
        self.assertEqual(self.ups[-1][1], -5)
        waits = [p for m, p in self.api.calls if p.get("chat_id") == -5 and m == "sendMessage"]
        self.assertTrue(all("keyboard" not in (p.get("reply_markup") or {}) for p in waits))

    def test_chaqqon_buttons_desc_and_save(self):
        """04.11: под видео — Гуруҳда ишлатиш · Тавсиф · MP3 · Сақлаш."""
        b = self.mk()
        b.handle(msg("https://www.instagram.com/reel/DDD/"))
        kb = self.ups[0][4]["inline_keyboard"]
        flat = [x for row in kb for x in row]
        self.assertTrue(any("startgroup" in (x.get("url") or "") for x in flat))
        d = next(x["callback_data"] for x in flat if x.get("callback_data", "").startswith("d:"))
        s_ = next(x["callback_data"] for x in flat if x.get("callback_data", "").startswith("s:"))
        b.q("UPDATE cache SET descr='Асл матн <b>'")
        self.assertEqual(b.handle(cb(d)), "desc")
        self.assertTrue(any("Асл матн &lt;b&gt;" in (p.get("text") or "") for m, p in self.api.calls))
        self.assertEqual(b.handle(cb(s_)), "save")
        self.assertEqual(b.handle(msg("/saqlangan")), "saved")
        self.assertEqual(b.handle(cb("x")), "del")
        self.assertIn("deleteMessage", [m for m, p in self.api.calls])


if __name__ == "__main__":
    unittest.main()
