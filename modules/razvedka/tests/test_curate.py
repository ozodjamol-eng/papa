import datetime as dt
import unittest

from razvedka import curate


class TestCurate(unittest.TestCase):
    def c(self, key, text, sc):
        return {"key": key, "text": text, "score": sc}

    def test_ads_filtered(self):
        self.assertTrue(curate.is_ad("Чегирма 50%! Тел +998 90 123 45 67", False))
        self.assertTrue(curate.is_ad("#реклама зўр дўкон", False))
        self.assertTrue(curate.is_ad("https://a.uz и https://b.uz", False))
        self.assertFalse(curate.is_ad("Футбол: Пахтакор голиб чиқди", False))

    def test_score_prefers_viral_and_fair_to_young(self):
        self.assertGreater(curate.score(5000, 1000, 12), curate.score(1500, 1000, 12))
        self.assertAlmostEqual(curate.score(500, 1000, 3), curate.score(1000, 1000, 12) * 1.0, delta=1.1)

    def test_same_news_once(self):
        a = "Андижонда кучли ёмғир ёғди йўллар сув остида қолди ҳайдовчилар эҳтиёт бўлинг"
        b = "Андижонда кучли ёмғир ёғди, йўллар сув остида қолди — ҳайдовчилар эҳтиёт бўлсин"
        out = curate.pick([self.c("1", a, 5), self.c("2", b, 4), self.c("3", "Пахтакор финалга чиқди олдинда жуда қизиқ ўйин", 3)], 5, [])
        self.assertEqual([x["key"] for x in out], ["1", "3"])

    def test_history_blocks_repeat(self):
        a = "Андижонда кучли ёмғир ёғди йўллар сув остида қолди"
        hist = [{"key": "9", "sig": sorted(curate.sig(a)), "ts": dt.datetime.now(dt.timezone.utc).isoformat()}]
        self.assertEqual(curate.pick([self.c("1", a, 5)], 5, hist), [])

    def test_routes_and_bots(self):
        self.assertEqual(curate.BOTS["davra"], "PapaGenplanBot")
        self.assertIn("KATTA DAVRA", curate.ROUTES["davra"])
        self.assertIn("Paparazzi UZ", curate.ROUTES["paparazzi"])

    def test_peers_in_ignores_case_and_spaces(self):
        folders = {"KATTA DAVRA": [1, 2], "Paparazzi  UZ": [3], "Новости": [9]}
        self.assertEqual(curate.peers_in(folders, curate.ROUTES["davra"]), [1, 2])
        self.assertEqual(curate.peers_in(folders, ["paparazzi uz"]), [3])
        self.assertEqual(curate.peers_in(folders, ["нет такой"]), [])


if __name__ == "__main__":
    unittest.main()


class TestPolicy(unittest.TestCase):
    def test_off_policy(self):
        self.assertEqual(curate.off_policy("Президент парламентда нутқ сўзлади", "davra"), "politics")
        self.assertEqual(curate.off_policy("Xonanda yangi klip taqdim etdi", "davra"), "showbiz")
        self.assertEqual(curate.off_policy("Xonanda yangi klip taqdim etdi", "paparazzi"), "")
        self.assertEqual(curate.off_policy("Saylov natijalari", "paparazzi"), "politics")
        self.assertEqual(curate.off_policy("Уйда фойдали маслаҳат: тез тозалаш", "davra"), "")
        self.assertEqual(curate.off_policy("OpenAI yangi model chiqardi", "davra"), "")
