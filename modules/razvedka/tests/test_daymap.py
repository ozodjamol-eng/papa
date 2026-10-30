import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from razvedka import daymap  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=5))


def post(cid, hour, text, rel=None, ad=False):
    return {"channel_id": cid, "local": dt.datetime(2026, 10, 29, hour, 0, tzinfo=TZ), "text": text, "ad": ad, "rel": rel}


class TestDaymap(unittest.TestCase):
    def test_rubric(self):
        self.assertEqual(daymap.rubric("Хайрли тонг, азизлар!", False), "greet")
        self.assertEqual(daymap.rubric("Фирибгарлардан эҳтиёт бўлинг", False), "scam")
        self.assertEqual(daymap.rubric("ИШГА МАРҲАМАТ! Хўжаобод тумани", False), "jobs")
        self.assertEqual(daymap.rubric("Chegirma", True), "ad")
        self.assertEqual(daymap.rubric("", False), "other")
        self.assertEqual(daymap.rubric("Бугун пойтахтда катта йиғилиш бўлиб ўтди ва қарор…", False, "Tezkor Yangiliklar"), "news")

    def test_build_per_topic_and_skip_own(self):
        chans = {1: {"title": "A", "folder": "KATTA DAVRA", "is_own": 0},
                 2: {"title": "B", "folder": "XOJAOBODCITY + KATTA DAVRA", "is_own": 0},
                 3: {"title": "Own", "folder": "свои", "is_own": 1}}
        ps = [post(1, 19, "😂 кулги", 1.5) for _ in range(9)] + [post(2, 19, "Хайрли тонг", 0.8) for _ in range(9)]
        ps += [post(3, 19, "😂", 9.0)]
        maps = {m["topic"]: m for m in daymap.build(ps, chans)}
        self.assertEqual(set(maps), {"KATTA DAVRA", "XOJAOBODCITY"})
        davra = maps["KATTA DAVRA"]
        self.assertEqual(davra["posts"], 18)                       # свой канал не считается
        h19 = next(h for h in davra["hours"] if h["hour"] == 19)
        self.assertEqual(h19["best"]["code"], "humor")
        humor = next(r for r in davra["rubrics"] if r["code"] == "humor")
        self.assertEqual(humor["strength"], 1.5)
        text = "\n".join(daymap.render(list(maps.values())))
        self.assertIn("КАРТА ДНЯ", text)
        self.assertIn("19:00", text)


if __name__ == "__main__":
    unittest.main()
