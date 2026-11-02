import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genplan import marker  # noqa: E402

CH = {"username": "kattadavrauz", "title": "КАТТА ДАВРА"}


def row(**kw):
    base = {"has_media": 1, "rubric": "Ҳажвия", "source": "РАЗВЛЕКАТЕЛЬНО",
            "media": json.dumps([{"type": "video", "file_id": "x"}])}
    base.update(kw)
    return base


class MarkerTest(unittest.TestCase):
    def test_marks_single_video(self):
        assert marker.decide(CH, row())[0] == "video"


    def test_marks_photo(self):
        assert marker.decide(CH, row(media=json.dumps([{"type": "photo", "file_id": "x"}])))[0] == "photo"


    def test_never_ads_and_muftiy(self):
        assert marker.decide(CH, row(rubric="Реклама"))[0] is None
        assert marker.decide(CH, row(rubric="Муфтий минбари"))[0] is None


    def test_not_twice_and_not_text_and_not_album(self):
        assert marker.decide(CH, row(source="fabrika"))[0] is None
        assert marker.decide(CH, row(has_media=0))[0] is None
        two = json.dumps([{"type": "photo", "file_id": "a"}, {"type": "photo", "file_id": "b"}])
        assert marker.decide(CH, row(media=two))[0] is None


    def test_mark_text(self):
        assert marker.mark_text(CH) == "@kattadavrauz"
        assert marker.mark_text({**CH, "watermark": "@KATTADAVRAUZ"}) == "@KATTADAVRAUZ"


class CandidatesTest(unittest.TestCase):
    def test_queue_first_then_stock_skip_marked_ads_textless(self):
        import datetime as dt
        import tomllib
        from genplan import plan, store
        cfg = tomllib.loads((Path(__file__).resolve().parent.parent / "config.toml").read_text(encoding="utf-8"))
        db = store.connect(":memory:")
        vid = [{"type": "video", "file_id": "f"}]
        now = dt.datetime.now(plan.TZ)
        a = store.add_material(db, -1, 1, "Кулгили видео матни", True, vid)
        store.update(db, a, channel="davra", status="draft", stock=1, rubric="Ҳажвия")
        b = store.add_material(db, -1, 2, "Фойдали видео матни", True, vid)
        store.update(db, b, channel="davra", status="queued", rubric="Фойдали видео",
                     scheduled_at=(now + dt.timedelta(hours=2)).isoformat())
        c = store.add_material(db, -1, 3, "Реклама матни узун", True, vid)
        store.update(db, c, channel="davra", status="queued", rubric="Реклама")
        d = store.add_material(db, -1, 4, "", True, vid)               # без текста — подпись при выходе
        store.update(db, d, channel="davra", status="queued", rubric="Ҳажвия")
        e = store.add_material(db, -1, 5, "Уже помечен матни", True, vid)
        store.update(db, e, channel="davra", status="queued", rubric="Ҳажвия")
        store.kv_set(db, f"marked_{e}", "1")
        ids = [r["id"] for r in marker.candidates(db, cfg, now)]
        self.assertEqual(ids, [b, a])
        self.assertEqual(marker.candidates(db, {**cfg, "marker": {"on": False}}, now), [])


class GrantTest(unittest.TestCase):
    """02.11: бот канала не был админом полки «· ГОТОВО» — посты падали «chat not found». Права доставляются."""

    def test_grant_fixes_missing_admin(self):
        import asyncio
        from genplan import marker
        calls = []

        class P:
            def __init__(self, status):
                self.status = status

            def http(self, method, payload):
                if method == "getMe":
                    return {"ok": True, "result": {"id": 7, "username": "PapaGenplanBot"}}
                if self.status:
                    return {"ok": True, "result": {"status": self.status}}
                return {"ok": False, "description": "Bad Request: chat not found"}

        bots = {}

        class Acc:
            _fake = True

            async def get_entity(self, x):
                return x

            async def __call__(self, req):
                calls.append(req)
                bots["bot"].status = "administrator"           # Telegram принял назначение

        cfg = {"channels": {"davra": {"publisher": "bot"}}}
        marker._GRANTED.clear()
        bots["bot"] = P(None)
        self.assertTrue(asyncio.run(marker.grant(Acc(), cfg, bots, "davra", -1001, log=lambda *_: None)))
        self.assertEqual(len(calls), 1)                       # права доставлены и проверены

        class Deaf(Acc):
            async def __call__(self, req):
                calls.append(req)                             # назначение «прошло», но бот так и не админ (Давра 02.11)
        marker._GRANTED.clear()
        bots["bot"] = P(None)
        self.assertFalse(asyncio.run(marker.grant(Deaf(), cfg, bots, "davra", -1001, log=lambda *_: None)))
        calls.clear(); calls.append(None)
        marker._GRANTED.clear()
        self.assertTrue(asyncio.run(marker.grant(Acc(), cfg, {"bot": P("administrator")}, "davra", -1001, log=lambda *_: None)))
        self.assertEqual(len(calls), 1)                       # уже админ — ничего не трогаем
