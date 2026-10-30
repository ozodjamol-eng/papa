"""30.10: наши каналы по дням недели (для тематических дней)."""
import datetime as dt
import unittest

from razvedka import analyze, store

NOW = dt.datetime(2026, 10, 30, 12, 0, tzinfo=dt.timezone.utc)


class TestOwnWeek(unittest.TestCase):
    def setUp(self):
        self.db = store.connect(":memory:")
        store.upsert_channel(self.db, {"id": 1, "username": "kattadavrauz", "title": "КАТТА ДАВРА", "folder": "свои",
                                       "is_own": 1, "subscribers": 2000}, NOW.isoformat())
        store.upsert_channel(self.db, {"id": 2, "username": "xojaobodcity24", "title": "Хўжаобод", "folder": "свои",
                                       "is_own": 1, "subscribers": 6500}, NOW.isoformat())
        store.upsert_channel(self.db, {"id": 3, "username": "rival", "title": "Rival", "folder": "x",
                                       "is_own": 0, "subscribers": 9000}, NOW.isoformat())
        n = 0
        for i in range(1, 27 * 4):                       # каждые 6 ч, 27 дней
            d = NOW - dt.timedelta(hours=6 * i)
            sunday = (d + dt.timedelta(hours=5)).weekday() == 6
            for cid, views, reac in ((1, 400 if sunday else 200, 0), (2, None, 20 if sunday else 10), (3, 900, 1)):
                n += 1
                store.upsert_post(self.db, {"channel_id": cid, "msg_id": n, "date_utc": d.isoformat(timespec="seconds"),
                                            "views": views, "forwards": 0, "replies": 0, "reactions": reac,
                                            "media": "video", "text": "матн", "text_len": 4, "links": 0,
                                            "is_forward": 0, "grp": None}, NOW.isoformat())

    def test_own_only_and_sunday_strong(self):
        res = {o["title"]: o for o in analyze.own_week(self.db, NOW)}
        self.assertEqual(set(res), {"КАТТА ДАВРА", "Хўжаобод"})        # конкурент не входит
        self.assertEqual(res["КАТТА ДАВРА"]["metric"], "просмотры")
        self.assertEqual(res["Хўжаобод"]["metric"], "реакции")           # группа — реакции
        for o in res.values():
            sun = o["days"][6]["strength"]
            mon = o["days"][0]["strength"]
            self.assertGreater(sun, mon)

    def test_report_and_card_render(self):
        a = analyze.analyze(self.db, 7, NOW)
        from razvedka import cards, report
        self.assertIn("НАШИ КАНАЛЫ ПО ДНЯМ", report.render(a))
        png = cards.card_leaders(a)
        self.assertTrue(png[:4] == b"\x89PNG" or png[:3] == b"\xff\xd8\xff")


if __name__ == "__main__":
    unittest.main()
