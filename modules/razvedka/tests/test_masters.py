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


if __name__ == "__main__":
    unittest.main()
