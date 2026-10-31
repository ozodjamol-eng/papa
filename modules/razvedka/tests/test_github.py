import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path

from razvedka import github

NOW = dt.datetime(2026, 10, 19, 10, 0, tzinfo=github.TZ)


def repo(name, stars, pushed="2026-10-15", created="2026-09-20", **kw):
    r = {"full_name": name, "stargazers_count": stars, "pushed_at": pushed + "T00:00:00Z",
         "created_at": created + "T00:00:00Z", "description": f"desc {name}", "html_url": f"https://github.com/{name}",
         "license": {"spdx_id": "MIT"}, "language": "Python"}
    r.update(kw)
    return r


def fake_get(items_by_call):
    calls = []

    def get(url, token="", timeout=30):
        calls.append(url)
        i = len(calls) - 1
        v = items_by_call[i] if i < len(items_by_call) else []
        if isinstance(v, Exception):
            raise v
        return {"items": v}
    get.calls = calls
    return get


class TestGithub(unittest.TestCase):
    def test_queries_have_freshness(self):
        qs = github.search_queries(NOW.date())
        self.assertEqual(len(qs), 2 * len(github.TOPICS))
        self.assertTrue(all("fork:false" in q and "archived:false" in q for _, q in qs))
        self.assertIn("created:>=2026-09-04", qs[0][1])
        self.assertIn("pushed:>=2026-09-19", qs[1][1])

    def test_collect_filters_junk_and_seen(self):
        get = fake_get([[
            repo("a/good", 800),
            repo("b/fork", 900, fork=True),
            repo("c/archived", 900, archived=True),
            repo("d/stale", 900, pushed="2026-06-01"),
            repo("e/seen", 900),
            repo("f/old-strong", 2000, created="2020-01-01"),
        ]])
        cands, errors = github.collect(NOW.date(), {"e/seen"}, get)
        names = [c["name"] for c in cands]
        self.assertEqual(names, ["a/good", "f/old-strong"])   # новый 800×3 > старый 2000
        self.assertEqual(errors, [])

    def test_rate_limit_stops(self):
        get = fake_get([github.GithubError("GitHub HTTP 403")])
        cands, errors = github.collect(NOW.date(), set(), get)
        self.assertEqual(cands, [])
        self.assertEqual(len(get.calls), 1)
        self.assertIn("403", errors[0])

    def test_run_with_ai_and_history(self):
        get = fake_get([[repo("x/tool", 120)]])
        answer = "🧭 GITHUB-РАЗВЕДКА — неделя до 19.10.2026\n1) x/tool ⭐ 120 · MIT\n👉 Совет: x/tool"

        def gpost(model, body, key, timeout=300):
            self.assertNotIn("tools", body)            # без веб-поиска — дёшево
            self.assertIn("x/tool", body["contents"][0]["parts"][0]["text"])
            return {"candidates": [{"content": {"parts": [{"text": answer}]}}],
                    "usageMetadata": {"promptTokenCount": 3000, "candidatesTokenCount": 400}}
        with tempfile.TemporaryDirectory() as d:
            os.environ["GEMINI_API_KEY"] = "g-test"
            old_dir = os.environ.get("PAPA_GEMINI_DIR")   # 31.10: вернуть как было, а не на боевой каталог
            os.environ["PAPA_GEMINI_DIR"] = d
            try:
                text = github.run(Path(d), now=NOW, get=get, gpost=gpost)
                self.assertIn("x/tool", text)
                self.assertIn("💲 расход", text)
                self.assertEqual(json.loads((Path(d) / "history-github.json").read_text()), ["x/tool"])
                # повторный запуск: уже показанный инструмент не предлагается
                text2 = github.run(Path(d), now=NOW, get=fake_get([[repo("x/tool", 130)]]), gpost=gpost)
                self.assertIn("не найдено", text2)
            finally:
                os.environ.pop("GEMINI_API_KEY", None)
                os.environ.pop("PAPA_GEMINI_DIR", None) if old_dir is None else os.environ.__setitem__("PAPA_GEMINI_DIR", old_dir)

    def test_run_without_key_plain(self):
        os.environ.pop("GEMINI_API_KEY", None)
        with tempfile.TemporaryDirectory() as d:
            text = github.run(Path(d), now=NOW, get=fake_get([[repo("y/bot", 4200, created="2024-01-01")]]))
        self.assertIn("без ИИ-оценки", text)
        self.assertIn("y/bot ⭐ 4.2k", text)


if __name__ == "__main__":
    unittest.main()
