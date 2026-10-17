import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from razvedka import trend

NOW = dt.datetime(2026, 10, 17, 12, 0, tzinfo=trend.TZ)
ANSWER = "🎬 ТРЕНДЫ ДНЯ — 17.10.2026\n1) Летающая машина — авто взлетает над пробкой\n👉 Совет: делаем 1)\nТЕМЫ: Летающая машина; AI-объятие"


def fake_post(seq):
    calls = []

    def post(body, key, timeout=300):
        calls.append(body)
        return seq[len(calls) - 1]
    post.calls = calls
    return post


class TestTrend(unittest.TestCase):
    def test_split_topics(self):
        text, topics = trend.split_topics(ANSWER)
        self.assertNotIn("ТЕМЫ", text)
        self.assertEqual(topics, ["Летающая машина", "AI-объятие"])
        self.assertEqual(trend.split_topics("без тем")[1], [])

    def test_run_pause_history_cost(self):
        post = fake_post([
            {"stop_reason": "pause_turn", "content": [{"type": "server_tool_use"}],
             "usage": {"input_tokens": 1000, "output_tokens": 10, "server_tool_use": {"web_search_requests": 2}}},
            {"stop_reason": "end_turn", "content": [{"type": "text", "text": ANSWER}],
             "usage": {"input_tokens": 2000, "output_tokens": 500, "server_tool_use": {"web_search_requests": 1}}},
        ])
        with tempfile.TemporaryDirectory() as d:
            import os
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
            out = trend.run("daily", Path(d), now=NOW, post=post)
            self.assertIn("Летающая машина", out)
            self.assertIn("расход", out)
            self.assertNotIn("ТЕМЫ:", out)
            self.assertEqual(len(post.calls), 2)
            self.assertEqual(post.calls[0]["tools"][0]["type"], "web_search_20250305")
            hist = json.loads((Path(d) / "history-daily.json").read_text())
            self.assertEqual(hist, ["Летающая машина", "AI-объятие"])
            post2 = fake_post([{"stop_reason": "end_turn", "content": [{"type": "text", "text": ANSWER}], "usage": {}}])
            trend.run("daily", Path(d), now=NOW, post=post2)           # повтор: история не дублируется,
            self.assertIn("Летающая машина", post2.calls[0]["messages"][0]["content"])   # и уходит в промпт
            self.assertEqual(len(json.loads((Path(d) / "history-daily.json").read_text())), 2)

    def test_no_key(self):
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with self.assertRaises(trend.TrendError):
            trend.ask("x", "m", 1, post=fake_post([]))

    def test_cost(self):
        u = {"input_tokens": 1_000_000, "output_tokens": 0, "searches": 10}
        self.assertEqual(trend.cost(u, "claude-haiku-5-5"), 1.1)


if __name__ == "__main__":
    unittest.main()
