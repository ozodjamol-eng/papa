"""30.10: вечерний пул — отбор Pixabay и фон по кругу."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from razvedka import evening


def hit(i, tags="sunset, sky", dur=20, w=1920, h=1080):
    return {"id": i, "tags": tags, "duration": dur,
            "videos": {"medium": {"url": f"https://x/{i}.mp4", "width": w, "height": h}}}


class TestEvening(unittest.TestCase):
    def test_no_people_and_duration(self):
        self.assertTrue(evening.ok(hit(1)))
        self.assertFalse(evening.ok(hit(2, tags="sunset, woman, beach")))
        self.assertFalse(evening.ok(hit(3, dur=4)))
        self.assertFalse(evening.ok(hit(4, w=640, h=360)))           # мелкое — нет

    def test_vertical_preferred(self):
        h = {"id": 5, "tags": "sky", "duration": 15, "videos": {
            "large": {"url": "L", "width": 3840, "height": 2160},
            "medium": {"url": "M", "width": 1080, "height": 1920}}}
        self.assertEqual(evening.best_file(h)["url"], "M")

    def test_season_and_pick_rotates(self):
        self.assertEqual(evening.season(dt.date(2026, 10, 30)), "kuz")
        self.assertEqual(evening.season(dt.date(2026, 12, 1)), "qish")
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for n in (1, 2, 3):
                (d / f"kuz-{n}.mp4").write_bytes(b"x")
            (d / "qish-9.mp4").write_bytes(b"x")
            a = evening.pick(dt.date(2026, 10, 30), d)
            b = evening.pick(dt.date(2026, 10, 31), d)
            self.assertNotEqual(a, b)
            self.assertTrue(a.name.startswith("kuz-"))
            self.assertIsNone(evening.pick(dt.date(2026, 10, 30), d / "нет"))


if __name__ == "__main__":
    unittest.main()


class FakeMsg:
    def __init__(self, i):
        self.id, self.video = i, True


class FakeClient:
    def __init__(self):
        self.msgs, self.n = [], 100

    async def iter_messages(self, ent, limit=200):
        for m in reversed(self.msgs):
            yield m

    async def send_file(self, ent, path, caption=None, supports_streaming=True):
        self.n += 1
        m = FakeMsg(self.n)
        self.msgs.append(m)
        return m

    async def download_media(self, m, file=None):
        raise AssertionError("не должен скачивать — файл уже на диске")


class TestEveningRun(unittest.TestCase):
    def test_fills_whole_season_once(self):
        import asyncio
        import os
        import shutil
        from unittest import mock
        with tempfile.TemporaryDirectory() as t:
            out, stdir = Path(t) / "out", Path(t) / "st"
            hits = {q: [hit(i * 100 + k) for k in range(20)] for i, q in enumerate(evening.QUERIES["kuz"])}
            fake = FakeClient()

            async def ent(c):
                return "pool"

            def to_v(src, dst):
                Path(dst).write_bytes(b"v")
                return dst
            now = dt.datetime(2026, 11, 20, 15, 30, tzinfo=dt.timezone(dt.timedelta(hours=5)))
            with mock.patch.object(evening, "OUT", out), mock.patch.object(evening, "pool_entity", ent), \
                    mock.patch.object(evening, "search", lambda key, q: hits[q]), \
                    mock.patch.object(evening, "to_vertical", to_v), \
                    mock.patch.object(evening.urllib.request, "urlretrieve", lambda u, p: Path(p).write_bytes(b"r")), \
                    mock.patch.object(evening.asyncio, "sleep", mock.AsyncMock()), \
                    mock.patch.dict(os.environ, {"PIXABAY_API_KEY": "k"}):
                r = asyncio.run(evening.run(fake, stdir, now, log=lambda *_: None))
                self.assertEqual(r["добавлено"], 2 * 11)          # 11 дней до 1 декабря × 2 канала
                self.assertEqual(r["фонов сезона"], 22)
                r2 = asyncio.run(evening.run(fake, stdir, now, log=lambda *_: None))
                self.assertEqual(r2["добавлено"], 0)              # уже полно — ничего не добирает
            shutil.rmtree(out, ignore_errors=True)
