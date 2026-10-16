"""Свой Кечки дайжест: сборка пакета на подставных данных (без сети), протокол 12.10, без выдуманных ссылок."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from genplan import digest, plan, store  # noqa: E402

NOW = dt.datetime(2026, 10, 16, 19, 50, tzinfo=plan.TZ)
FORECAST = {"current": {"temperature_2m": 17.6, "weather_code": 0, "wind_speed_10m": 6.1, "is_day": 0, "time": "2026-10-16T19:45"},
            "daily": {"weather_code": [0, 2], "temperature_2m_max": [24, 23.4], "temperature_2m_min": [9, 10.2],
                      "precipitation_probability_max": [0, 10]}}
AIR = {"current": {"us_aqi": 63, "pm2_5": 18}}
CBU = [{"Ccy": "USD", "Rate": "12650.43", "Diff": "-12.4", "Date": "17.10.2026"},
       {"Ccy": "EUR", "Rate": "14720.10", "Diff": "21.3", "Date": "17.10.2026"},
       {"Ccy": "RUB", "Rate": "156.12", "Diff": "0", "Date": "17.10.2026"}]
RSS = """<rss><channel>
<item><title>Andijonda yangi ko'prik ochildi</title><link>https://kun.uz/news/1</link><pubDate>Fri, 16 Oct 2026 10:00:00 +0500</pubDate></item>
<item><title>Eski yangilik</title><link>https://kun.uz/news/0</link><pubDate>Wed, 14 Oct 2026 10:00:00 +0500</pubDate></item>
</channel></rss>"""


def fake_get(url, timeout=25):
    if "air-quality" in url:
        return json.dumps(AIR).encode()
    if "open-meteo" in url:
        return json.dumps(FORECAST).encode()
    if "cbu.uz" in url:
        return json.dumps(CBU).encode()
    if "kun.uz" in url:
        return RSS.encode()
    raise RuntimeError("недоступно")


def fake_gen(system, user):
    return ('[{"t": "Andijonda yangi ko\'prik ochildi", "src": "x", "url": "https://kun.uz/news/1"},'
            ' {"t": "Выдумка", "src": "x", "url": "https://fake.example/1"}]')


class TestDigest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.db = store.connect(self.dir / "g.db")

    def test_build_ready_package(self):
        r = digest.build(self.db, self.dir, NOW, get=fake_get, gen=fake_gen)
        self.assertEqual(r["status"], "READY")
        out = Path(r["dir"])
        m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((m["status"], m["date"], m["channel_id"]), ("READY", "2026-10-16", -1001404984661))
        self.assertEqual(m["publish_at"], "2026-10-16T20:30:00+05:00")
        self.assertEqual(m["image_sha256"], digest.sha(out / "digest.png"))
        self.assertEqual(m["text_sha256"], digest.sha((out / "digest.txt").read_text(encoding="utf-8").encode()))
        self.assertLessEqual(len(m["photo_caption"]), 1024)
        self.assertEqual([s["url"] for s in m["news_sources"]], ["https://kun.uz/news/1"])     # выдуманная ссылка выброшена
        txt = (out / "digest.txt").read_text(encoding="utf-8")
        for part in ("КЕЧКИ ДАЙЖЕСТ | 16 октябрь 2026", "Андижонда янги кўприк очилди", "Хўжаобод: +18°", "AQI 63",
                     "Эртага Хўжаободда: +10…+23°", "1 USD = 12 650,43 сўм (▼ 12,40)", "@xojaobodcity24"):
            self.assertIn(part, txt)
        self.assertIn("лента Daryo.uz: RuntimeError", r["errors"])

    def test_no_weather_not_ready(self):
        r = digest.build(self.db, self.dir, NOW, get=lambda u, timeout=25: (_ for _ in ()).throw(RuntimeError("нет сети")),
                         gen=fake_gen)
        self.assertEqual(r["status"], "INVALID")
        self.assertFalse((self.dir / "evening-digest-2026-10-16" / "manifest.json").exists())

    def test_ai_down_still_ready_without_news(self):
        def broken(s, u):
            raise RuntimeError("лимит")
        r = digest.build(self.db, self.dir, NOW, get=fake_get, gen=broken)
        self.assertEqual((r["status"], r["news"]), ("READY", 0))

    def test_long_caption_trimmed(self):
        news = [{"t": "Ж" * 150, "src": "Kun.uz", "url": f"https://kun.uz/{i}"} for i in range(5)]
        w = digest.weather(fake_get)
        short, full = digest.compose(NOW.date(), w, digest.rates(fake_get), news * 3)
        self.assertLessEqual(len(short), 1024)
        self.assertIn("@xojaobodcity24", short)
