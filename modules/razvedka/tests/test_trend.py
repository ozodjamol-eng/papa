import datetime as dt
import os
import json
import tempfile
import unittest
from pathlib import Path

from razvedka import trend

NOW = dt.datetime(2026, 10, 17, 12, 0, tzinfo=trend.TZ)
ANSWER = "🎬 ТРЕНДЫ ДНЯ — 17.10.2026\n1) Летающая машина — авто взлетает над пробкой\n👉 Совет: делаем 1)\nТЕМЫ: Летающая машина; AI-объятие"


def fake_gpost(texts):
    calls = []

    def gpost(model, body, key, timeout=300):
        calls.append(body)
        return {"candidates": [{"content": {"parts": [{"text": texts[len(calls) - 1]}]},
                                "groundingMetadata": {"webSearchQueries": ["q1", "q2", "q3"]}}],
                "usageMetadata": {"promptTokenCount": 2000, "candidatesTokenCount": 500}}
    gpost.calls = calls
    return gpost


class TestTrend(unittest.TestCase):
    def test_split_topics(self):
        text, topics = trend.split_topics(ANSWER)
        self.assertNotIn("ТЕМЫ", text)
        self.assertEqual(topics, ["Летающая машина", "AI-объятие"])
        self.assertEqual(trend.split_topics("без тем")[1], [])

    def test_run_history_cost(self):
        gpost = fake_gpost([ANSWER, ANSWER])
        with tempfile.TemporaryDirectory() as d:
            os.environ["GEMINI_API_KEY"] = "g-test"
            os.environ["PAPA_GEMINI_DIR"] = d
            try:
                out = trend.run("daily", Path(d), now=NOW, gpost=gpost)
                self.assertIn("Летающая машина", out)
                self.assertIn("расход", out)
                self.assertNotIn("ТЕМЫ:", out)
                self.assertEqual(gpost.calls[0]["tools"], [{"google_search": {}}])
                hist = json.loads((Path(d) / "history-daily.json").read_text())
                self.assertEqual(hist, ["Летающая машина", "AI-объятие"])
                trend.run("daily", Path(d), now=NOW, gpost=gpost)            # повтор: история не дублируется,
                self.assertIn("Летающая машина", gpost.calls[1]["contents"][0]["parts"][0]["text"])   # и уходит в промпт
                self.assertEqual(len(json.loads((Path(d) / "history-daily.json").read_text())), 2)
            finally:
                os.environ.pop("GEMINI_API_KEY", None)
                os.environ.pop("PAPA_GEMINI_DIR", None)

    def test_no_key(self):
        os.environ.pop("GEMINI_API_KEY", None)
        with self.assertRaises(trend.TrendError):
            trend.ask("x", gpost=fake_gpost([]))

    def test_cost(self):
        u = {"input_tokens": 1_000_000, "output_tokens": 0, "searches": 10}
        self.assertEqual(trend.cost(u), 0.3)


if __name__ == "__main__":
    unittest.main()


class TestBotSend(unittest.TestCase):
    def test_chunks_and_fail(self):
        import io
        try:
            from razvedka import telegram
        except ImportError:
            self.skipTest("нет telethon")
        sent = []

        def ok(url, data=None, timeout=30):
            sent.append(data)
            return io.BytesIO(b'{"ok": true}')
        self.assertTrue(telegram.bot_send("T", -1001, "x" * 8000, urlopen=ok))
        self.assertEqual(len(sent), 3)

        def bad(url, data=None, timeout=30):
            raise OSError("boom")
        self.assertFalse(telegram.bot_send("T", -1001, "hi", urlopen=bad))


class TestGemini(unittest.TestCase):
    """22.10 аудит: Anthropic владельца заблокирован — разведка идёт через Gemini с поиском Google."""
    def test_gemini_path_and_cost(self):
        seen = {}

        def gpost(model, body, key, timeout=300):
            seen["model"], seen["body"], seen["key"] = model, body, key
            return {"candidates": [{"content": {"parts": [{"text": "🎬 ТРЕНДЫ ДНЯ\nТЕМЫ: a; b"}]},
                                    "groundingMetadata": {"webSearchQueries": ["q1", "q2"]}}],
                    "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 500}}
        os.environ["GEMINI_API_KEY"] = "g-test"
        try:
            text, u = trend.ask("x", gpost=gpost)
        finally:
            del os.environ["GEMINI_API_KEY"]
        self.assertIn("ТРЕНДЫ", text)
        self.assertEqual((u["searches"], u["model"], seen["key"]), (2, "gemini", "g-test"))
        self.assertEqual(seen["body"]["tools"], [{"google_search": {}}])
        self.assertLess(trend.cost(u, "gemini"), 0.01)

    def test_gemini_no_key(self):
        os.environ.pop("GEMINI_API_KEY", None)
        with self.assertRaises(trend.TrendError):
            trend.gemini_ask("x")
