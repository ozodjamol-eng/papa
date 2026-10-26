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

    def test_theme_rubrics_and_politics(self):
        self.assertEqual(sources.theme(["humor", "news"]), "news")
        self.assertEqual(sources.theme(["interesting"]), "fun")
        pap = dict((x[0], x[3]) for x in sources.PROFILES)["paparazzi"]
        self.assertEqual(sources.theme(["news", "humor"], pap), "humor")      # новостей у PaparazziUZ нет
        self.assertIsNone(sources.theme(["politics_official", "news"], None, politics=False))  # Давре — без пресс-служб

    def test_folder_match_emoji_and_spaces(self):
        t = ["Все", "🏙 XOJAOBOD  CITY", "KATTA DAVRA", "Paparazzi UZ", "Новости"]
        self.assertEqual(sources.folder_match(t, ("XOJAOBOD CITY",)), "🏙 XOJAOBOD  CITY")
        self.assertEqual(sources.folder_match(["XOJAOBODCITY"], ("XOJAOBOD CITY",)), "XOJAOBODCITY")
        self.assertIsNone(sources.folder_match(t, ("PAPA·Шаҳар",)))

    def test_verdict(self):
        self.assertEqual(sources.verdict(row(1, "news"))[0], 0)                       # ⭐
        self.assertEqual(sources.verdict(row(1, "news", clean=1 / 3))[0], 3)          # 🚫 лого
        self.assertEqual(sources.verdict({**row(1, "news"), "clean": None})[0], 2)    # ⚠️ не проверен
        self.assertIn("латиница", sources.verdict({**row(1, "news"), "cyr_share": 0.2})[1])

    def test_candidates_five_best_dirty_out_must_kept(self):
        rows = [row(i, "news", 10000 + i * 1000) for i in range(8)] + [row(20, "news", 999999, clean=1 / 3)]
        rows.append({**row(30, "news", 900, clean=1 / 3), "title": "Tezkor Yangiliklar ⚡", "username": "tezkor_y",
                     "why": "мало просмотров"})
        c = sources.candidates(rows, "davra", "news")
        ids = [r["id"] for r in c]
        self.assertEqual(len(c), 5)
        self.assertNotIn(20, ids)                                                     # чужое лого — не предлагаем
        self.assertIn(30, ids)                                                        # «обязательный» — всегда в пятёрке

    def test_card_buttons_and_preselect(self):
        rows = [row(1, "news"), {**row(2, "news"), "clean": None}]
        cands = sources.build(rows)
        t, kb = sources.card("davra", cands["davra"], rows, "KATTA DAVRA", "26.10")
        btn = [b for r in kb["inline_keyboard"] for b in r]
        self.assertTrue(btn[0]["text"].startswith("☑"))                               # ⭐ отмечен сразу
        self.assertTrue(btn[1]["text"].startswith("⬜"))
        self.assertEqual(btn[0]["callback_data"], "sw:t:davra:news:1")
        self.assertEqual(btn[-1]["callback_data"], "sw:ok:davra")
        self.assertTrue(all(len(b["callback_data"].encode()) <= 64 for b in btn))
        self.assertIn("⭐ Рекомендую", t)
        self.assertIn("Мой совет", t)
        t2, kb2 = sources.card("davra", cands["davra"], rows, "KATTA DAVRA", "26.10", chosen={2})
        self.assertTrue(kb2["inline_keyboard"][1][0]["text"].startswith("☑"))       # уже выбранные владельцем
        self.assertIsNone(sources.card("paparazzi", {}, rows, None, "26.10")[1])     # нет папки — без кнопок

    def test_rare_artist_channels_ok_for_live_music_only(self):
        art = {**row(1, "music", ch="paparazzi"), "why": "редко пишет", "posts": 2, "per_day": 0.3, "media_share": 1.0}
        sources.relax_rare(art)
        self.assertEqual(art["why"], "")
        self.assertIn("пишет редко", sources.verdict(art)[1])
        self.assertEqual(sources.verdict(art)[0], 1)                                  # 👍, не ⭐
        news = {**row(2, "news"), "why": "редко пишет", "posts": 2}
        sources.relax_rare(news)
        self.assertEqual(news["why"], "редко пишет")                                  # новостям порог остаётся
        weak = {**row(4, "music", 77, ch="paparazzi"), "why": "редко пишет", "posts": 1, "per_day": 0.1, "media_share": 1.0}
        sources.relax_rare(weak)
        self.assertEqual(weak["why"], "мало просмотров")                              # 77 просмотров — всё равно нет
        dead = {**row(3, "music", ch="paparazzi"), "why": "редко пишет", "posts": 0}
        sources.relax_rare(dead)
        self.assertEqual(dead["why"], "редко пишет")                                  # совсем молчит — нет

    def test_choice_ids_and_main_empty(self):
        ch = {"version": 2, "channels": {"davra": {"news": [{"id": 5, "title": "A"}], "humor": [{"id": 6, "title": "B"}]},
                                          "paparazzi": {"humor": [{"id": 9, "title": "C"}]}}}
        self.assertEqual(sources.ids_for(ch, "davra"), [5, 6])
        self.assertEqual(sources.ids_for(ch, "xojaobod"), [])                        # не выбирал — по папке
        self.assertEqual(sources.ids_for(None, "davra"), [])
        self.assertTrue(sources.main_empty(ch, "paparazzi"))                         # нет жонли ижро — плюс папка
        self.assertFalse(sources.main_empty(ch, "davra"))

    def test_check_order_must_first_round_robin(self):
        good = [dict(row(i, "news", 1000 * i), clean=None) for i in range(1, 20)] + [dict(row(50, "humor"), clean=None)]
        good.append({**row(60, "news", 10), "title": "Тезкор Хабарлар", "clean": None})
        order = sources.check_order(good)
        self.assertEqual(order[0]["id"], 60)                                         # обязательный — первым
        self.assertEqual(order[1]["id"], 19)
        self.assertEqual(order[2]["id"], 50)                                         # и сразу другая рубрика


if __name__ == "__main__":
    unittest.main()
