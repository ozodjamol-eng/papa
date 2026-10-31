import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import archive  # noqa: E402

NOW = dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc)


def it(i, days=400, kind="video", text="ЗЎР ВИДЕО", views=1000, ad=False):
    return {"id": i, "kind": kind, "text": text, "date": NOW - dt.timedelta(days=days), "views": views, "ad": ad}


class T(unittest.TestCase):
    def test_candidate(self):
        self.assertTrue(archive.is_candidate(it(1), NOW))
        self.assertFalse(archive.is_candidate(it(1, days=30), NOW))              # моложе 6 месяцев
        self.assertFalse(archive.is_candidate(it(1, kind="text"), NOW))
        self.assertFalse(archive.is_candidate(it(1, ad=True), NOW))
        self.assertFalse(archive.is_candidate(it(1, text="Бугун концерт бўлади"), NOW))   # привязка к дате

    def test_strong(self):
        got = archive.strong([it(1, views=100), it(4, views=500), it(2, views=1000), it(3, views=5000)])
        self.assertEqual([x["id"] for x in got], [2, 3])                       # медиана 750 ×1.1


class Batch(unittest.TestCase):
    """31.10 отдел Архив: пачка постов за один запрос; чужое лого и непонятное — SKIP."""

    def test_parse(self):
        out = '[{"n":1,"hub":"РАЗВЛЕКАТЕЛЬНО","text":"😂 КУЛГИ","logo":false},' \
              '{"n":2,"hub":"ФОЙДАЛИК","text":"x","logo":true},{"n":3,"hub":"???","text":"y"}]'
        r = archive.parse_batch(out, 4)
        self.assertEqual([x["hub"] for x in r], ["РАЗВЛЕКАТЕЛЬНО", "SKIP", "SKIP", "SKIP"])
        self.assertTrue(r[1]["logo"])

    def test_parse_no_numbers(self):
        r = archive.parse_batch('[{"hub":"ИБРАТ","text":"a"},{"hub":"SKIP","text":""}]', 2)
        self.assertEqual([x["hub"] for x in r], ["ИБРАТ", "SKIP"])


class Sources(unittest.TestCase):
    """31.10: группа без просмотров и свой музыкальный склад."""

    def test_no_views_take_all(self):
        got = archive.strong([it(1, views=0), it(2, views=0)])
        self.assertEqual([x["id"] for x in got], [1, 2])

    def test_age_free(self):
        self.assertFalse(archive.is_candidate(it(1, days=1), NOW))
        self.assertTrue(archive.is_candidate(it(1, days=1), NOW, True))
