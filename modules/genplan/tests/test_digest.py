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


def fake_get(url, timeout=25, tries=3):
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
    return ('```json\n[{"i": 1, "t": "Andijonda yangi ko\'prik ochildi"},'
            ' {"i": 99, "t": "Выдумка"}, {"i": "1", "t": "дубль"}]\n```')


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
        for part in ("КЕЧКИ ДАЙЖЕСТ", "📅 16 октябрь 2026, жума", "1️⃣ Андижонда янги кўприк очилди", "🔗 Манбалар: Kun.uz",
                     "• Хўжаобод — +18°", "🫁 Ҳаво сифати: ўртача (AQI 63)", "+10…+23°",
                     "🇺🇸 USD — 12 650,43 сўм 📉 −12,40", "RUB — 156,12 сўм ➖ ўзгармади",
                     "📢 Реклама учун: @Ozodjamol", "👉 @xojaobodcity24", "━━━━━━━━━━━━"):
            self.assertIn(part, txt)
        self.assertIn("лента Daryo.uz: RuntimeError", r["errors"])

    def test_no_weather_not_ready(self):
        r = digest.build(self.db, self.dir, NOW, get=lambda u, timeout=25, tries=3: (_ for _ in ()).throw(RuntimeError("нет сети")),
                         gen=fake_gen)
        self.assertEqual(r["status"], "INVALID")
        self.assertFalse((self.dir / "evening-digest-2026-10-16" / "manifest.json").exists())

    def test_ai_retry_after_overload(self):
        calls = []

        def flaky(s, u):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("Gemini: ошибка 503")
            return fake_gen(s, u)
        got = digest.pick_news(self.db, [{"title": "Andijonda yangi ko'prik ochildi", "src": "Kun.uz",
                                          "url": "https://kun.uz/news/1", "time": "10:00"}], flaky, sleep=lambda s: None)
        self.assertEqual((len(calls), len(got)), (3, 1))

    def test_ai_down_still_ready_without_news(self):
        def broken(s, u):
            raise RuntimeError("лимит")
        digest.time_sleep = None
        import time as _t
        orig, _t.sleep = _t.sleep, (lambda s: None)
        try:
            r = digest.build(self.db, self.dir, NOW, get=fake_get, gen=broken)
        finally:
            _t.sleep = orig
        self.assertEqual((r["status"], r.get("news_mode")), ("READY", "без ИИ (заголовки)"))
        txt = (Path(r["dir"]) / "digest.txt").read_text(encoding="utf-8")
        self.assertIn("Андижонда янги кўприк очилди", txt)

    def test_long_caption_trimmed(self):
        news = [{"t": "Ж" * 150, "src": "Kun.uz", "url": f"https://kun.uz/{i}"} for i in range(5)]
        w = digest.weather(fake_get)
        short, full = digest.compose(NOW.date(), w, digest.rates(fake_get), news * 3)
        self.assertLessEqual(len(short), 1024)
        self.assertIn("@xojaobodcity24", short)

    def test_aqi_once_and_ad_off(self):
        w = digest.weather(fake_get)
        short, full = digest.compose(NOW.date(), w, {}, [], ad="")
        self.assertEqual(full.count("AQI"), 1)
        self.assertNotIn("Реклама", full)


class TestFallback(unittest.TestCase):
    def test_region_first_ads_and_russian_skipped(self):
        items = [{"title": "Toshkentda yangi metro bekati ochildi", "src": "Kun.uz", "url": "u1", "time": "18:00"},
                 {"title": "Andijonda suv ta'minoti yaxshilandi", "src": "Daryo.uz", "url": "u2", "time": "09:00"},
                 {"title": "Reklama: chegirmalar haftaligi", "src": "Kun.uz", "url": "u3", "time": "19:00"},
                 {"title": "В Ташкенте открыли новую станцию метро", "src": "Gazeta.uz", "url": "u4", "time": "17:00"}]
        got = digest.fallback_news(items)
        self.assertEqual([x["url"] for x in got], ["u2", "u1"])
        self.assertTrue(got[0]["t"].startswith("Андижонда"))


class TestLive(unittest.TestCase):
    def test_publish_once_in_window(self):
        import asyncio
        d = Path(tempfile.mkdtemp()); db = store.connect(d / "g.db")
        now = dt.datetime(2026, 10, 16, 20, 31, tzinfo=plan.TZ)
        digest.build(db, d, now.replace(hour=19, minute=50), get=fake_get, gen=fake_gen)
        sent = []

        class Acc:
            async def send_file(self, to, path, caption=""):
                sent.append((to, caption)); return type("M", (), {"id": 7})()
        cfg = {"channels": {"xojaobod": {"username": "xojaobodcity24", "publisher": "account", "mode": "shadow",
                                         "morning": {"live": True}, "digest": {"live": True}}}}
        run = lambda t: asyncio.run(digest.publish_live(db, cfg, {"TEST_GROUP_ID": "1"}, Acc(), t, d))
        self.assertIsNone(run(now.replace(minute=10)))          # рано
        self.assertIn("опубликован", run(now))
        self.assertIsNone(run(now.replace(minute=40)))          # второй раз — нет
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][0], "@xojaobodcity24")
