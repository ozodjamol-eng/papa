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
        rid = self.ups[0][4]["inline_keyboard"][0][0]["callback_data"]
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
        self.assertEqual(len(warns), 1)

    def test_fail_and_bad_link(self):
        b = self.mk(dl=DL(ok=False))
        self.assertEqual(b.handle(msg("салом")), "bad")
        b.handle(msg("https://www.instagram.com/reel/BBB/"))
        self.assertTrue(any(T.FAIL in (p.get("text") or "") for m, p in self.api.calls))
        self.assertIn("❌ 1", b.stats())

    def test_owner_ad_and_broadcast_needs_confirm(self):
        b = self.mk()
        b.handle(msg("/start", uid=50)); b.handle(msg("/start", uid=51))
        self.assertEqual(b.handle(msg(T.O_AD, uid=OWNER)), "o_ad")
        self.assertEqual(b.handle(msg("Реклама: Шодиёна мебель @x", uid=OWNER)), "o_ad_set")
        b.handle(msg("https://www.instagram.com/reel/CCC/", uid=50))
        self.assertIn("Шодиёна", self.ups[-1][3])                                  # реклама видео остида
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

    def test_groups_ignored(self):
        b = self.mk()
        self.assertIsNone(b.handle({"message": {"message_id": 1, "chat": {"id": -5, "type": "group"},
                                                "from": {"id": 1}, "text": "https://youtu.be/abcdefgh123"}}))


if __name__ == "__main__":
    unittest.main()
