import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import sortfolders as S  # noqa: E402


class TestSort(unittest.TestCase):
    def test_titles_fit_telegram_limit(self):
        self.assertTrue(all(len(t) <= 12 for t in S.FOLDERS))

    def test_plan(self):
        chans = [{"id": 1, "title": "Musiqa", "subscribers": 10}, {"id": 2, "title": "Futbol", "subscribers": 50},
                 {"id": 3, "title": "Kulgu", "subscribers": 5}, {"id": 4, "title": "Bozor", "subscribers": 99},
                 {"id": 5, "title": "Andijon", "subscribers": 7}]
        cats = {"1": ["music"], "2": ["sport"], "3": ["humor"], "4": ["ads_market"], "5": ["local", "news"]}
        p = S.plan(chans, cats)
        names = {f: [c["title"] for c in cs] for f, cs in p.items()}
        self.assertEqual(names["PAPA·Музыка"], ["Musiqa", "Kulgu"])
        self.assertEqual(names["PAPA·Давра"], ["Futbol", "Andijon", "Kulgu"])
        self.assertEqual(names["PAPA·Шаҳар"], ["Andijon", "Kulgu"])
        self.assertNotIn("Bozor", sum(names.values(), []))

    def test_keywords_without_ai(self):
        self.assertEqual(S.keyword_cats({"title": "Futbol yangiliklari", "texts": ["Real Madrid matchda gol urdi"]})[0], "sport")
        self.assertIn("music", S.keyword_cats({"title": "Yangi qo'shiqlar 🎵", "texts": ["Yangi klip"]}))
        self.assertEqual(S.keyword_cats({"title": "Abc", "texts": []}), ["other"])

    def test_parse_json(self):
        self.assertEqual(S.parse_json('```json\n{"1": ["music"]}\n```'), {"1": ["music"]})
        self.assertEqual(S.parse_json('ok: {"2": ["news"]} end'), {"2": ["news"]})


if __name__ == "__main__":
    unittest.main()
