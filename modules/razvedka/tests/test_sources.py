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


def row(i, theme, views=20000, clean=1.0, ad=0.05, per_day=20, ch="davra"):
    chs = [ch] if isinstance(ch, str) else list(ch)
    return {"id": i, "title": f"Канал {i}", "username": f"k{i}", "theme_by": {c: theme for c in chs}, "for": chs,
            "median_views": views, "per_day": per_day,
            "ad_share": ad, "cyr_share": 0.9, "checked": 3, "clean_n": round(clean * 3), "clean": clean,
            "score": sources.score({"median_views": views, "ad_share": ad, "per_day": per_day}, clean), "why": ""}


FOUND = {"xojaobod": "XOJAOBOD CITY", "davra": "KATTA DAVRA", "paparazzi": "Paparazzi UZ"}


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

    def test_theme_priority_and_channel_rubrics(self):
        self.assertEqual(sources.theme(["humor", "news"]), "news")
        self.assertEqual(sources.theme(["live_music"]), "music")
        self.assertEqual(sources.theme(["recipes"]), "food")
        self.assertIsNone(sources.theme(["ads_market"]))
        pap = dict((x[0], x[3]) for x in sources.PROFILES)["paparazzi"]
        self.assertEqual(sources.theme(["news", "humor"], pap), "humor")      # новостей у PaparazziUZ нет
        self.assertIsNone(sources.theme(["religion"], pap))

    def test_shortlist_per_channel_only_own_folder(self):
        rows = [row(i, "news", 10000 + i, ch="xojaobod") for i in range(8)] + [row(20, "news", 999999, clean=1 / 3, ch="xojaobod")]
        rows += [row(30 + i, "humor", ch="davra") for i in range(5)] + [row(40, "music", ch="paparazzi")]
        sl = sources.shortlist(rows)
        self.assertEqual(len(sl["xojaobod"]["news"]["top"]), 4)
        self.assertNotIn(20, [r["id"] for r in sl["xojaobod"]["news"]["top"]])  # чужое лого — не в списке
        self.assertEqual(len(sl["xojaobod"]["news"]["spare"]), 2)
        self.assertEqual(sl["davra"]["news"]["top"], [])                      # новости Хўжаобода Давре не идут
        self.assertEqual(len(sl["davra"]["humor"]["top"]), 3)
        self.assertEqual([r["id"] for r in sl["paparazzi"]["music"]["top"]], [40])
        self.assertEqual(sl["paparazzi"]["humor"]["top"], [])                 # юмор Давры Папарацци не берёт

    def test_folder_match_emoji_and_spaces(self):
        t = ["Все", "🏙 XOJAOBOD  CITY", "KATTA DAVRA", "Paparazzi UZ", "Новости"]
        self.assertEqual(sources.folder_match(t, ("XOJAOBOD CITY",)), "🏙 XOJAOBOD  CITY")
        self.assertEqual(sources.folder_match(["XOJAOBOD CITY 24"], ("XOJAOBOD CITY",)), "XOJAOBOD CITY 24")
        self.assertEqual(sources.folder_match(t, ("katta davra",)), "KATTA DAVRA")
        self.assertIsNone(sources.folder_match(t, ("PAPA·Шаҳар",)))

    def test_channel_in_two_folders_serves_both(self):
        sl = sources.shortlist([row(1, "humor", ch=("davra", "xojaobod"))])
        self.assertEqual([r["id"] for r in sl["davra"]["humor"]["top"]], [1])
        self.assertEqual([r["id"] for r in sl["xojaobod"]["humor"]["top"]], [1])

    def test_render(self):
        rows = [row(1, "news", ch="xojaobod"), row(2, "news", clean=0.0, ch="xojaobod")]
        rows[0]["subscribers"] = 1159335
        t = sources.render(sources.shortlist(rows), rows, "26.10.2026 09:00", {**FOUND, "paparazzi": None})
        self.assertIn("1.16 млн", t)
        self.assertIn("🧼 3/3", t)
        self.assertIn("с чужим логотипом", t.lower())
        self.assertIn("чистых каналов нет", t)                               # пустая рубрика видна владельцу
        self.assertIn("папка «XOJAOBOD CITY»", t)
        self.assertIn("«Paparazzi UZ» не найдена", t)

    def test_whitelist_v2_per_channel_and_block(self):
        rows = [row(1, "news", ch="xojaobod"), row(2, "music", ch="paparazzi"), row(3, "faith", ch="xojaobod"),
                row(4, "humor", ch="davra"), row(5, "useful", ch="davra")]
        rows[3]["username"] = "ShohonaKulgu"                                 # своё лого на всех видео — никогда
        wl = sources.whitelist(sources.shortlist(rows), "26.10")
        self.assertEqual(sources.ids_for(wl, "xojaobod"), [1, 3])
        self.assertEqual(sources.ids_for(wl, "paparazzi"), [2])
        self.assertEqual(sources.ids_for(wl, "davra"), [5])
        self.assertEqual(sources.ids_for(None, "davra"), [])                 # нет списка — куратор по своей папке
        wl2 = sources.whitelist(sources.shortlist([row(9, "humor", ch="paparazzi")]), "26.10")
        self.assertEqual(sources.ids_for(wl2, "paparazzi"), [])              # нет жонли ижро — Папарацци по папке

    def test_old_whitelist_ignored(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.assertIsNone(sources.load_whitelist(d / "whitelist.json"))
        (d / "whitelist.json").write_text('{"themes": {"news": [{"id": 7, "title": "T"}]}}', encoding="utf-8")
        self.assertEqual(sources.ids_for(sources.load_whitelist(d / "whitelist.json"), "davra"), [])  # старый (все папки) — не берём

    def test_check_order_round_robin_and_complete(self):
        good = [dict(row(i, "news", 1000 * i, ch="xojaobod"), clean=None) for i in range(1, 20)]
        good += [dict(row(50, "humor", ch="davra"), clean=None)]
        order = sources.check_order(good)
        self.assertEqual(order[0]["id"], 19)                                 # сильнейшие новости первыми
        self.assertEqual(order[1]["id"], 50)                                 # и сразу другой канал/рубрика — по кругу
        self.assertEqual(len([r for r in order if r["theme_by"].get("xojaobod") == "news"]), 10)  # квота×2+2
        self.assertFalse(sources.complete_list(sources.shortlist([row(i, "news", ch="xojaobod") for i in range(6)])))


if __name__ == "__main__":
    unittest.main()
