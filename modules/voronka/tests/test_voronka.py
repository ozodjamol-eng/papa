import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from voronka import engine, joins, store  # noqa: E402
from voronka.api import ApiError  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def c(cid, uid, text, user=None):
    return {"id": cid, "text": text, "timestamp": "2026-10-15T11:00:00+0000",
            "from": {"id": uid, "username": user or f"u{uid}"}}


class FakeIG:
    user_id = "999"

    def __init__(self):
        self.media = [
            {"id": "M1", "timestamp": "2026-10-15T08:00:00+0000", "permalink": "https://www.instagram.com/p/AAA/", "comments_count": 3},
            {"id": "M2", "timestamp": "2026-10-14T08:00:00+0000", "permalink": "https://www.instagram.com/p/BBB/", "comments_count": 1},
            {"id": "OLD", "timestamp": "2026-10-01T08:00:00+0000", "permalink": "https://www.instagram.com/p/OLD/", "comments_count": 1},
        ]
        self.cm = {"M1": [], "M2": [c("x", "5", "hi")], "OLD": [c("o", "6", "hi")]}
        self.sent = []
        self.fail = None

    def recent_media(self, limit=10):
        return self.media

    def comments(self, mid, limit=50):
        return list(reversed(self.cm[mid]))  # API: новые первыми

    def private_reply(self, cid, text):
        if self.fail:
            raise self.fail
        self.sent.append((cid, text))
        return {"message_id": "m"}


CFG = {"mode": "all", "posts": ["https://www.instagram.com/p/AAA"], "dry_run": False, "max_per_hour": 30,
       "own_username": "paparazzi.uz", "dm_text": "салом {source}", "keywords": ["канал", "kanal"]}


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        self.ig = FakeIG()
        self.log = []

    def run1(self, cfg=CFG, now=NOW):
        return engine.run_once(self.ig, self.db, cfg, now, log=self.log.append)

    def test_backlog_skipped_then_new_answered_once_per_user(self):
        self.ig.cm["M1"] = [c("1", "10", "old comment")]
        s = self.run1()
        self.assertEqual((s["media"], s["skip"], s["sent"]), (1, 1, 0))  # только M1 из списка, старое не трогаем
        self.ig.cm["M1"] += [c("2", "11", "Зўр!"), c("3", "11", "яна"), c("4", "999", "own reply", "paparazzi.uz"),
                             c("5", "12", "नमस्ते")]
        s = self.run1()
        self.assertEqual((s["sent"], s["dup"], s["own"]), (2, 1, 1))
        self.assertEqual([x[0] for x in self.ig.sent], ["2", "5"])
        self.assertIn("ig-M1", self.ig.sent[0][1])
        self.assertEqual(self.run1()["new"], 0)  # повтор — ничего нового

    def test_old_media_and_unlisted_ignored(self):
        s = self.run1(dict(CFG, posts=["OLD", "M2"]))
        self.assertEqual(s["media"], 1)  # OLD старше 7 дней

    def test_keyword_mode_any_script_and_case(self):
        self.assertTrue(engine.wants_link("Менга КАНАЛ керак", dict(CFG, mode="keyword")))
        self.assertTrue(engine.wants_link("kanal pls", dict(CFG, mode="keyword")))
        self.assertFalse(engine.wants_link("зўр видео", dict(CFG, mode="keyword")))
        self.assertTrue(engine.wants_link("anything", CFG))

    def test_spam_filter(self):
        cfg = dict(CFG, spam_words=["vpn", "сервис", "заработ"])
        self.assertTrue(engine.is_spam("Отличный сервис — @takoe_vpn21", cfg))
        self.assertTrue(engine.is_spam("смотри t.me/xxx", cfg))
        self.assertFalse(engine.is_spam("@dostim qara 😂", cfg))  # друзей отмечают — это не спам
        self.assertFalse(engine.is_spam("Омийн🤲", cfg))

    def test_dry_run_sends_nothing(self):
        self.run1()
        self.ig.cm["M1"] = [c("2", "11", "a")]
        s = self.run1(dict(CFG, dry_run=True))
        self.assertEqual((s["dry"], self.ig.sent), (1, []))

    def test_hour_cap(self):
        self.run1()
        self.ig.cm["M1"] = [c(str(i), str(100 + i), "a") for i in range(5)]
        s = self.run1(dict(CFG, max_per_hour=3))
        self.assertEqual(s["sent"], 3)
        s = self.run1(dict(CFG, max_per_hour=3))
        self.assertEqual(s["sent"], 0)  # в этот час больше нельзя
        s = self.run1(dict(CFG, max_per_hour=3), NOW + dt.timedelta(hours=2))
        self.assertEqual(s["sent"], 2)

    def test_meta_rate_limit_pauses(self):
        self.run1()
        self.ig.cm["M1"] = [c("2", "11", "a"), c("3", "12", "b")]
        self.ig.fail = ApiError("messages", 613, "Calls to this api have exceeded the rate limit")
        s = self.run1()
        self.assertTrue(s["paused"])
        self.ig.fail = None
        self.assertTrue(self.run1(now=NOW + dt.timedelta(minutes=10))["paused"])
        self.assertEqual(self.run1(now=NOW + dt.timedelta(minutes=61))["sent"], 1)  # ошибочный не повторяется


