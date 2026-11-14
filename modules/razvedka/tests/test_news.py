import datetime as dt
import tempfile
import unittest
from pathlib import Path

from razvedka import news

LONG = " Бу ҳақда маълумот берилди, янги тартиб барча вилоятларда жорий этилади ва фуқароларга қулайлик яратади."


class T(unittest.TestCase):
    def test_good_news(self):
        self.assertTrue(news.fits("Ўзбекистонда янги автобус йўналишлари очилди, расман эълон қилинди." + LONG, False))
        self.assertTrue(news.fits("Андижонда янги боғ очилди, одамлар хурсанд бўлишмоқда." + LONG, True))   # выбранный источник

    def test_never_sad_politics_crime_showbiz(self):
        for t in ("Йўлда авария: икки киши ҳалок бўлди, расман маълум қилинди.", "Президент янги фармон имзолади.",
                  "Ўғирлик учун қамоққа олинди, ИИВ хабар берди.", "Хонанда янги клип чиқарди, расман эълон қилди."):
            self.assertFalse(news.fits(t + LONG, True), t)

    def test_short_or_not_news(self):
        self.assertFalse(news.fits("Расман эълон қилинди.", True))                     # слишком коротко
        self.assertFalse(news.fits("Ажойиб манзара, тоғлар ва дарёлар жуда чиройли кўринади." + LONG.replace("маълумот берилди", "айтилди"), False))

    def test_sources_limit_bank(self):
        choice = {"channels": {"davra": {"news": [{"id": 1}], "humor": [{"id": 2}]}, "xojaobod": {"local": [{"id": 3}]},
                               "paparazzi": {"news": [{"id": 9}]}}}
        self.assertEqual(news.news_ids(choice), {1, 3})
        self.assertEqual(news.news_ids(None), set())
        now = dt.datetime(2026, 11, 14, 7, tzinfo=dt.timezone.utc)
        self.assertTrue(news.bank_fresh([now - dt.timedelta(hours=1)], now))
        self.assertFalse(news.bank_fresh([now - dt.timedelta(hours=5)], now))
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "n.json"
            news.save({"sent": {"2026-11-14": 2}}, p)
            self.assertEqual(news.sent_today(news.load(p), "2026-11-14"), 2)
            self.assertEqual(news.sent_today(news.load(p), "2026-11-15"), 0)


if __name__ == "__main__":
    unittest.main()
