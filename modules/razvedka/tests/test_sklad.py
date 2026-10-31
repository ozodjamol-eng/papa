"""26.10: 📦 склады владельца — доверенный материал, сам по сетке с вето."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import sklad  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=5))
MORNING = dt.datetime(2026, 10, 26, 8, 0, tzinfo=TZ)
NOON = dt.datetime(2026, 10, 26, 12, 30, tzinfo=TZ)
EVENING = dt.datetime(2026, 10, 26, 17, 0, tzinfo=TZ)


def it(i, kind="video", text="Фойдали маслаҳат", days=100, ad=False):
    return {"id": i, "ids": [i], "kind": kind, "text": text, "date": MORNING - dt.timedelta(days=days), "ad": ad}


class TestSklad(unittest.TestCase):
    def test_daily_quota_split_over_three_runs(self):
        self.assertEqual(sklad.allowed(3, 0, MORNING), 1)                  # 3 → 1 + 1 + 1
        self.assertEqual(sklad.allowed(3, 1, NOON), 1)
        self.assertEqual(sklad.allowed(3, 2, EVENING), 1)
        self.assertEqual(sklad.allowed(3, 3, EVENING), 0)
        self.assertEqual(sklad.allowed(2, 0, MORNING), 1)                  # 2 → 1 + 1 + 0
        self.assertEqual(sklad.allowed(3, 0, EVENING), 3)                  # утром не вышло — вечером догоняем
        self.assertEqual(sklad.FIXED["davra"]["ФОЙДАЛИК"], 3)
        self.assertEqual(sklad.FIXED["xojaobod"]["ФОЙДАЛИК"], 3)
        self.assertEqual(sklad.FIXED["paparazzi"]["РЕТРО КЛИПЛАР"], 4)

    def test_eligible_media_fresh_policy(self):
        self.assertTrue(sklad.eligible(it(1), "ФОЙДАЛИК", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, kind=None), "ФОЙДАЛИК", "davra", MORNING))       # голая ссылка/текст
        self.assertFalse(sklad.eligible(it(1, ad=True), "ФОЙДАЛИК", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, days=3), "NEWS INBOX", "davra", MORNING))       # старая новость
        self.assertTrue(sklad.eligible(it(1, days=1), "NEWS INBOX", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, days=1, text="Президент парламентда сўзлади"), "NEWS INBOX", "davra", MORNING))
        self.assertTrue(sklad.eligible(it(1, days=1, text="Президент парламентда сўзлади"), "NEWS INBOX", "xojaobod", MORNING))

    def test_plan_fixed_foydalik_plus_round_robin(self):
        stashes = {"ФОЙДАЛИК": [it(i) for i in range(1, 21)], "РАЗВЛЕКАТЕЛЬНО": [it(i) for i in range(100, 103)],
                   "ФОЙДАЛИК ОВКАТ": [it(i) for i in range(300, 305)], "Jonlik ijrolar": [it(i) for i in range(200, 205)]}
        p = sklad.plan(stashes, {}, {}, EVENING)
        d = [(s, x["id"]) for s, x, _ in p["davra"]]
        self.assertEqual([x for s, x in d if s == "ФОЙДАЛИК"], [1, 2, 3])                  # ровно 3, с начала
        self.assertEqual([s for s, _ in d].count("РАЗВЛЕКАТЕЛЬНО"), 2)                       # юмор — 2
        self.assertEqual([s for s, _ in d].count("Jonlik ijrolar"), 3)                       # 30.10 сверка: музыка — своя норма 3
        self.assertEqual([s for s, _ in d].count("ФОЙДАЛИК ОВКАТ"), 3)                       # + 3 других по кругу
        x = [(s, i) for s, i, _ in [(s, x["id"], k) for s, x, k in p["xojaobod"]]]
        self.assertEqual([i for s, i in x if s == "ФОЙДАЛИК"], [20, 19, 18])                # Хўжаобод — с конца
        self.assertEqual(len(x), 6)                                                        # 3 + юмор 1 + 2 по кругу
        pp = [(s, x["id"]) for s, x, _ in p["paparazzi"]]
        self.assertEqual(pp[:4], [("ФОЙДАЛИК", 11), ("ФОЙДАЛИК", 12), ("Jonlik ijrolar", 202), ("Jonlik ijrolar", 203)])
        self.assertEqual([s for s, _ in pp].count("РАЗВЛЕКАТЕЛЬНО"), 2)
        self.assertTrue(all(k == "davra|ФОЙДАЛИК" for s, _, k in p["davra"] if s == "ФОЙДАЛИК"))
        used = {"davra|ФОЙДАЛИК": ["1", "2", "3"]}
        p2 = sklad.plan(stashes, used, {"davra|ФОЙДАЛИК": 2}, EVENING)
        self.assertEqual([x["id"] for s, x, _ in p2["davra"] if s == "ФОЙДАЛИК"], [4])     # норма: осталась 1

    def test_davra_hour_norms(self):
        """30.10 сверка: часы Давры «час = рубрика» получают свои нормы — мотивация 2, музыка 3, бизнес 1, ибрат 1."""
        self.assertEqual({k: sklad.FIXED["davra"][k] for k in ("МОТИВАЦИЯ", "Jonlik ijrolar", "УЙДА БИЗНЕС", "ИБРАТ")},
                         {"МОТИВАЦИЯ": 2, "Jonlik ijrolar": 3, "УЙДА БИЗНЕС": 1, "ИБРАТ": 1})
        stashes = {k: [it(i) for i in range(n, n + 5)] for k, n in
                   (("МОТИВАЦИЯ", 400), ("Jonlik ijrolar", 500), ("УЙДА БИЗНЕС", 600), ("ИБРАТ", 700))}
        d = [s for s, _, _ in sklad.plan(stashes, {}, {}, EVENING)["davra"]]
        self.assertEqual((d.count("МОТИВАЦИЯ"), d.count("Jonlik ijrolar"), d.count("УЙДА БИЗНЕС"), d.count("ИБРАТ")), (2, 3, 1, 1))

    def test_stale_words_and_juma_only_friday(self):
        self.assertFalse(sklad.eligible(it(1, text="Бугун об-ҳаво иссиқ"), "ФОЙДАЛИК", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, text="2024 йил натижалари"), "ФОЙДАЛИК", "davra", MORNING))
        self.assertFalse(sklad.eligible(it(1, text="Учрашув 12.05.2025 да"), "ФОЙДАЛИК", "davra", MORNING))
        self.assertTrue(sklad.eligible(it(1, text="Бугунги кунда ҳам фойдали"), "ФОЙДАЛИК", "davra", MORNING))  # «бугунги» ≠ «бугун»
        friday = dt.datetime(2026, 10, 30, 8, 0, tzinfo=TZ)
        self.assertFalse(sklad.eligible(it(1, text="Жума муборак!"), "МАЪНАВИЯТ", "xojaobod", MORNING))   # понедельник
        self.assertTrue(sklad.eligible(it(1, text="Жума муборак!"), "МАЪНАВИЯТ", "xojaobod", friday))
        st = {"МАЪНАВИЯТ": [it(1, text="Дуо"), it(2, text="Жума муборак"), it(3, text="Ҳадис")]}
        p = sklad.plan(st, {}, {}, friday.replace(hour=17))
        self.assertEqual([x["id"] for s, x, _ in p["xojaobod"] if s == "МАЪНАВИЯТ"], [2, 3, 1])   # пятница: 3, «Жума» первой

    def test_left_counts_hungriest_channel(self):
        stashes = {"ФОЙДАЛИК": [it(i) for i in range(1, 6)]}
        self.assertEqual(sklad.left(stashes, {"davra|ФОЙДАЛИК": ["1", "2", "3"]}, MORNING), {"ФОЙДАЛИК": 2})

    def test_external_archive_quota_bad_and_fresh(self):
        self.assertTrue(sklad.external("@AbduraxmonQiziq"))
        self.assertFalse(sklad.external("ФОЙДАЛИК"))
        self.assertNotIn("@ShohonaKulgu", sklad.SKLAD)                                     # своё лого — в блоке
        st = {"@AbduraxmonQiziq": [it(i, text="Ҳажвия") for i in range(1, 6)]}
        p = sklad.plan(st, {"bad|@AbduraxmonQiziq": ["1"]}, {}, EVENING)
        self.assertEqual([x["id"] for _, x, _ in p["davra"]], [2])                         # 1 в день, «лого» пропущен
        self.assertEqual([x["id"] for _, x, _ in p["xojaobod"]], [5])
        old = {"@madaniyatvazirligi": [it(1, days=30), it(2, days=1)]}
        self.assertEqual([x["id"] for _, x, _ in sklad.plan(old, {}, {}, EVENING)["paparazzi"]], [2])   # архив новостей — нет

    def test_titles_match_without_case_and_emoji(self):
        self.assertEqual(sklad._norm("📦 Фойдалик  овкат"), sklad._norm("ФОЙДАЛИК ОВКАТ"))

    def test_muftiy_lessons_only_and_different_per_channel(self):
        """31.10 владелец: Муфтий в обоих каналах, разными постами; в слот — только уроки."""
        M = "@shayx_nuriddinxoliqnazar"
        now = dt.datetime(2026, 10, 31, 3, 0, tzinfo=dt.timezone.utc)   # 08:00 Ташкент, 1-й запуск
        items = [it(1, text="#muftiy_minbari Дарс А"), it(2, text="#kun_oyati Оят"), it(3, text="#tabrik Табрик"),
                 it(4, text="#muftiy_minbari Дарс Б"), it(5, text="#muftiy_minbari Дарс А")]
        self.assertFalse(sklad.eligible(items[1], M, "davra", now))
        self.assertFalse(sklad.eligible(items[2], M, "davra", now))
        used = {}
        p = sklad.plan({M: items}, used, {}, now)
        d = [x["id"] for s, x, _ in p["davra"] if s == M]
        self.assertEqual(len(d), 1)
        sklad.mark_used(used, M, "davra", next(x for x in items if x["id"] == d[0]))
        p = sklad.plan({M: items}, used, {}, now)
        x = [x for s, x, _ in p["xojaobod"] if s == M]
        self.assertEqual(len(x), 1)
        self.assertNotEqual(sklad.text_key(x[0]["text"]), sklad.text_key(next(i for i in items if i["id"] == d[0])["text"]))


if __name__ == "__main__":
    unittest.main()


class LogoCheckAllStashes(unittest.TestCase):
    """31.10: в Хўжаобод вышло видео ФОЙДАЛИК с чужим @OPER_UZ — проверка лого для всех складов."""

    def test_own_stash_checked(self):
        for s in ("ФОЙДАЛИК", "РАЗВЛЕКАТЕЛЬНО", "NEWS INBOX", "@AbduraxmonQiziq"):
            self.assertTrue(sklad.needs_check(s), s)

    def test_muftiy_not_checked(self):
        self.assertFalse(sklad.needs_check("@shayx_nuriddinxoliqnazar"))
