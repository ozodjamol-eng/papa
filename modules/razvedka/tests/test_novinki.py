import datetime as dt
import tempfile
import unittest
from pathlib import Path

from razvedka import novinki
from razvedka.trend import TrendError

NOW = dt.datetime(2026, 10, 28, 10, 0, tzinfo=novinki.TZ)


class NovinkiTest(unittest.TestCase):
    def test_prompt_has_services_and_dates(self):
        p = novinki.prompt(NOW, ["Eleven v4"])
        self.assertIn("ElevenLabs", p)
        self.assertIn("21.10.2026", p)
        self.assertIn("Eleven v4", p)

    def test_split_topics(self):
        text, t = novinki.split_topics("🆕 НОВИНКИ\n1) x\nТЕМЫ: Eleven v4; Veo 4")
        self.assertNotIn("ТЕМЫ", text)
        self.assertEqual(t, ["Eleven v4", "Veo 4"])

    def test_run_saves_history_and_hides_topics(self):
        with tempfile.TemporaryDirectory() as d:
            out = novinki.run(Path(d), NOW, ask=lambda p, search: ("🆕 НОВИНКИ\n1) a\nТЕМЫ: A; B", {}))
            self.assertNotIn("ТЕМЫ", out)
            self.assertEqual(novinki.load_history(Path(d) / "history-novinki.json"), ["A", "B"])
            seen = []
            novinki.run(Path(d), NOW, ask=lambda p, search: (seen.append(p) or "ok\nТЕМЫ: C", {}))
            self.assertIn("A; B", seen[0])

    def test_error_is_reported(self):
        def bad(p, search):
            raise TrendError("нет ключа")
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("ошибка", novinki.run(Path(d), NOW, ask=bad))


if __name__ == "__main__":
    unittest.main()
