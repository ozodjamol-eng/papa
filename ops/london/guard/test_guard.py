import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genplan5_guard as g  # noqa: E402


class T(unittest.TestCase):
    def db(self):
        d = sqlite3.connect(":memory:"); d.row_factory = sqlite3.Row
        d.execute("CREATE TABLE campaigns(id, name, slot_time, active, deleted_at)")
        d.execute("CREATE TABLE scheduled_posts(id, rubric, slot_key, scheduled_at, status, last_error)")
        d.executemany("INSERT INTO campaigns VALUES(?,?,?,?,?)", [(11, "ИЖАРА", "18:30", 1, None), (12, "УТИН", "18:30", 1, None)])
        d.executemany("INSERT INTO scheduled_posts VALUES(?,?,?,?,?,?)", [
            (952, "ad", "campaign_11_2026-10-20", "2026-10-20T18:30:00", "pending", None),
            (953, "ad", "campaign_12_2026-10-20", "2026-10-20T18:30:00", "skipped", "slot busy")])
        return d

    def test_today_case(self):
        p = g.check(self.db(), dt.datetime(2026, 10, 20, 7, 0))
        txt = " ".join(t for _, t in p)
        self.assertIn("одно время 18:30", txt)
        self.assertIn("«УТИН» 18:30 — ПРОПУЩЕНА", txt)
        self.assertNotIn("ИЖАРА» 18:30 —", txt)       # ещё не время

    def test_late_pending(self):
        p = g.check(self.db(), dt.datetime(2026, 10, 20, 18, 45))
        self.assertTrue(any("«ИЖАРА» 18:30 — время прошло" in t for _, t in p), p)


if __name__ == "__main__":
    unittest.main()
