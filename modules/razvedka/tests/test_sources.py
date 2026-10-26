"""26.10: отбор каналов-источников — счёт, отсев, темы, квоты, таблица."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import sources  # noqa: E402

NOW = dt.datetime(2026, 10, 26, 6, 0, tzinfo=dt.timezone.utc)


def post(h, views=1000, text="Янгилик матни", media=True, ad=False):
    return {"date": NOW - dt.timedelta(hours=h), "views": views, "text": text, "media": media, "ad": ad}


def row(i, theme, views=20000, clean=1.0, ad=0.05, per_day=20):
    return {"id": i, "title": f"Канал {i}", "username": f"k{i}", "theme": theme, "median_views": views, "per_day": per_day,
            "ad_share": ad, "cyr_share": 0.9, "checked": 3, "clean_n": round(clean * 3), "clean": clean,
            "score": sources.score({"median_views": views, "ad_share": ad, "per_day": per_day}, clean), "why": ""}


class TestSources(unittest.TestCase):
    def test_stats(self):
        p = [post(5, 2000), post(30, 4000, ad=True), post(50, 6000, media=False, text="Yangilik matni lotinda"),
             post(24 * 9, 99999)]                              # старше 7 дней — не считается
        s = sources.stats(p, NOW)
        self.assertEqual((s["posts"], s["median_views"], s["ad_share"]), (3, 4000, 0.33))
        self.assertEqual((s["media_share"], s["cyr_share"]), (0.67, 0.67))

    def test_eligible(self):
        base = {"per_day": 5, "median_views": 3000, "ad_share": 0.1, "media_share": 0.8}
        self.assertEqual(sources.eligible(base), "")
        self.assertEqual(sources.eligible({**base, "ad_share": 0.5}), "много рекламы")   # Водий бозор и т.п.
        self.assertEqual(sources.eligible({**base, "per_day": 0.2}), "редко пишет")
        self.assertEqual(sources.eligible({**base, "median_views": 100}), "мало просмотров")

    def test_score_clean_matters_most(self):
        s = {"median_views": 90000, "ad_share": 0.05, "per_day": 60}
        self.assertGreater(sources.score({**s, "median_views": 20000}, 1.0), sources.score(s, 1 / 3))
        self.assertEqual(sources.score(s, None), 0.0)

    def test_theme_priority(self):
        self.assertEqual(sources.theme(["humor", "news"]), "news")
        self.assertEqual(sources.theme(["live_music"]), "music")
        self.assertEqual(sources.theme(["recipes"]), "food")
        self.assertIsNone(sources.theme(["ads_market"]))

    def test_shortlist_quota_dirty_out_and_15_total(self):
        rows = [row(i, "news", 10000 + i) for i in range(10)] + [row(20, "news", 999999, clean=1 / 3)]
        rows += [row(30 + i, "humor") for i in range(3)] + [row(40, "music"), row(41, "faith")]
        sl = sources.shortlist(rows)
        self.assertEqual(len(sl["news"]["top"]), 6)
        self.assertNotIn(20, [r["id"] for r in sl["news"]["top"]])           # чужое лого — не в списке
        self.assertEqual(len(sl["news"]["spare"]), 2)
        self.assertEqual(len(sl["humor"]["top"]), 2)
        self.assertEqual(sum(q[2] for q in sources.QUOTAS), 15)

    def test_render(self):
        rows = [row(1, "news"), row(2, "news", clean=0.0)]
        rows[0]["subscribers"] = 1159335
        t = sources.render(sources.shortlist(rows), rows, "26.10.2026 09:00", 5)
        self.assertIn("1.16 млн", t)
        self.assertIn("🧼 3/3", t)
        self.assertIn("с чужим логотипом", t)
        self.assertIn("чистых каналов этой темы нет", t)                    # пустая тема видна владельцу

    def test_whitelist_for_channels_and_block(self):
        rows = [row(1, "news"), row(2, "music"), row(3, "faith"), row(4, "humor")]
        rows[3]["username"] = "ShohonaKulgu"                                 # своё лого на всех видео — никогда
        wl = sources.whitelist(sources.shortlist(rows), "26.10")
        self.assertEqual(sources.ids_for(wl, "xojaobod"), [1, 3])
        self.assertEqual(sources.ids_for(wl, "paparazzi"), [2])
        self.assertEqual(sources.ids_for(wl, "davra"), [1])                  # Маънавият — только Хўжаобод
        self.assertEqual(sources.ids_for(None, "davra"), [])                 # нет списка — куратор по папкам
        wl2 = sources.whitelist(sources.shortlist([row(1, "news"), row(5, "humor")]), "26.10")
        self.assertEqual(sources.ids_for(wl2, "paparazzi"), [])              # нет жонли ижро — PaparazziUZ по папке

    def test_whitelist_file_roundtrip(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.assertIsNone(sources.load_whitelist(d / "whitelist.json"))
        (d / "whitelist.json").write_text('{"themes": {"news": [{"id": 7, "title": "T"}]}}', encoding="utf-8")
        self.assertEqual(sources.ids_for(sources.load_whitelist(d / "whitelist.json"), "davra"), [7])

    def test_check_order_round_robin_and_complete(self):
        good = [dict(row(i, "news", 1000 * i), clean=None) for i in range(1, 20)] + [dict(row(50, "humor"), clean=None)]
        order = sources.check_order(good)
        self.assertEqual(order[0]["id"], 19)                                 # сильнейшие новости первыми
        self.assertEqual(order[1]["id"], 50)                                 # и сразу другая тема — по кругу
        self.assertEqual(len([r for r in order if r["theme"] == "news"]), 14)  # квота×2+2
        sl = sources.shortlist([row(i, "news") for i in range(6)])
        self.assertFalse(sources.complete_list(sl))                          # других тем нет — список не полный


if __name__ == "__main__":
    unittest.main()
