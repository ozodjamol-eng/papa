import asyncio
import datetime as dt
import sqlite3
import unittest
from types import SimpleNamespace as NS

from razvedka import pain

NOW = dt.datetime(2026, 10, 16, 12, 0, tzinfo=dt.timezone.utc)


class TestClassify(unittest.TestCase):
    def test_kinds(self):
        c = pain.classify
        self.assertEqual(c("Қаерда сотиб олиш мумкин?"), "question")
        self.assertEqual(c("Narxi qancha ekan"), "request")            # «narxi» — запрос цены
        self.assertEqual(c("Где посмотреть полную версию?"), "question")
        self.assertEqual(c("Сделайте пожалуйста про погоду"), "request")
        self.assertEqual(c("Qo’shing iltimos yana shunday video"), "request")   # типографский апостроф
        self.assertEqual(c("Надоели эти новости, хватит уже"), "complaint")
        self.assertEqual(c("Juda zerikarli, yomon"), "complaint")

    def test_noise(self):
        for t in ("🔥🔥🔥", "+", "Супер", "Zo'r", "", "👏👏 ✅", "Скидка 50% тел +998 90 123 45 67", "https://a.uz смотри все"):
            self.assertEqual(pain.classify(t), "noise", t)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        pain.connect(self.db)

    def test_save_dedup_summary_no_user_fields(self):
        items = [{"id": 1, "date": NOW.isoformat(), "text": "Қаерда кўриш мумкин?"},
                 {"id": 2, "date": NOW.isoformat(), "text": "🔥🔥"},
                 {"id": 3, "date": NOW.isoformat(), "text": "Надоело, хватит уже"}]
        self.assertEqual(pain.save(self.db, 10, 5, items, NOW), 3)
        self.assertEqual(pain.save(self.db, 10, 5, items, NOW), 0)       # повтор не дублируется
        s = pain.summary(self.db)
        self.assertEqual((s["total"], s["useful"], s["useful_pct"]), (3, 2, 67))
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(comments)")}
        self.assertFalse(cols & {"user_id", "username", "from_id", "name"})   # людей не храним

    def test_purge_30_days(self):
        old = (NOW - dt.timedelta(days=31)).isoformat()
        pain.save(self.db, 1, 1, [{"id": 1, "date": old, "text": "Қаерда кўриш мумкин?"},
                                  {"id": 2, "date": NOW.isoformat(), "text": "Қаерда сотилади?"}], NOW)
        self.assertEqual(pain.purge(self.db, NOW), 1)
        self.assertEqual(pain.summary(self.db)["total"], 1)

    def test_long_text_trimmed(self):
        pain.save(self.db, 1, 1, [{"id": 1, "date": NOW.isoformat(), "text": "Қаерда? " + "а" * 900}], NOW)
        self.assertLessEqual(len(self.db.execute("SELECT text FROM comments").fetchone()[0]), 500)


class FakeClient:
    def __init__(self, posts, comments, fail=()):
        self.posts, self.comments, self.fail = posts, comments, set(fail)

    async def iter_messages(self, ent, limit=None, reply_to=None, wait_time=None):
        if reply_to is not None:
            if reply_to in self.fail:
                raise RuntimeError("comments off")
            for m in self.comments.get(reply_to, []):
                yield m
        else:
            for m in self.posts:
                yield m


def post(i, replies, age_days=1):
    return NS(id=i, action=None, date=NOW - dt.timedelta(days=age_days), views=1000, replies=NS(replies=replies))


def cm(i, text):
    return NS(id=i, message=text, date=NOW, reactions=None)


class TestCollect(unittest.TestCase):
    def test_only_strong_fresh_posts_and_comments_off_tolerated(self):
        posts = [post(1, 10), post(2, 1), post(3, 8, age_days=9), post(4, 5)]
        cl = FakeClient(posts, {1: [cm(1, "Қаерда кўриш мумкин?"), cm(2, "🔥")]}, fail={4})
        ent = NS(id=77, username="x")
        strong = asyncio.run(pain.strong_posts(cl, ent, NOW))
        self.assertEqual([m.id for m in strong], [1, 4])                # слабый и старый отброшены
        self.assertEqual(len(asyncio.run(pain.comments_of(cl, ent, 1))), 2)
        with self.assertRaises(RuntimeError):
            asyncio.run(pain.comments_of(cl, ent, 4))


if __name__ == "__main__":
    unittest.main()