class TestRetention(unittest.TestCase):
    def test_purge_after_90_days(self):
        db, ig = store.connect(":memory:"), FakeIG()
        engine.run_once(ig, db, CFG, NOW, log=lambda *_: None)
        ig.cm["M1"] = [c("2", "11", "a")]
        engine.run_once(ig, db, CFG, NOW, log=lambda *_: None)
        self.assertTrue(store.seen(db, "2"))
        ig.media = []
        engine.run_once(ig, db, CFG, NOW + dt.timedelta(days=91), log=lambda *_: None)
        self.assertFalse(store.seen(db, "2"))


class TestOnlyUsers(unittest.TestCase):
    def test_only_testers_answered_including_backlog(self):
        db, ig = store.connect(":memory:"), FakeIG()
        ig.cm["M1"] = [c("1", "10", "Омийн", "goldwaterandijon"), c("2", "11", "Омийн", "stranger")]
        cfg = dict(CFG, only_users=["GoldWaterAndijon"])
        s = engine.run_once(ig, db, cfg, NOW, log=lambda *_: None)
        self.assertEqual((s["sent"], [x[0] for x in ig.sent]), (1, ["1"]))
        self.assertFalse(store.seen(db, "2"))  # чужой не помечен — после теста обработается обычным порядком


class TestPublish(unittest.TestCase):
    def test_stats_without_personal_data(self):
        import json, os, tempfile
        from voronka.__main__ import publish_stats
        db, ig = store.connect(":memory:"), FakeIG()
        engine.run_once(ig, db, CFG, NOW, log=lambda *_: None)
        ig.cm["M1"] = [c("2", "11", "a", "secret_user")]
        engine.run_once(ig, db, CFG, dt.datetime.now(UTC), log=lambda *_: None)
        d = tempfile.mkdtemp()
        path = publish_stats(db, dict(CFG, page_url="https://x/"), ig.media[:1], d)
        raw = open(path, encoding="utf-8").read()
        data = json.loads(raw)
        self.assertEqual(data["mode"], "work")
        self.assertEqual(data["comments_24h"].get("sent"), 1)
        self.assertNotIn("secret_user", raw)
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o640")
        self.assertIsNone(publish_stats(db, CFG, [], os.path.join(d, "missing")))


class FakeBot:
    def __init__(self, fail_welcome=False):
        self.calls, self.fail_welcome = [], fail_welcome

    def call(self, method, **p):
        self.calls.append(method)
        if method == "sendMessage" and self.fail_welcome:
            raise ApiError(method, 403, "Forbidden")
        if method == "getUpdates":
            return [{"update_id": 7, "chat_join_request": {"chat": {"id": -100}, "from": {"id": 5}, "user_chat_id": 5,
                                                           "invite_link": {"name": "ig-M1"}}},
                    {"update_id": 8, "chat_join_request": {"chat": {"id": -200}, "from": {"id": 6}, "user_chat_id": 6}}]
        return {}


class TestJoins(unittest.TestCase):
    CFG = {"channels": [{"title": "T", "chat_id": -100, "welcome": "хуш келибсиз"}]}

    def test_welcome_before_approve_and_offset(self):
        db, b = store.connect(":memory:"), FakeBot()
        self.assertEqual(joins.poll_once(b, db, self.CFG, "t", log=lambda *_: None), 2)
        self.assertEqual(b.calls, ["getUpdates", "sendMessage", "approveChatJoinRequest"])  # чужой чат не тронут
        self.assertEqual(store.kv_get(db, "tg_offset"), "9")
        row = db.execute("SELECT invite_name, welcomed, approved FROM joins").fetchone()
        self.assertEqual(tuple(row), ("ig-M1", 1, 1))

    def test_welcome_failure_still_approves(self):
        db, b = store.connect(":memory:"), FakeBot(fail_welcome=True)
        joins.poll_once(b, db, self.CFG, "t", log=lambda *_: None)
        self.assertEqual(tuple(db.execute("SELECT welcomed, approved FROM joins").fetchone()), (0, 1))


if __name__ == "__main__":
    unittest.main()
