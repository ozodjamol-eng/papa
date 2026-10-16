"""Тесты исполнителя Лондона: сверка с allow.json, отказ незнакомому, маскировка секретов."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import papa_runner as pr  # noqa: E402

REPO = HERE.parents[2]


class TestRunner(unittest.TestCase):
    def test_allowed(self):
        self.assertEqual(pr.allowed("london-diagnose", REPO), "")
        self.assertEqual(pr.allowed("genplan5-overdue-skip", REPO), "")
        self.assertEqual(pr.allowed("runner-install", REPO), "denied")
        self.assertEqual(pr.allowed("purge", REPO), "denied")
        self.assertEqual(pr.allowed("something-new", REPO), "not_listed")
        self.assertEqual(pr.allowed("../etc", REPO), "bad_name")
        self.assertEqual(pr.allowed("status", Path("/nonexistent")), "no_allow_list")

    def test_execute_refuses_without_running(self):
        ran = []
        pr.REPO = REPO
        ok, res = pr.execute({"task": "purge"}, runner=lambda t: ran.append(t) or (0, ""), refresh=False)
        self.assertEqual((ok, ran, res["error"]), (False, [], "denied"))

    def test_execute_runs_listed(self):
        pr.REPO = REPO
        ok, res = pr.execute({"task": "london-diagnose"}, runner=lambda t: (0, "a\n== LONDON_DIAGNOSE_DONE\n"), refresh=False)
        self.assertTrue(ok)
        self.assertEqual(res["summary"], "== LONDON_DIAGNOSE_DONE")

    def test_mask(self):
        out = pr.mask("bot 1234567890:AAH" + "x" * 33 + " password=supersecretvalue1 ok")
        self.assertNotIn("x" * 20, out)
        self.assertNotIn("supersecretvalue1", out)
        self.assertIn("ok", out)


if __name__ == "__main__":
    unittest.main()
