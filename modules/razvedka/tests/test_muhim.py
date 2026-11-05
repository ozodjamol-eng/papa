import datetime as dt
import tempfile
import unittest
from pathlib import Path

from razvedka import muhim


class T(unittest.TestCase):
    def test_useful_urgent(self):
        for t in ("Эртага электр энергияси ўчирилади", "Ertaga gaz berilmaydi, ehtiyot bo'ling",
                  "Ичимлик сув таъминотида узилиш бўлади", "Душанба дам олиш куни деб эълон қилинди",
                  "Фирибгарлардан эҳтиёт бўлинг: SMS орқали карта маълумотларини сўрашмоқда",
                  "Кучли шамол ва дўл бўйича огоҳлантириш", "Бензин нархи ошди", "Пенсиялар 1-декабрдан оширилади"):
            self.assertTrue(muhim.is_muhim(t), t)

    def test_never_politics_crime_sad(self):
        for t in ("Президент электр энергияси бўйича фармон имзолади", "Йўлда ЙТҲ: 2 киши ҳалок бўлди, газ баллони портлади",
                  "Ўғирлик учун қамоққа олинди, газ плита", "Вафот этди: сув тошқини"):
            self.assertFalse(muhim.is_muhim(t), t)

    def test_plain_posts_not_muhim(self):
        for t in ("Хўжаобод тумани ҳокимлигида учрашув бўлди", "Янги клип чиқди", "Ажойиб манзара, туман ҳаммомлари"):
            self.assertFalse(muhim.is_muhim(t), t)

    def test_key_mark_limit(self):
        self.assertEqual(muhim.bot_key(5551, 77), "-1005551:77")
        now = dt.datetime(2026, 11, 5, 14, tzinfo=dt.timezone.utc)
        d = muhim.mark({"keys": {"old:1": {"ts": "2026-11-01T00:00:00+00:00"}}}, "xojaobod", ["-1005551:77"], now)
        self.assertEqual(set(d["keys"]), {"-1005551:77"})          # старше 2 дней — убрано
        self.assertEqual(muhim.sent_today({"sent": {"xojaobod": {"2026-11-05": 2}}}, "xojaobod", "2026-11-05"), 2)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "m.json"
            muhim.save(d, p)
            self.assertEqual(muhim.load(p)["keys"]["-1005551:77"]["channel"], "xojaobod")


if __name__ == "__main__":
    unittest.main()
