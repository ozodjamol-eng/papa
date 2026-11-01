import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from razvedka import masters

NOW = dt.datetime(2026, 11, 2, 10, 0, tzinfo=masters.TZ)
CID = "UC" + "a" * 22

FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
 <title>OBSION</title><author><name>OBSION</name></author>
 <entry><yt:videoId>new1</yt:videoId><title>Новый урок</title><published>2026-10-30T10:00:00+00:00</published></entry>
 <entry><yt:videoId>sh1</yt:videoId><title>коротко #shorts</title><published>2026-10-31T10:00:00+00:00</published></entry>
 <entry><yt:videoId>old1</yt:videoId><title>Старый</title><published>2026-08-01T10:00:00+00:00</published></entry>
</feed>"""


def fake_fetch(url, timeout=30):
    if "feeds/videos.xml" in url:
        return FEED
    return 'xx "channelId":"%s" yy' % CID


def ok_post(text="🎓 OBSION — «Новый урок»\nСуть: …\nВердикт: 🧪 в проверку", tokens=40000):
    calls = []

    def post(model, body, key, timeout=600):
        calls.append(body)
        return {"candidates": [{"content": {"parts": [{"text": text}]}}],
                "usageMetadata": {"promptTokenCount": tokens}}
    post.calls = calls
    return post


class TestMasters(unittest.TestCase):
    def test_resolve_by_video_and_query(self):
        self.assertEqual(masters.resolve({"name": "x", "video": "abc"}, fake_fetch), CID)
        self.assertEqual(masters.resolve({"name": "x", "query": "q"}, fake_fetch), CID)
        self.assertEqual(masters.resolve({"name": "x", "channel": "UCzzz"}, fake_fetch), "UCzzz")
        with self.assertRaises(masters.MastersError):
            masters.resolve({"name": "x", "video": "abc"}, lambda u, timeout=30: "<html>consent</html>")

    def test_feed_and_pick_skip_shorts_old_seen(self):
        author, vids = masters.parse_feed(FEED)
        self.assertEqual(author, "OBSION")
        m = {"name": "OBSION"}
        chosen = masters.pick([(m, vids)], set(), NOW.date())
        self.assertEqual([v["id"] for _, v in chosen], ["new1"])
        self.assertEqual(masters.pick([(m, vids)], {"new1"}, NOW.date()), [])

    def test_pick_round_robin_and_limit(self):
        a = [{"id": f"a{i}", "title": "t", "published": "2026-10-2%d" % i} for i in range(5)]
        b = [{"id": "b0", "title": "t", "published": "2026-10-20"}]
        chosen = masters.pick([({"name": "A"}, a), ({"name": "B"}, b)], set(), NOW.date(), limit=3)
        self.assertEqual([v["id"] for _, v in chosen], ["a4", "b0", "a3"])

    def test_watch_sends_youtube_uri_and_guards_unwatched(self):
        post = ok_post()
        text, tokens = masters.watch({"name": "OBSION"}, {"id": "new1", "title": "T"}, "k", post)
        part = post.calls[0]["contents"][0]["parts"][0]
        self.assertEqual(part["file_data"]["file_uri"], "https://www.youtube.com/watch?v=new1")
        self.assertGreater(tokens, masters.MIN_VIDEO_TOKENS)
        with self.assertRaises(masters.MastersError):     # мало токенов = видео не смотрели
            masters.watch({"name": "O"}, {"id": "x", "title": "T"}, "k", ok_post(tokens=500))
        with self.assertRaises(masters.MastersError):
            masters.watch({"name": "O"}, {"id": "x", "title": "T"}, "k", ok_post(text="ВИДЕО НЕДОСТУПНО"))

    def test_run_writes_lesson_queue_and_skips_next_time(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(masters, "MASTERS", [{"name": "OBSION", "video": "Et9", "why": "моушн"}]), \
                mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k", "PAPA_GEMINI_DIR": d}):
            text = masters.run(Path(d), now=NOW, fetch=fake_fetch, post=ok_post())
            self.assertIn("УРОКИ МАСТЕРОВ", text)
            self.assertIn("watch?v=new1", text)
            q = json.loads((Path(d) / "navyki-queue.json").read_text())
            self.assertEqual(q[0]["topic"], "Урок мастера")
            self.assertTrue((Path(d) / "masters" / "new1.txt").exists())
            text2 = masters.run(Path(d), now=NOW, fetch=fake_fetch, post=ok_post())
            self.assertIn("Новых уроков", text2)

    def test_messages_split(self):
        text = "🎓 УРОКИ\n\n" + "\n\n".join("🎓 урок %d\n" % i + "строка\n" * 300 for i in range(3))
        parts = masters.messages(text)
        self.assertTrue(all(len(p) <= 3900 for p in parts))
        self.assertGreaterEqual(len(parts), 3)


class FakeMsg:
    def __init__(self, i, text, date):
        self.id, self.message, self.date = i, text, date


class FakeClient:
    def __init__(self, msgs):
        self.msgs, self.min_ids = msgs, []

    async def get_entity(self, u):
        return u

    def iter_messages(self, ent, limit=40, min_id=0, wait_time=1):
        self.min_ids.append(min_id)
        msgs = [m for m in self.msgs if m.id > min_id]

        async def gen():
            for m in sorted(msgs, key=lambda m: -m.id):
                yield m
        return gen()


class TestTgMasters(unittest.TestCase):
    def test_read_first_week_then_only_new_and_report(self):
        import asyncio
        d0 = dt.datetime(2026, 10, 31, 9, 0, tzinfo=dt.timezone.utc)
        old = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.timezone.utc)
        c = FakeClient([FakeMsg(60, "Инструменты: TubeTranscript", d0), FakeMsg(59, "", d0), FakeMsg(10, "старое", old)])
        with tempfile.TemporaryDirectory() as d:
            found = asyncio.run(masters.read_tg(c, Path(d), NOW))
            self.assertEqual([p["id"] for p in found[0][1]], [60])          # пустой и старше недели — мимо
            prompts = []
            text = masters.run_tg(Path(d), found, NOW, ask=lambda p: prompts.append(p) or "📡 Лаб — неделя\n1) TubeTranscript → ✅")
            self.assertIn("КАНАЛЫ ПРАКТИКОВ", text)
            self.assertIn("t.me/laboratornaya/60", prompts[0])
            self.assertEqual(json.loads((Path(d) / "navyki-queue.json").read_text())[0]["topic"], "Канал практика")
            found2 = asyncio.run(masters.read_tg(c, Path(d), NOW))
            self.assertEqual(c.min_ids[-1], 60)
            self.assertEqual(found2[0][1], [])
            self.assertIn("Новых постов нет", masters.run_tg(Path(d), found2, NOW, ask=lambda p: "x"))

    def test_unreadable_channel_noted(self):
        text = masters.run_tg(Path(tempfile.mkdtemp()), [({"name": "X", "username": "x", "error": "ValueError"}, [])], NOW,
                              ask=lambda p: "x")
        self.assertIn("не прочитан", text)


if __name__ == "__main__":
    unittest.main()
