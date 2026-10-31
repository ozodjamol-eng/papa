"""30.10 полный аудит: общий лимит Gemini — фоновая Разведка уступает ассистенту и постам."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from razvedka import budget

NOW = dt.datetime(2026, 10, 30, 12, 0, tzinfo=budget.TZ)


class TestBudget(unittest.TestCase):
    def test_counter_and_share(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self.assertEqual(budget.used(NOW, p), 0)
            cap = int(budget.DAY_BUDGET * budget.BACKGROUND_SHARE)
            budget.spend(cap - 1, NOW, p)
            budget.gate(NOW, p)                                   # последний разрешённый
            self.assertEqual(budget.used(NOW, p), cap)
            with self.assertRaises(budget.BudgetStop):
                budget.gate(NOW, p)                               # дальше — ассистенту и постам
            self.assertTrue(issubclass(budget.BudgetStop, RuntimeError))   # вызывающие ловят как «лимит Gemini»
            self.assertEqual(budget.used(NOW + dt.timedelta(days=1), p), 0)   # новый день — заново

    def test_saver_flag_stops(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "gemini-saver").write_text(NOW.date().isoformat())
            ok, why = budget.background_ok(NOW, p)
            self.assertFalse(ok)
            self.assertIn("экономия", why)
            (p / "gemini-saver").write_text("2026-10-29")          # вчерашний флаг не действует
            self.assertTrue(budget.background_ok(NOW, p)[0])

    def test_no_access_does_not_break(self):
        p = Path("/nonexistent-papa-dir")
        self.assertEqual(budget.spend(1, NOW, p), 0)
        self.assertTrue(budget.background_ok(NOW, p)[0])


if __name__ == "__main__":
    unittest.main()


class GoogleReset(unittest.TestCase):
    """31.10: флаг экономии, поставленный до полуночи PT, после обнуления лимита Google не действует."""

    def test_old_flag_off(self):
        import os, tempfile, datetime as dt
        from pathlib import Path
        from razvedka import budget
        now = dt.datetime(2026, 10, 31, 9, 0, tzinfo=dt.timezone.utc)          # 14:00 Ташкент, после сброса (07:00 UTC)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "gemini-saver"
            f.write_text("2026-10-31")
            os.utime(f, (now.timestamp() - 4 * 3600,) * 2)                     # 05:00 UTC — до сброса
            self.assertFalse(budget.saver_on(now, Path(d)))
            os.utime(f, (now.timestamp() - 600,) * 2)                          # после сброса
            self.assertTrue(budget.saver_on(now, Path(d)))
